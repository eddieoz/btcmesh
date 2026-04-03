#!/usr/bin/env python3
import uuid
import os
from core.config_loader import get_meshtastic_serial_port
from core.logger_setup import setup_logger
import time
from pubsub import pub
import queue


def is_valid_hex(s):
    """Check if a string is a valid hexadecimal."""
    try:
        int(s, 16)
        return True
    except ValueError:  # More specific exception
        return False


CHUNK_SIZE = 170  # hex chars (100 bytes)


def chunk_transaction(tx_hex, chunk_size):
    """Split a hex string into chunks of specified size."""
    return [tx_hex[i : i + chunk_size] for i in range(0, len(tx_hex), chunk_size)]


def generate_session_id():
    """Generate a unique 5-character hex session ID."""
    return uuid.uuid4().hex[:5]


# Example raw transaction for reference and testing (see reference_materials.md):
EXAMPLE_RAW_TX = (
    "02000000000108bf2c7da5efaf2708170ffbafde7b2b0ca68234474ea71d443aee6aebf"
    "bf998030000000000fdffffffd6fcdbf37f974be27e8b0d66638355e5f53bfaf7b930fa"
    "e035d23b313c4751042900000000fdffffffcccc5ca913b8eb426fd7c6bb578eab0f265"
    "83d40c51ce52cb12a428c1e75f7320100000000fdffffff981b8b54ad2a8bd8b59d063e"
    "9473aead87412b699cb969298cf29b8787fe10600000000000fdffffff5d154c445b35a"
    "92aaf179c078cdab6310e69455cde650f128cbe85d92bab51600100000000fdffffff7"
    "d23c74a412ef33d5dd856d01933dd6a5453aee3539b12349febbf6c1ba1579801000000"
    "00fdffffffc5c95ce2eac84fbd3db87bbbdb4cc0855088e891cc57b1f9e0684943a399a"
    "abf0000000000fdffffffb7ef5d8a55141068da0d7b5a712ad9bbe44c3b8b412d0df5b9"
    "bcad366d71c8f90500000000fdffffff01697c63030000000016001482ea8436a6318c9"
    "89767a51ce33886d65faf59a10247304402203ec9cfb2b60a7b1df545493d1794fec0b8"
    "b6d8589f562f61c9aec6852775b54102205dfb34dcc9cc31110fdf4e4544c76e9a664cf"
    "29e8f1f9905771db386882527190121030e92cc6f0829ea8b91469c8aa7ca0660d66020"
    "d3e8baaece478905e0c30c1f770247304402204a3a6a7a5d4ff285b1ba4a3457dae8566"
    "a1616738f94e9eddcce6a75dbb831ef0220285c586f6463dcf68ccef59484b2d12bccd7"
    "d68a68b7092068e6cbfd96f04d88012102f48b8ab9a082a1cf94dcd7052ddea7d260b40"
    "cf01e83aa3df00f2266721ef420024730440220527c3eb66a06d697a078b2b2bdf9be52"
    "f9fe036b1e3422a0a150e151ff0cd25b0220268688d8d9a3dd24b9f846b1b2f1b1f1ed8"
    "4443f0023e26fa1ac5f2c1f0626ac012103acc2fbe36c425eb49389e5896232ef90beda"
    "75531845cd726dfed5f60a1fedd10247304402202eee600a307d10fc4777e8143d3db89"
    "94a6e742d56d4e3ce67a21a1e5e509178022022ee1b1fee5d7ec8112a56b1c0ab2eef1b"
    "e00907d384bbf10a7a9d2d27564fb5012103bd6876311fbf657af0c1c85e907c3adf8d5"
    "086d1b3cf2cd4805b40873d2cf3cd02473044022042dbc6204b70da1548456beef504d5"
    "e8d61349dd36913832060b35f61a360429022006940b48cff72f6476b8d449512661876"
    "6500f0868fb99ba40ab518934e9cc2b0121035aa46c0cf9b30a9edf20c65e5c39158aef"
    "bfdd2b7a049d146f42b7dc3163d1b50247304402207811bd5b127e8a693f20115f7f8b8"
    "b4dec6a4d5df32109b21e1252331778ac5202202ac727cc6c53287110fcd371845b5fcd"
    "ba825cb9e60992cc01cffa8e2ee41701012102700455a96ddb63fdaf8fc3ad60d02b057"
    "f8e00ed512476d817150a22fd4495d90247304402202caf8f9c584fe1b5214dc2a67f42"
    "fe3b9fd7386b98807fc6bc273a2cf519769902201f9f7b407f92c7df84701e4259acb19"
    "8ca19c5edbd860385caa6ca1316417c010121035bfcbb577fe3a3a805c78226c7e7c573"
    "053e85e6641243c8f435acde0e04668902473044022074d6273ed2c7f338c9db6a979f6"
    "4f572a21e5a324eec4979dad77383b25263de02202635d0e21ddf4e46f5751d4d6117ad"
    "559f04b7a6d3d00f13dd784b82a902638e012103de05dcec6736d4e15dd88c5b34b638f"
    "ee6cccfd8b260d53379a43be0b343617cd9540c00"
)

CLI_LOG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "logs", "btcmesh_cli.log"
)
cli_logger = setup_logger("btcmesh_cli", CLI_LOG_FILE)

# Define ACK_TIMEOUT for message receive operations
ACK_TIMEOUT = 30  # seconds, adjust as needed
RETRY_TIMEOUT = 10  # seconds, for retrying after unrecognized message
MAX_RETRIES = 3

# Global or context-specific queue and session_id for onReceive
# This is a simple way; for more complex scenarios, consider classes or other structures
_message_queue = None
_current_session_id = None
_expected_sender_node_id = None  # To filter messages from the correct server


def on_receive_text_message_cli(packet, interface):
    """Callback for Meshtastic receive events in CLI."""
    global _message_queue, _current_session_id, _expected_sender_node_id
    try:
        if _message_queue is None or _current_session_id is None:
            # Not yet initialized to receive for a session
            return

        if "decoded" in packet and packet["decoded"]["portnum"] == "TEXT_MESSAGE_APP":
            message_bytes = packet["decoded"]["payload"]
            message_text = message_bytes.decode("utf-8")
            sender_node_id = packet.get("fromId")

            # Filter messages: must be from the expected server and for the current session
            if sender_node_id == _expected_sender_node_id:
                msg_parts = message_text.split("|")
                if len(msg_parts) > 1 and msg_parts[1] == _current_session_id:
                    cli_logger.info(
                        f"CLI received relevant message for session {_current_session_id} from {sender_node_id}: '{message_text}'"
                    )
                    _message_queue.put(message_text)
                elif len(msg_parts) > 1 and msg_parts[1] != _current_session_id:
                    cli_logger.debug(
                        f"CLI received message for different session ID. Expected: '{_current_session_id}', Got: '{msg_parts[1]}'. Msg: '{message_text}'"
                    )
                else:  # Message for our session but not parsable for session ID, or from wrong sender
                    cli_logger.debug(
                        f"CLI received message from {sender_node_id} but not for current session ID or malformed for session check. Msg: '{message_text}'"
                    )
            elif sender_node_id != _expected_sender_node_id:
                # Log if it's a text message but not from the expected sender
                cli_logger.debug(
                    f"CLI received text message from unexpected sender {sender_node_id} (expected {_expected_sender_node_id}). Msg: '{message_text}'"
                )

    except UnicodeDecodeError:
        cli_logger.warning(
            f"CLI could not decode payload: {packet['decoded']['payload']}"
        )
    except Exception as e:
        cli_logger.error(
            f"CLI error in on_receive_text_message_cli: {e}", exc_info=True
        )


def initialize_meshtastic_interface_cli(port=None):
    """
    Initializes and returns a Meshtastic SerialInterface for CLI use.
    Logs all attempts and errors to both stdout and the CLI log file.
    Args:
        port: Optional override for serial port.
    Returns:
        Meshtastic SerialInterface instance if successful, None otherwise.
    """
    serial_port_to_use = port if port is not None else get_meshtastic_serial_port()
    try:
        import meshtastic.serial_interface

        log_port_info = (
            f" on port {serial_port_to_use}" if serial_port_to_use else " (auto-detect)"
        )
        cli_logger.info(
            f"Attempting to initialize Meshtastic interface{log_port_info}..."
        )
        iface = (
            meshtastic.serial_interface.SerialInterface(devPath=serial_port_to_use)
            if serial_port_to_use
            else meshtastic.serial_interface.SerialInterface()
        )
        node_num_display = "Unknown Node Num"
        if (
            hasattr(iface, "myInfo")
            and iface.myInfo
            and hasattr(iface.myInfo, "my_node_num")
        ):
            node_num_display = str(iface.myInfo.my_node_num)
        cli_logger.info(
            f"Meshtastic interface initialized successfully. Device: {getattr(iface, 'devPath', '?')}, My Node Num: {node_num_display}"
        )
        return iface
    except ImportError:
        cli_logger.error(
            "Meshtastic library not found. Please install it (e.g., pip install meshtastic)."
        )
        return None
    except Exception as e:
        cli_logger.error(
            f"An unexpected error occurred during Meshtastic initialization: {e}",
            exc_info=True,
        )
        return None


def cli_main(
    args=None, injected_iface=None, injected_logger=None, injected_message_receiver=None
):
    """Main CLI logic for sending transactions."""
    import argparse
    import sys
    import re

    global _message_queue, _current_session_id, _expected_sender_node_id  # Ensure globals are accessible

    if args is None:
        parser = argparse.ArgumentParser(
            description="Send a raw Bitcoin transaction via Meshtastic LoRa relay."
        )
        parser.add_argument(
            "-d",
            "--destination",
            required=True,
            help="Destination node ID (e.g., !abcdef12)",
        )
        parser.add_argument(
            "-tx", "--tx", required=True, help="Raw transaction hex string"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only parse and print arguments, do not send",
        )
        args = parser.parse_args()
    tx_hex = args.tx
    if len(tx_hex) % 2 != 0 or not re.fullmatch(r"[0-9a-fA-F]+", tx_hex):
        print(
            "Invalid raw transaction hex: must be even length and hex characters only.",
            file=sys.stderr,
        )
        raise ValueError("Invalid raw transaction hex")
    logger = injected_logger if injected_logger is not None else cli_logger
    if args.dry_run:
        print(f"Arguments parsed successfully:")
        print(f"  Destination: {args.destination}")
        print(f"  Raw TX Hex: {args.tx}")
        session_id = getattr(args, "session_id", None) or generate_session_id()
        chunks = chunk_transaction(tx_hex, CHUNK_SIZE)
        total_chunks = len(chunks)
        for i, payload in enumerate(chunks, 1):
            print(f"BTC_TX|{session_id}|{i}/{total_chunks}|{payload}")
        return 0
    iface = (
        injected_iface
        if injected_iface is not None
        else initialize_meshtastic_interface_cli()
    )
    if iface is None:
        print(
            "Failed to initialize Meshtastic interface. See logs for details.",
            file=sys.stderr,
        )
        # Make sure logger is available or fallback
        (injected_logger or cli_logger).error(
            "Failed to initialize Meshtastic interface in cli_main."
        )
        raise RuntimeError("Failed to initialize Meshtastic interface")

    _current_session_id = (
        getattr(args, "session_id", None) or generate_session_id()
    )  # Set global session ID
    _expected_sender_node_id = args.destination  # Set global expected sender

    chunks = chunk_transaction(tx_hex, CHUNK_SIZE)
    total_chunks = len(chunks)

    # Determine if we are using injected receiver or setting up our own
    use_injected_receiver = injected_message_receiver is not None

    if use_injected_receiver and not args.dry_run:
        message_iterator = injected_message_receiver(
            timeout=ACK_TIMEOUT, session_id=_current_session_id
        )
    elif not args.dry_run:  # Standard execution path, set up pubsub
        _message_queue = queue.Queue()
        pub.subscribe(on_receive_text_message_cli, "meshtastic.receive")
        logger.info(
            f"CLI Subscribed to Meshtastic messages for session {_current_session_id}. Expecting replies from {args.destination}"
        )
        message_iterator = None  # We'll use queue.get() instead
    else:  # Dry run or other unhandled case
        message_iterator = None
        # If it's a dry run, we already handled it and returned.
        # If not dry_run but also not using injected_receiver and not setting up pubsub,
        # this means the logic for sending won't run. This path should ideally not be hit
        # if not a dry run. The earlier dry_run check should have exited.
        # For safety, if we reach here and it's not a dry run, log an error.
        if not args.dry_run:
            logger.error(
                "CLI reached an unexpected state: not a dry run, but no message receiver configured."
            )
            return 1  # Error exit

    # Main sending and ACK/NACK handling loop
    # This loop will now run for both injected_message_receiver and pubsub/queue
    if not args.dry_run:
        i = 0
        try:
            while i < total_chunks:
                chunk_num = i + 1
                payload = chunks[i]
                current_retries = 0

                while current_retries < MAX_RETRIES:
                    msg_to_send = f"BTC_TX|{_current_session_id}|{chunk_num}/{total_chunks}|{payload}"
                    try:
                        iface.sendText(text=msg_to_send, destinationId=args.destination)
                        print(
                            f"Sent chunk {chunk_num}/{total_chunks} for session {_current_session_id} to {args.destination}"
                        )
                        logger.info(
                            f"Sent chunk {chunk_num}/{total_chunks} for session {_current_session_id} to {args.destination}"
                        )
                    except Exception as e:
                        err_msg = f"Error sending chunk {chunk_num}/{total_chunks} for session {_current_session_id}: {e}"
                        print(err_msg)
                        logger.error(err_msg, exc_info=True)
                        # Decide if this is retryable or fatal. For now, let's make it fatal for send errors.
                        raise  # Re-raise to be caught by outer try/except in main()

                    # Wait for ACK/NACK/Abort
                    received_msg_text = None
                    try:
                        if use_injected_receiver:
                            received_msg_text = next(message_iterator)
                        else:  # Use our queue
                            received_msg_text = _message_queue.get(
                                block=True, timeout=ACK_TIMEOUT
                            )
                            # Clear queue for next message if multiple arrived
                            while not _message_queue.empty():
                                _message_queue.get_nowait()

                    except StopIteration:  # Only for injected_message_receiver
                        logger.warning(
                            f"Message generator exhausted for session {_current_session_id} while waiting for ACK for chunk {chunk_num}/{total_chunks}."
                        )
                        # This implies a timeout or premature end from the generator
                        current_retries += 1
                        if current_retries < MAX_RETRIES:
                            print(
                                f"Retrying chunk {chunk_num}/{total_chunks} (attempt {current_retries + 1} of {MAX_RETRIES}) due to timeout/generator end."
                            )
                            logger.warning(
                                f"Retrying chunk {chunk_num}/{total_chunks} (attempt {current_retries + 1} of {MAX_RETRIES}) for session {_current_session_id} due to timeout/generator end."
                            )
                            time.sleep(RETRY_TIMEOUT)  # Wait a bit before retrying
                            continue  # Retry sending the same chunk
                        else:
                            errmsg = f"Aborting session {_current_session_id} after {MAX_RETRIES} failed attempts (timeout/generator end) for chunk {chunk_num}/{total_chunks}."
                            print(errmsg)
                            logger.error(errmsg)
                            raise SystemExit(2)  # Abort session
                    except queue.Empty:  # Timeout for our queue
                        logger.warning(
                            f"Timeout waiting for ACK/NACK for chunk {chunk_num}/{total_chunks} in session {_current_session_id}."
                        )
                        current_retries += 1
                        if current_retries < MAX_RETRIES:
                            print(
                                f"Retrying chunk {chunk_num}/{total_chunks} (attempt {current_retries + 1} of {MAX_RETRIES}) due to timeout."
                            )
                            logger.warning(
                                f"Retrying chunk {chunk_num}/{total_chunks} (attempt {current_retries + 1} of {MAX_RETRIES}) for session {_current_session_id} due to timeout."
                            )
                            # No need to sleep here as sendText will take time, and ACK_TIMEOUT is the primary wait.
                            continue  # Retry sending the same chunk
                        else:
                            errmsg = f"Aborting session {_current_session_id} after {MAX_RETRIES} failed attempts (timeout) for chunk {chunk_num}/{total_chunks}."
                            print(errmsg)
                            logger.error(errmsg)
                            raise SystemExit(2)  # Abort session

                    # Process received message
                    msg_parts = received_msg_text.split("|")
                    msg_type = msg_parts[0] if len(msg_parts) > 0 else ""
                    msg_session_id_from_payload = (
                        msg_parts[1] if len(msg_parts) > 1 else ""
                    )

                    # Already filtered by onReceive for session ID if using queue, but double check for injected
                    if (
                        use_injected_receiver
                        and msg_session_id_from_payload != _current_session_id
                    ):
                        logger.warning(
                            f"CLI received message for wrong session ID. Expected '{_current_session_id}', got '{msg_session_id_from_payload}'. Msg: '{received_msg_text}'"
                        )
                        # This is an unexpected message, effectively a timeout for the current chunk's ACK.
                        # Let retry logic handle it.
                        current_retries += 1  # Count as a failed attempt
                        if current_retries < MAX_RETRIES:
                            print(
                                f"Retrying chunk {chunk_num}/{total_chunks} (attempt {current_retries + 1} of {MAX_RETRIES}) due to unexpected message for other session."
                            )
                            logger.warning(
                                f"Retrying chunk {chunk_num}/{total_chunks} (attempt {current_retries + 1} of {MAX_RETRIES}) for session {_current_session_id} due to unexpected message for other session: {received_msg_text}"
                            )
                            time.sleep(RETRY_TIMEOUT)  # Wait before retrying
                            continue
                        else:
                            errmsg = f"Aborting session {_current_session_id} after {MAX_RETRIES} failed attempts (unexpected messages) for chunk {chunk_num}/{total_chunks}."
                            print(errmsg)
                            logger.error(errmsg)
                            raise SystemExit(2)

                    # Handle BTC_CHUNK_ACK
                    if msg_type == "BTC_CHUNK_ACK" and len(msg_parts) >= 5:
                        try:
                            msg_chunk_num_int = int(msg_parts[2])
                            msg_status = msg_parts[3]
                            msg_command = msg_parts[4]

                            if msg_chunk_num_int == chunk_num and msg_status == "OK":
                                print(
                                    f"Received ACK for chunk {chunk_num}/{total_chunks}"
                                )
                                logger.info(
                                    f"ACK for chunk {chunk_num}/{total_chunks} in session {_current_session_id}. Server command: {msg_command}"
                                )
                                if (
                                    msg_command == "REQUEST_CHUNK"
                                    and len(msg_parts) >= 6
                                ):
                                    next_chunk_req = msg_parts[5]
                                    if (
                                        next_chunk_req.isdigit()
                                        and int(next_chunk_req) == chunk_num + 1
                                    ):
                                        i += 1  # Move to next chunk
                                        break  # Break from retry loop, proceed to next chunk in outer while loop
                                    else:  # Malformed REQUEST_CHUNK
                                        logger.warning(
                                            f"Malformed REQUEST_CHUNK in ACK for chunk {chunk_num}: '{received_msg_text}'"
                                        )
                                        # Treat as unrecognized, fall through to retry
                                elif msg_command == "ALL_CHUNKS_RECEIVED":
                                    print(
                                        f"All transaction chunks ACKed by server for session {_current_session_id}."
                                    )
                                    logger.info(
                                        f"All transaction chunks ACKed by server for session {_current_session_id}."
                                    )
                                    i = total_chunks  # Signal outer loop to terminate successfully
                                    # Now wait for final transaction broadcast ACK/NACK from server
                                    # This part of the logic was previously in a separate block.
                                    # Let's integrate it here if all chunks are confirmed.
                                    print(
                                        f"Waiting for final transaction broadcast confirmation from server for session {_current_session_id}..."
                                    )
                                    logger.info(
                                        f"Waiting for final TX ACK/NACK for session {_current_session_id}"
                                    )
                                    final_ack_retries = 0
                                    final_tx_confirmed = False
                                    while (
                                        final_ack_retries < MAX_RETRIES
                                    ):  # Use a similar retry for final confirmation
                                        try:
                                            if use_injected_receiver:
                                                final_msg_text = next(message_iterator)
                                            else:
                                                final_msg_text = _message_queue.get(
                                                    block=True, timeout=ACK_TIMEOUT * 2
                                                )  # Longer timeout for broadcast

                                            final_msg_parts = final_msg_text.split("|")
                                            final_msg_type = final_msg_parts[0]
                                            final_msg_session = final_msg_parts[1]

                                            if final_msg_session == _current_session_id:
                                                if (
                                                    final_msg_type == "BTC_ACK"
                                                    and len(final_msg_parts) >= 4
                                                    and final_msg_parts[2] == "SUCCESS"
                                                ):
                                                    txid = (
                                                        final_msg_parts[3].split(
                                                            "TXID:", 1
                                                        )[-1]
                                                        if "TXID:" in final_msg_parts[3]
                                                        else "UNKNOWN_TXID"
                                                    )
                                                    print(
                                                        f"Transaction successfully broadcast by relay. TXID: {txid}"
                                                    )
                                                    logger.info(
                                                        f"Received final BTC_ACK for session {_current_session_id}: {final_msg_text}"
                                                    )
                                                    final_tx_confirmed = True
                                                    break  # from final_ack_retries loop
                                                elif (
                                                    final_msg_type == "BTC_NACK"
                                                    and len(final_msg_parts) >= 3
                                                    and final_msg_parts[2] == "ERROR"
                                                ):
                                                    error_details = "|".join(
                                                        final_msg_parts[3:]
                                                    )
                                                    print(
                                                        f"Relay reported an error broadcasting transaction: {error_details}"
                                                    )
                                                    logger.error(
                                                        f"Received final BTC_NACK for session {_current_session_id}: {error_details}"
                                                    )
                                                    # Even with NACK, all chunks were sent. Exit with specific error for broadcast failure
                                                    raise SystemExit(
                                                        3
                                                    )  # Specific exit code for broadcast failure
                                                else:
                                                    logger.warning(
                                                        f"Received unexpected final message for session {_current_session_id}: {final_msg_text}"
                                                    )
                                                # Fall through to retry if not MAX_RETRIES for final ack
                                        except (
                                            StopIteration,
                                            queue.Empty,
                                        ):  # Timeout for final ACK/NACK
                                            logger.warning(
                                                f"Timeout waiting for final TX ACK/NACK for session {_current_session_id} (attempt {final_ack_retries + 1})"
                                            )
                                        final_ack_retries += 1
                                        if (
                                            final_ack_retries < MAX_RETRIES
                                            and not final_tx_confirmed
                                        ):
                                            print(
                                                f"Retrying wait for final confirmation (attempt {final_ack_retries + 1})"
                                            )
                                            time.sleep(RETRY_TIMEOUT)

                                    if not final_tx_confirmed:
                                        print(
                                            f"No final transaction confirmation received from relay for session {_current_session_id}."
                                        )
                                        logger.error(
                                            f"Timeout or max retries for final TX confirmation for session {_current_session_id}."
                                        )
                                        raise SystemExit(
                                            4
                                        )  # Specific exit code for no final confirmation

                                    # If we got here and final_tx_confirmed is true, it means success.
                                    # The outer loop 'i = total_chunks' will cause graceful exit.
                                    break  # Break from current_retries loop (for the chunk)
                            else:  # ACK for wrong chunk or bad status
                                logger.warning(
                                    f"Received ACK for wrong chunk/status in session {_current_session_id}. Expected chunk {chunk_num}, Got: '{received_msg_text}'"
                                )
                                # Treat as unrecognized, fall through
                        except (ValueError, IndexError) as e:
                            logger.warning(
                                f"Malformed BTC_CHUNK_ACK received in session {_current_session_id}: '{received_msg_text}', Error: {e}"
                            )
                            # Treat as unrecognized, fall through

                    # Handle BTC_NACK
                    elif (
                        msg_type == "BTC_NACK" # Session ID implicitly checked by onReceive or earlier
                    ):
                        # Server NACKs are expected in the format: BTC_NACK|session_id|ERROR|details
                        if len(msg_parts) >= 4 and msg_parts[2] == "ERROR":
                            error_details_parts = msg_parts[3:]
                            error_details = "|".join(error_details_parts)
                            
                            print(f"Session {_current_session_id} failed. Server NACK: {error_details}")
                            logger.error(
                                f"Session {_current_session_id} terminated by server NACK: {error_details}. Original message: {received_msg_text}"
                            )
                            raise SystemExit(3) # Exit code 3 for session failure due to server NACK
                        else:
                            # This NACK format is unexpected from the current server implementation.
                            logger.warning(
                                f"Malformed or unexpected BTC_NACK received in session {_current_session_id}: '{received_msg_text}'. Treating as unrecognized response."
                            )
                            # Allow to fall through to the general 'unrecognized message' handling block, which will retry.
                            pass
                    # Fall-through for unrecognized messages if they made it past initial filters
                    # (e.g. correct session ID but unknown type, or malformed known type)
                    # The onReceive filter should catch messages for other sessions or from other senders.
                    # This block handles messages that *were* for our session and from the server, but not understood.
                    logger.warning(
                        f"Unrecognized or unexpected response for chunk {chunk_num}/{total_chunks} in session {_current_session_id}: '{received_msg_text}'"
                    )
                    print(f"Unrecognized response from server: {received_msg_text}")
                    current_retries += 1
                    if current_retries < MAX_RETRIES:
                        print(
                            f"Retrying chunk {chunk_num}/{total_chunks} (attempt {current_retries + 1} of {MAX_RETRIES}) due to unrecognized response."
                        )
                        logger.warning(
                            f"Retrying chunk {chunk_num}/{total_chunks} (attempt {current_retries + 1} of {MAX_RETRIES}) for session {_current_session_id} due to unrecognized response."
                        )
                        time.sleep(RETRY_TIMEOUT)  # Wait a bit before retrying
                        continue  # Retry sending the same chunk
                    else:
                        errmsg = f"Aborting session {_current_session_id} after {MAX_RETRIES} failed attempts (unrecognized responses) for chunk {chunk_num}/{total_chunks}."
                        print(errmsg)
                        logger.error(errmsg)
                        raise SystemExit(2)  # Abort session
                # Inner while loop (retries) ended. If it broke due to ACK, i is incremented.
                # If it fell through after MAX_RETRIES, an exception was raised.
            # Outer while loop (chunks) ended.
            # If we successfully processed all chunks (i == total_chunks), and final TX was confirmed.
            if i >= total_chunks:  # Should be i == total_chunks if successful
                logger.info(
                    f"All chunks processed and final TX confirmed for session {_current_session_id}."
                )
                print(
                    f"Transaction transmission completed for session {_current_session_id}."
                )
                return 0  # Success!
            else:  # Should not be reached if logic is correct, implies loop exited unexpectedly
                logger.error(
                    f"Exited chunk processing loop prematurely for session {_current_session_id}. Chunks processed: {i}/{total_chunks}"
                )
                print("Error: Transaction processing did not complete as expected.")
                return 1  # Generic error

        except SystemExit as e:  # Catch explicit SystemExits to return their code
            logger.info(
                f"SystemExit caught in cli_main for session {_current_session_id} with code {e.code}"
            )
            return e.code
        except Exception as e:
            logger.error(
                f"Unhandled exception during CLI message processing for session {_current_session_id}: {e}",
                exc_info=True,
            )
            print(f"An unexpected error occurred: {e}")
            return 1  # Generic error
        finally:
            if not use_injected_receiver and not args.dry_run:  # Cleanup for pubsub
                logger.info(
                    f"CLI Unsubscribing from Meshtastic messages for session {_current_session_id}."
                )
                try:
                    # It's possible pubsub or the specific listener isn't robust to multiple unsubscribes
                    # or unsubscribing if never subscribed, though typically it should be.
                    # Adding a check or guard if issues arise.
                    pub.unsubscribe(on_receive_text_message_cli, "meshtastic.receive")
                except Exception as e_unsub:  # Broad catch for unsubscription errors
                    logger.error(
                        f"Error during pub.unsubscribe for session {_current_session_id}: {e_unsub}",
                        exc_info=True,
                    )
            if (
                iface and hasattr(iface, "close") and not injected_iface
            ):  # Close iface if we opened it
                logger.info(
                    f"CLI closing Meshtastic interface for session {_current_session_id}."
                )
                iface.close()
            # Reset globals for potential re-entry (e.g. in tests, though not typical for CLI)
            _message_queue = None
            _current_session_id = None
            _expected_sender_node_id = None
            logger.info(
                f"CLI main execution finished for session (was {_current_session_id})."
            )

    # This part for Story 6.4 is now integrated into the main loop's ALL_CHUNKS_RECEIVED path.
    # So, we can remove the old separate block if injected_message_receiver is not None.
    # If using injected_message_receiver, it's assumed the generator handles the final ACK/NACK if needed.
    # For our pubsub path, the main loop now handles it.

    # The original script had a final `return 0` here.
    # If dry_run, it returned 0 earlier.
    # If not dry_run, the try/finally block now handles returns (0 for success, non-zero for errors).
    # If somehow execution reaches here and it wasn't a dry run, it's an unplanned path.
    if not args.dry_run:
        logger.error(
            "Execution reached an unexpected point after main processing loop without returning a status."
        )
        return 1  # Should have returned within the loop or its exception handlers.
    return 0  # Default for dry_run if it didn't exit earlier (it should have)


def main():
    """CLI entry point."""
    import sys

    exit_status = 0
    try:
        exit_status = cli_main()
    except ValueError:
        sys.exit(1)
    except RuntimeError:
        sys.exit(2)
    except Exception:
        sys.exit(3)
    sys.exit(exit_status)


if __name__ == "__main__":
    main()
