from __future__ import annotations

import time
from typing import Optional, Any, Dict, TYPE_CHECKING
import subprocess
import tempfile
import shutil
import socket
import os

# No direct 'import meshtastic' or its components here at the module level.
# These will be imported inside functions that need them to allow the module
# to be imported by tests even if meshtastic is not installed.

from core.logger_setup import server_logger
from core.config_loader import (
    get_meshtastic_serial_port,
    load_app_config,
    load_bitcoin_rpc_config,
    load_reassembly_timeout,
)
from core.reassembler import (
    TransactionReassembler,
    InvalidChunkFormatError,
    MismatchedTotalChunksError,
    ReassemblyError,
    CHUNK_PREFIX,
    CHUNK_PARTS_DELIMITER,
)
from core.rpc_client import BitcoinRPCClient

if TYPE_CHECKING:
    import meshtastic.serial_interface

# Global instance of the TransactionReassembler
# Now initialized in main() with config timeout
transaction_reassembler: TransactionReassembler = None  # type: ignore

# Placeholder for the main Meshtastic interface, to be set in main()
# This is needed if on_receive_text_message or other global scope functions
# need to call send_meshtastic_reply directly or access iface properties.
# For now, iface is passed to on_receive_text_message by pubsub.
# And send_meshtastic_reply is called from main loop for timeouts,
# or from on_receive for immediate NACKs.
meshtastic_interface_instance: Optional[
    "meshtastic.serial_interface.SerialInterface"
] = None

bitcoin_rpc = None  # Global RPC connection for broadcasting

TRX_CHUNK_BUFFER: Dict[str, Any] = {}  # This will be replaced by reassembler logic
# TODO: Remove TRX_CHUNK_BUFFER once reassembler is fully integrated and tested.

# Ensure .env is loaded at application startup
load_app_config()

# Tor integration settings
TOR_BINARY_PATH = os.path.join(os.path.dirname(__file__), "tor", "tor")
TOR_SOCKS_PORT = 19050  # You can randomize or make configurable
TOR_CONTROL_PORT = 9051  # Not strictly needed unless you want to control Tor

# --- Reliable Chunked Protocol: Deduplication state ---
PROCESSED_CHUNKS = set()  # Set of (session_id, chunk_number) tuples


def is_onion_address(host):
    return host.endswith(".onion")


def start_tor(socks_port=TOR_SOCKS_PORT):
    data_dir = tempfile.mkdtemp()
    tor_cmd = [
        TOR_BINARY_PATH,
        "--SocksPort",
        str(socks_port),
        "--DataDirectory",
        data_dir,
    ]
    tor_process = subprocess.Popen(
        tor_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    # Wait for Tor to be ready
    for _ in range(30):
        try:
            s = socket.create_connection(("localhost", socks_port), timeout=2)
            s.close()
            return tor_process, data_dir
        except Exception:
            time.sleep(1)
    tor_process.terminate()
    shutil.rmtree(data_dir)
    raise RuntimeError("Tor did not start in time")


def stop_tor(tor_process, data_dir):
    if tor_process:
        tor_process.terminate()
        tor_process.wait()
    if data_dir and os.path.exists(data_dir):
        shutil.rmtree(data_dir)


def _format_node_id(node_id_val: Any) -> Optional[str]:
    """Helper to consistently format node IDs to !<hex_string> or return None."""
    if isinstance(node_id_val, int):
        return f"!{node_id_val:x}"
    elif isinstance(node_id_val, str):
        if node_id_val.startswith("!"):
            return node_id_val
        else:
            try:
                # Try to interpret as hex string if not starting with '!'
                int(node_id_val, 16)  # Validate if it can be hex
                return f"!{node_id_val}"
            except ValueError:
                # Not a valid hex string if it doesn't start with '!'
                # and isn't parseable as hex.
                # This case should ideally not happen if Meshtastic
                # provides consistent IDs.
                # Depending on strictness, could log a warning or return None.
                server_logger.warning(
                    f"Received non-standard string node ID format: {node_id_val}"
                )
                return None  # Or treat as opaque string if that's ever expected
    return None


def _extract_session_id_from_raw_chunk(message_text: str) -> Optional[str]:
    """Rudimentary attempt to extract tx_session_id for NACKs if full parsing fails."""
    try:
        if message_text.startswith(CHUNK_PREFIX):
            parts = message_text[len(CHUNK_PREFIX) :].split(CHUNK_PARTS_DELIMITER)
            if len(parts) > 0 and parts[0]:
                return parts[0]
    except Exception:  # pylint: disable=broad-except
        pass  # Best effort
    return None


def on_receive_text_message(
    packet: Dict[str, Any], interface=None, send_reply_func=None, logger=None, **kwargs
) -> None:
    """
    Callback function to handle received Meshtastic packets.
    Filters for direct text messages, identifies transaction chunks,
    and uses TransactionReassembler to process them.
    """
    iface = interface
    global meshtastic_interface_instance
    if meshtastic_interface_instance is None and iface is not None:
        pass

    # Use dependency injection for reply function
    if send_reply_func is None:
        send_reply_func = send_meshtastic_reply
    # Use dependency injection for logger
    if logger is None:
        logger = server_logger

    try:
        decoded_packet = packet.get("decoded")
        if not decoded_packet:
            logger.debug(
                f"Received packet without 'decoded' content: "
                f"{packet.get('id', 'N/A')}"
            )
            return

        my_node_id_from_iface = None
        if (
            hasattr(iface, "myInfo")
            and iface.myInfo
            and hasattr(iface.myInfo, "my_node_num")
        ):
            my_node_id_from_iface = iface.myInfo.my_node_num

        my_node_id = _format_node_id(my_node_id_from_iface)

        # Check if the message is from self, using the raw integer ID for comparison
        # This check needs to be after my_node_id_from_iface is determined and
        # ideally after decoded_packet is confirmed to exist for text preview.
        sender_raw_id = packet.get("from")
        if (
            sender_raw_id is not None
            and my_node_id_from_iface is not None
            and sender_raw_id == my_node_id_from_iface
        ):
            text_preview = "(No text field)"  # Default if text is not present
            if decoded_packet and "text" in decoded_packet:
                text_content = decoded_packet.get("text", "")
                text_preview = text_content[:30]
                if len(text_content) > 30:
                    text_preview += "..."

            # For self-messages, From and To are the same (our ID)
            logger.debug(
                f"Ignoring DM from self. From: {my_node_id}, To: {my_node_id}, "
                f"Text: '{text_preview}'"
            )
            return

        # Determine destination node ID from packet (prefer 'to',
        # fallback to 'toId')
        dest_val = packet.get("to")
        if dest_val is None:  # If 'to' (int) is not present, try 'toId' (str)
            dest_val = packet.get("toId")
        destination_node_id = _format_node_id(dest_val)

        if not my_node_id:
            logger.warning("Could not determine or format my node ID from interface.")
            return

        # If destination_node_id is None, it could be a broadcast
        # (not handled here as DM) or malformed.
        # For strict DM processing, if destination_node_id is None, we ignore.
        # Story 1.2 specifies DMs, so if destination_node_id is None or
        # not matching our ID, it's not a DM to us.
        if destination_node_id != my_node_id:
            # This also handles destination_node_id being None implicitly
            if destination_node_id:  # Log only if there was a different destination
                from_node_display = (
                    _format_node_id(packet.get("from") or packet.get("fromId"))
                    or "UnknownSender"
                )
                logger.debug(
                    f"Received message not for this node. To: "
                    f"{destination_node_id}, MyID: {my_node_id}, "
                    f"From: {from_node_display}"
                )
            # Else, it could be a broadcast or message with no destination,
            # not processed as DM to us.
            return

        # At this point, message is considered a direct message to us
        # (my_node_id == destination_node_id)
        actual_portnum_str = str(decoded_packet.get("portnum"))

        sender_raw_key_for_reassembler = packet.get("from")  # Prefer int ID
        if sender_raw_key_for_reassembler is None:
            sender_raw_key_for_reassembler = packet.get("fromId", "UnknownSender")

        # This formatted ID is crucial for sending replies correctly
        sender_node_id_for_reply = _format_node_id(
            packet.get("from") or packet.get("fromId")
        )

        if not sender_node_id_for_reply:
            logger.warning(
                f"Could not determine a valid sender node ID for reply from packet: {packet}. Ignoring DM."
            )
            return

        if actual_portnum_str == "TEXT_MESSAGE_APP":
            # Robust message extraction: support both 'text' and 'payload' (see Meshtastic autoresponder.py)
            message_text = decoded_packet.get("text")
            if not message_text and "payload" in decoded_packet:
                try:
                    message_text = decoded_packet["payload"].decode("utf-8")
                except Exception as e:
                    logger.error(f"Failed to decode payload as UTF-8: {e}")
                    message_text = None
            if not message_text:
                logger.debug(
                    f"Direct text message with no text from {sender_node_id_for_reply}: {packet.get('id', 'N/A')}"
                )
                return

            logger.info(
                f"Direct text from {sender_node_id_for_reply}: '{message_text}'"
            )

            if message_text.startswith("BTC_SESSION_START|"):
                # Parse: BTC_SESSION_START|<session_id>|<total_chunks>|<chunk_size>
                try:
                    parts = message_text.split("|")
                    if len(parts) != 4:
                        raise ValueError("Malformed BTC_SESSION_START message")
                    _, session_id, total_chunks, chunk_size = parts
                    ack_msg = f"BTC_SESSION_ACK|{session_id}|READY|REQUEST_CHUNK|1"
                except Exception:
                    session_id = parts[1] if len(parts) > 1 else "unknown"
                    ack_msg = f"BTC_SESSION_ACK|{session_id}|READY|REQUEST_CHUNK|1"
                logger.debug(
                    f"[TEST] send_meshtastic_reply called for session {session_id} to {sender_node_id_for_reply} with: {ack_msg}"
                )
                send_reply_func(iface, sender_node_id_for_reply, ack_msg, session_id)
                return

            if message_text.startswith("BTC_SESSION_ABORT|"):
                # Parse: BTC_SESSION_ABORT|<session_id>|<reason>
                try:
                    parts = message_text.split("|", 2)
                    if len(parts) < 3:
                        session_id = parts[1] if len(parts) > 1 else "unknown"
                        reason = "No reason provided"
                    else:
                        _, session_id, reason = parts
                    logger.info(
                        f"Session {session_id} aborted by {sender_node_id_for_reply}: {reason}"
                    )
                except Exception as e:
                    logger.error(f"Failed to parse BTC_SESSION_ABORT message: {e}")
                return

            if message_text.startswith("BTC_CHUNK|"):
                # Parse: BTC_CHUNK|<session_id>|<chunk_number>/<total_chunks>|<hex_payload>
                try:
                    parts = message_text.split("|", 3)
                    if len(parts) != 4:
                        raise ValueError("Malformed BTC_CHUNK message")
                    _, session_id, chunk_info, hex_payload = parts
                    chunk_number, total_chunks = chunk_info.split("/")
                    chunk_number = int(chunk_number)
                    total_chunks = int(total_chunks)
                    sender_node_id_for_reply = _format_node_id(
                        packet.get("from") or packet.get("fromId")
                    )
                    # Deduplication: only process first time
                    global PROCESSED_CHUNKS
                    chunk_key = (session_id, chunk_number)
                    if chunk_key in PROCESSED_CHUNKS:
                        return  # Ignore duplicate
                    PROCESSED_CHUNKS.add(chunk_key)
                    if chunk_number == 1:
                        ack_msg = f"BTC_CHUNK_ACK|{session_id}|1|OK|REQUEST_CHUNK|2"
                        send_reply_func(
                            iface, sender_node_id_for_reply, ack_msg, session_id
                        )
                        return
                except Exception as e:
                    logger.error(f"Failed to parse BTC_CHUNK message: {e}")
                    return

            if message_text.startswith(CHUNK_PREFIX):
                # Log every received chunk for diagnostics
                try:
                    # Always parse session_id and chunk_info for NACK, even if add_chunk fails
                    parts = message_text[len(CHUNK_PREFIX) :].split(
                        CHUNK_PARTS_DELIMITER
                    )
                    session_id = parts[0] if len(parts) > 0 else "UNKNOWN"
                    chunk_info = parts[1] if len(parts) > 1 else "UNKNOWN"
                except Exception:
                    session_id = "UNKNOWN"
                    chunk_info = "UNKNOWN"
                logger.debug(
                    f"Received BTC_TX chunk: session_id={session_id}, chunk={chunk_info}, from={sender_node_id_for_reply}"
                )
                logger.info(
                    f"Potential BTC transaction chunk from {sender_node_id_for_reply}. Processing..."
                )
                try:
                    chunk_number = 1
                    total_chunks = 1
                    try:
                        if chunk_info and "/" in chunk_info:
                            chunk_number, total_chunks = chunk_info.split("/")
                            chunk_number = int(chunk_number)
                            total_chunks = int(total_chunks)
                    except Exception:
                        # If chunk_info is invalid, leave chunk_number/total_chunks as 1
                        pass
                    reassembled_hex = transaction_reassembler.add_chunk(
                        sender_raw_key_for_reassembler, message_text
                    )

                    # ACK valid chunk and request next
                    if chunk_number < total_chunks:
                        ack_msg = f"BTC_CHUNK_ACK|{session_id}|{chunk_number}|OK|REQUEST_CHUNK|{chunk_number+1}"
                    elif chunk_number == total_chunks:
                        ack_msg = f"BTC_CHUNK_ACK|{session_id}|{chunk_number}|OK|ALL_CHUNKS_RECEIVED"
                    send_reply_func(
                        iface, sender_node_id_for_reply, ack_msg, session_id
                    )

                    if reassembled_hex:
                        logger.info(
                            f"[Sender: {sender_node_id_for_reply}] Successfully reassembled transaction: "
                            f"{reassembled_hex[:80]}{'...' if len(reassembled_hex) > 80 else ''} (len: {len(reassembled_hex)})"
                        )

                        # Log the full raw transaction hex before broadcasting
                        logger.info(
                            f"[Sender: {sender_node_id_for_reply}, Session: {session_id}] Attempting to broadcast raw TX: {reassembled_hex}"
                        )

                        txid, error = bitcoin_rpc.broadcast_transaction_via_rpc(
                                reassembled_hex
                        )
                        if txid:
                            ack_msg = f"BTC_ACK|{session_id}|SUCCESS|TXID:{txid}"
                            send_reply_func(
                                iface, sender_node_id_for_reply, ack_msg, session_id
                            )
                            logger.info(
                                f"[Sender: {sender_node_id_for_reply}, Session: {session_id}] Broadcast success. TXID: {txid}"
                            )
                        else:
                            # Optimize error message for size constraints
                            error_msg = str(error)
                            if "Transaction outputs already in utxo set" in error_msg:
                                error_msg = "TX already in UTXO set"
                            elif "Transaction already in block chain" in error_msg:
                                error_msg = "TX already in chain"
                            elif "insufficient fee" in error_msg.lower():
                                error_msg = "Insufficient fee"
                            elif "missing inputs" in error_msg.lower():
                                error_msg = "Missing inputs"
                            elif "bad-txns-inputs-spent" in error_msg:
                                error_msg = "Inputs spent"
                            elif "bad-txns-in-belowout" in error_msg:
                                error_msg = "Input < Output"
                            elif "too-long-mempool-chain" in error_msg:
                                error_msg = "Chain too long"
                            elif "mempool full" in error_msg.lower():
                                error_msg = "Mempool full"
                            elif "replacement transaction" in error_msg.lower():
                                error_msg = "RBF disabled"
                            elif "non-mandatory-script-verify-flag" in error_msg:
                                error_msg = "Script verify failed"
                            elif "transaction already abandoned" in error_msg.lower():
                                error_msg = "TX abandoned"
                            elif "bad-txns-nonstandard-inputs" in error_msg:
                                error_msg = "Non-std inputs"
                            elif "bad-txns-oversize" in error_msg:
                                error_msg = "TX too large"
                            elif "version" in error_msg.lower() and "reject" in error_msg.lower():
                                error_msg = "Version rejected"
                            elif "dust" in error_msg.lower():
                                error_msg = "Dust output"
                            elif "fee is too high" in error_msg.lower():
                                error_msg = "Fee too high"
                            elif "absurdly-high-fee" in error_msg.lower():
                                error_msg = "Absurd fee"
                            # Keep original error in logs but use concise version in NACK
                            nack_msg = f"BTC_NACK|{session_id}|ERROR|{error_msg}"
                            send_reply_func(
                                iface, sender_node_id_for_reply, nack_msg, session_id
                            )
                            logger.error(
                                f"[Sender: {sender_node_id_for_reply}, Session: {session_id}] Broadcast failed: {error}. Sending NACK."
                            )
                except (InvalidChunkFormatError, MismatchedTotalChunksError) as e:
                    tx_session_id_for_nack = (
                        session_id
                        or _extract_session_id_from_raw_chunk(message_text)
                        or "UNKNOWN"
                    )
                    error_type_str = (
                        type(e)
                        .__name__.replace("Error", "")
                        .replace("Invalid", "Invalid ")
                    )
                    nack_message_detail = f"{error_type_str}: {str(e)}"
                    nack_message = (
                        f"BTC_NACK|{tx_session_id_for_nack}|ERROR|{nack_message_detail}"
                    )
                    max_nack_len = 200
                    if len(nack_message) > max_nack_len:
                        available_len_for_detail = max_nack_len - len(
                            f"BTC_NACK|{tx_session_id_for_nack}|ERROR|...e"
                        )
                        if available_len_for_detail > 0:
                            nack_message_detail = (
                                nack_message_detail[:available_len_for_detail] + "..."
                            )
                        else:
                            nack_message_detail = "Error detail too long"
                        nack_message = f"BTC_NACK|{tx_session_id_for_nack}|ERROR|{nack_message_detail}"
                    logger.error(
                        f"[Sender: {sender_node_id_for_reply}, Session: {tx_session_id_for_nack}] "
                        f"Reassembly error: {str(e)}. Sending NACK."
                    )
                    if iface:
                        send_reply_func(
                            iface,
                            sender_node_id_for_reply,
                            nack_message,
                            tx_session_id_for_nack,
                        )
                    else:
                        server_logger.error(
                            f"[Sender: {sender_node_id_for_reply}, Session: {tx_session_id_for_nack}] "
                            f"Cannot send NACK: Meshtastic interface not available in on_receive."
                        )
                except (
                    ReassemblyError
                ) as e:  # Catch other specific reassembly errors if any
                    tx_session_id_for_nack = (
                        _extract_session_id_from_raw_chunk(message_text) or "UNKNOWN"
                    )
                    server_logger.error(
                        f"[Sender: {sender_node_id_for_reply}, Session: {tx_session_id_for_nack}] "
                        f"General reassembly error: {e}. Notifying sender may be needed."
                    )
                    # Decide if a generic NACK is useful here. Current stories might NACK on timeout instead.
                except Exception as e:  # Catch-all for unexpected errors in add_chunk
                    tx_session_id_for_nack = (
                        _extract_session_id_from_raw_chunk(message_text) or "UNKNOWN"
                    )
                    server_logger.error(
                        f"[Sender: {sender_node_id_for_reply}, Session: {tx_session_id_for_nack}] "
                        f"Unexpected error processing chunk: {e}. Not NACKing automatically.",
                        exc_info=True,
                    )
            else:
                server_logger.info(
                    f"Std direct text from {sender_node_id_for_reply} (not BTC_TX): '{message_text}'"
                )
        else:
            server_logger.debug(
                f"Received direct message, but not TEXT_MESSAGE_APP. "
                f"Portnum: {actual_portnum_str}, From: {sender_node_id_for_reply}, "
                f"ID: {packet.get('id', 'N/A')}"
            )

    except Exception as e:
        server_logger.error(f"Error processing received packet: {e}", exc_info=True)


def send_meshtastic_reply(
    iface: "meshtastic.serial_interface.SerialInterface",
    destination_id: str,  # Expected to be in '!<hex_id>' format
    message_text: str,
    tx_session_id: Optional[str] = None,
) -> bool:
    """
    Sends a reply message to a specified node via Meshtastic.

    Args:
        iface: The initialized Meshtastic interface.
        destination_id: The target node ID (e.g., '!abcdef12').
                        Must be correctly formatted for Meshtastic.
        message_text: The text message to send.
        tx_session_id: Optional transaction session ID for logging context.

    Returns:
        True if the message was sent successfully, False otherwise.
    """
    log_prefix = f"[Session: {tx_session_id}] " if tx_session_id else ""
    try:
        if not iface:
            server_logger.error(
                f"{log_prefix}Cannot send reply: "
                f"Meshtastic interface is not available."
            )
            return False

        # Basic validation for destination_id format (must start with '!')
        # More robust validation could be added if necessary.
        if not destination_id or not destination_id.startswith("!"):
            msg = (
                f"{log_prefix}Cannot send reply: Invalid destination_id format "
                f"'{destination_id}'. Must start with '!'. "
                f"Message: '{message_text}'"
            )
            server_logger.error(msg)
            return False

        server_logger.info(
            f"{log_prefix}Attempting to send reply to {destination_id}: "
            f"'{message_text}'"
        )

        # The sendText method expects the destination node ID.
        # SerialInterface.getNode(nodeId) is used to find the node object.
        # If `destination_id` is `!node_hex_id`, getNode should resolve it.
        # node = iface.getNode(destination_id) # DIAGNOSTIC: Temporarily bypass getNode
        # if not node:
        #     server_logger.error(
        #         f"{log_prefix}Node {destination_id} not found in mesh. "
        #         f"Cannot send reply: '{message_text}'"
        #     )
        #     return False

        # node.sendText( # DIAGNOSTIC: Temporarily bypass getNode
        #     text=message_text,
        #     wantAck=False  # Set to True if we want link-layer ACK
        # )
        # Typically, it queues for sending.

        # DIAGNOSTIC: Use direct sendText with destinationId
        iface.sendText(
            text=message_text,
            destinationId=destination_id,  # destination_id should be in '!<hex_id>' format
            wantAck=False,  # Set to True if we want link-layer ACK
        )
        # End DIAGNOSTIC change

        server_logger.info(
            f"{log_prefix}Successfully queued reply to {destination_id}: "  # Changed "sent" to "queued"
            f"'{message_text}'"
        )
        return True
    except AttributeError as e:
        # This might happen if 'iface' or 'node' is None or
        # doesn't have sendText/getNode
        error_msg = (
            f"{log_prefix}AttributeError while sending reply to {destination_id}: "
            f"{e}. Ensure interface and node objects are valid. "
            f"Message: '{message_text}'"
        )
        server_logger.error(error_msg, exc_info=True)
        return False
    except Exception as e:
        # Catching generic MeshtasticError or other exceptions
        server_logger.error(
            f"{log_prefix}Failed to send reply to {destination_id}: {e}. "
            f"Message: '{message_text}'",
            exc_info=True,
        )
        return False


def initialize_meshtastic_interface(
    port: Optional[str] = None,
) -> Optional["meshtastic.serial_interface.SerialInterface"]:
    """
    Initializes and returns a Meshtastic SerialInterface.
    Imports meshtastic library components internally to handle cases where
    the library might not be installed in the test environment.
    Args:
        port: The specific serial port to connect to (e.g., /dev/ttyACM0).
              If None, the library will attempt to get from config, then auto-detect.
    Returns:
        SerialInterface instance or None if not available.
    """
    serial_port_to_use = port if port is not None else get_meshtastic_serial_port()
    try:
        import meshtastic.serial_interface
    except ImportError:
        server_logger.error(
            "Meshtastic library not found. Please install it (e.g., pip install meshtastic)."
        )
        return None
    log_port_info = (
        f" on port {serial_port_to_use}" if serial_port_to_use else " (auto-detect)"
    )
    server_logger.info(
        f"Attempting to initialize Meshtastic interface{log_port_info}..."
    )
    try:
        iface = (
            meshtastic.serial_interface.SerialInterface(devPath=serial_port_to_use)
            if serial_port_to_use
            else meshtastic.serial_interface.SerialInterface()
        )
    except Exception as e:
        # Robust to test mocks: check type or message
        err_type = type(e).__name__
        err_msg = str(e)
        if err_type == "NoDeviceError" or "No Meshtastic device found" in err_msg:
            server_logger.error(
                "No Meshtastic device found. Ensure it is connected and drivers are installed."
            )
        elif err_type == "MeshtasticError" or "Meshtastic error" in err_msg:
            server_logger.error(
                f"Meshtastic library error during initialization: {err_msg}"
            )
        else:
            server_logger.error(
                f"An unexpected error occurred during Meshtastic initialization: {err_msg}",
                exc_info=True,
            )
        return None
    node_num_display = "Unknown Node Num"
    if (
        hasattr(iface, "myInfo")
        and iface.myInfo
        and hasattr(iface.myInfo, "my_node_num")
    ):
        formatted_node_id = _format_node_id(iface.myInfo.my_node_num)
        if formatted_node_id:
            node_num_display = formatted_node_id
        elif iface.myInfo.my_node_num is not None:
            node_num_display = str(iface.myInfo.my_node_num)
    device_path_str = str(getattr(iface, "devicePath", getattr(iface, "devPath", "?")))
    server_logger.info(
        f"Meshtastic interface initialized successfully. Device: {device_path_str}, My Node Num: {node_num_display}"
    )
    return iface


def main() -> None:
    """
    Main function for the BTC Mesh Server.
    """
    global meshtastic_interface_instance
    global transaction_reassembler
    server_logger.info("Starting BTC Mesh Relay Server...")

    tor_process = None
    tor_data_dir = None
    try:
        # --- Story 5.2: Load reassembly timeout from config ---
        timeout_seconds, timeout_source = load_reassembly_timeout()
        transaction_reassembler = TransactionReassembler(
            timeout_seconds=timeout_seconds
        )
        server_logger.info(
            f"TransactionReassembler initialized with timeout: {timeout_seconds}s (source: {timeout_source})"
        )
        # --- End Story 5.2 integration ---

        # --- Story 4.2: Connect to Bitcoin RPC ---
        try:
            rpc_config = load_bitcoin_rpc_config()
            global bitcoin_rpc

            # Tor integration: if host is .onion, start Tor and set proxy
            rpc_host = rpc_config.get("host", "")
            if is_onion_address(rpc_host):
                server_logger.info(
                    f"Bitcoin RPC host {rpc_host} is a .onion address. Starting Tor..."
                )
                tor_process, tor_data_dir = start_tor()
                proxy_url = f"socks5h://localhost:{TOR_SOCKS_PORT}"
                rpc_config["proxy"] = proxy_url
                server_logger.info(
                    f"Tor started. Using SOCKS proxy at {proxy_url} for Bitcoin RPC."
                )
            # connect rpc    
            bitcoin_rpc = BitcoinRPCClient(rpc_config)
            server_logger.info("Connected to Bitcoin Core RPC node successfully.")
            server_logger.info(f"rpc: {bitcoin_rpc}.")
        except Exception as e:
            bitcoin_rpc = None
            server_logger.error(
                f"Failed to connect to Bitcoin Core RPC node: {e}. Continuing without RPC connection."
            )
        # Store bitcoin_rpc for later use (e.g., as a global or pass to handlers)
        # --- End Story 4.2 integration ---

        # initialize_meshtastic_interface will now use the config loader by default
        meshtastic_iface = initialize_meshtastic_interface()

        if not meshtastic_iface:
            server_logger.error("Failed to initialize Meshtastic interface. Exiting.")
            return

        try:
            # Import pubsub here as it's part of meshtastic
            from pubsub import pub  # PubSub library used by meshtastic

            # Register the callback for text messages
            pub.subscribe(on_receive_text_message, "meshtastic.receive")
            server_logger.info(
                "Registered Meshtastic message handler. Waiting for messages..."
            )

        except ImportError:
            server_logger.error(
                "PubSub library not found. Please install it (e.g., pip install "
                "pypubsub). This is a dependency for Meshtastic event handling."
            )
            if meshtastic_iface and hasattr(meshtastic_iface, "close"):
                meshtastic_iface.close()
            return
        except Exception as e:
            server_logger.error(
                f"Failed to subscribe to Meshtastic messages: {e}", exc_info=True
            )
            if meshtastic_iface and hasattr(meshtastic_iface, "close"):
                meshtastic_iface.close()
            return

        try:
            cleanup_interval = 10  # seconds, same as sleep
            last_cleanup_time = time.time()

            while True:
                current_time = time.time()
                if current_time - last_cleanup_time >= cleanup_interval:
                    server_logger.debug(
                        "Running periodic cleanup of stale reassembly sessions..."
                    )
                    timed_out_sessions = (
                        transaction_reassembler.cleanup_stale_sessions()
                    )
                    for session_info in timed_out_sessions:
                        nack_message = (
                            f"BTC_NACK|{session_info['tx_session_id']}|ERROR|"
                            f"{session_info['error_message']}"
                        )
                        max_nack_len = 200  # Arbitrary safe length
                        if len(nack_message) > max_nack_len:
                            nack_message = nack_message[: max_nack_len - 3] + "..."

                        server_logger.info(
                            f"[Sender: {session_info['sender_id_str']}, Session: {session_info['tx_session_id']}] "
                            f"Session timed out. Sending NACK: {nack_message}"
                        )
                        # Ensure global instance is used here if iface is not available otherwise
                        if meshtastic_interface_instance:
                            on_receive_text_message(
                                packet=None,
                                interface=meshtastic_interface_instance,
                                send_reply_func=send_meshtastic_reply,
                                tx_session_id=session_info["tx_session_id"],
                                error_message=session_info["error_message"],
                            )
                        else:
                            server_logger.error(
                                f"[Sender: {session_info['sender_id_str']}, Session: {session_info['tx_session_id']}] "
                                f"Cannot send timeout NACK: Meshtastic interface not available globally."
                            )
                    last_cleanup_time = current_time
                time.sleep(
                    1.0
                )  # Check for cleanup every second, actual cleanup every 10s.
        except KeyboardInterrupt:
            server_logger.info("Server shutting down by user request (Ctrl+C).")
        except Exception as e:
            server_logger.error(f"Unhandled exception in main loop: {e}", exc_info=True)
        finally:
            if meshtastic_iface and hasattr(meshtastic_iface, "close"):
                server_logger.info("Closing Meshtastic interface...")
                meshtastic_iface.close()
            if tor_process:
                server_logger.info("Stopping Tor process...")
                stop_tor(tor_process, tor_data_dir)
            server_logger.info("BTC Mesh Relay Server stopped.")

    except Exception as e:
        server_logger.error(f"Unhandled exception in main function: {e}", exc_info=True)


if __name__ == "__main__":
    main()
