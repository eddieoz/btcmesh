from __future__ import annotations

import time
from typing import Dict, Optional, Tuple, List, Any

from core.logger_setup import server_logger  # Assuming a logger is available

# Constants for chunk parsing
CHUNK_PREFIX = "BTC_TX|"
CHUNK_PARTS_DELIMITER = "|"
CHUNK_INDEX_TOTAL_DELIMITER = "/"

# Default timeout for reassembly sessions in seconds
DEFAULT_REASSEMBLY_TIMEOUT_SECONDS = 5 * 60  # 5 minutes


class ReassemblyError(Exception):
    """Custom exception for reassembly errors."""

    pass


class MismatchedTotalChunksError(ReassemblyError):
    """Raised when total_chunks differs for the same session."""

    pass


class DuplicateChunkError(ReassemblyError):
    """Raised when a duplicate chunk is received."""

    pass


class InvalidChunkFormatError(ReassemblyError):
    """Raised when a chunk format is invalid."""

    pass


class TransactionReassembler:
    """
    Manages the reassembly of chunked Bitcoin transaction messages received via Meshtastic.
    """

    def __init__(self, timeout_seconds: int = DEFAULT_REASSEMBLY_TIMEOUT_SECONDS):
        """
        Initializes the TransactionReassembler.

        Args:
            timeout_seconds: The time in seconds before an incomplete reassembly session
                             is considered timed out and discarded.
        """
        self.timeout_seconds = timeout_seconds
        # Structure for active_sessions:
        # {
        #   sender_id_tuple_key: {
        #       tx_session_id: {
        #           "chunks": {chunk_num: hex_payload_part},
        #           "total_chunks": Optional[int],
        #           "last_update_time": float,
        #           "sender_id_str": str # For logging/reply purposes
        #       }
        #   }
        # }
        # sender_id_tuple_key is (sender_id_type_str, sender_id_value) e.g. ('int', 12345) or ('str', '!abcdef')
        # This is to handle different types of sender_ids from Meshtastic packets
        self.active_sessions: Dict[Any, Dict[str, Dict[str, Any]]] = {}
        server_logger.info(
            f"TransactionReassembler initialized with timeout: {timeout_seconds}s"
        )

    def _parse_chunk(self, message_text: str) -> Tuple[str, int, int, str]:
        """
        Parses a raw message string to extract transaction chunk components.

        Format: "BTC_TX|<tx_session_id>|<chunk_num>/<total_chunks>|<hex_payload_part>"

        Args:
            message_text: The raw text message received.

        Returns:
            A tuple containing (tx_session_id, chunk_num, total_chunks, hex_payload_part).

        Raises:
            InvalidChunkFormatError: If the message_text does not conform to the expected format.
        """
        if not message_text.startswith(CHUNK_PREFIX):
            raise InvalidChunkFormatError(f"Message does not start with {CHUNK_PREFIX}")

        parts = message_text[len(CHUNK_PREFIX) :].split(CHUNK_PARTS_DELIMITER)
        if len(parts) != 3:
            raise InvalidChunkFormatError(
                f"Message does not have 3 parts after prefix: {parts}"
            )

        tx_session_id = parts[0]
        chunk_index_part = parts[1]
        hex_payload_part = parts[2]

        if not tx_session_id:
            raise InvalidChunkFormatError("tx_session_id is empty.")
        if (
            not hex_payload_part
        ):  # Allow empty payload for last chunk if needed by protocol?
            # For now, assume payload must exist. Consider if it needs to be optional.
            server_logger.warning(
                f"[Session: {tx_session_id}] Received chunk with empty payload part."
            )
            # Depending on strictness, could raise InvalidChunkFormatError here.

        try:
            chunk_num_str, total_chunks_str = chunk_index_part.split(
                CHUNK_INDEX_TOTAL_DELIMITER
            )
            chunk_num = int(chunk_num_str)
            total_chunks = int(total_chunks_str)
        except ValueError:
            raise InvalidChunkFormatError(
                f"Invalid chunk_num/total_chunks format: {chunk_index_part}"
            )

        if not (0 < chunk_num <= total_chunks and total_chunks > 0):
            raise InvalidChunkFormatError(
                f"Invalid chunk numbering: {chunk_num}/{total_chunks}"
            )

        return tx_session_id, chunk_num, total_chunks, hex_payload_part

    def add_chunk(self, sender_id: Any, message_text: str) -> Optional[str]:
        """
        Adds a received transaction chunk to the appropriate reassembly session.

        If all chunks for a transaction are received, it reassembles them and
        returns the complete hexadecimal transaction string.

        Args:
            sender_id: The unique identifier of the message sender.
                    Can be an int (node_num) or str (node_id string like !hex).
                    Used as the session key for tracking.
            message_text: The raw text message content for the chunk.

        Returns:
            The reassembled hexadecimal transaction string if complete, otherwise None.
            Can also return None if an error occurs during processing the chunk (logged).

        Raises:
            ReassemblyError (or its subclasses) for specific, potentially recoverable errors
            that the caller might want to handle (e.g., to send a NACK).
            Other exceptions are logged and result in None being returned.
        """
        current_time = time.time()
        # Normalize sender_id to a consistent key for the dictionary
        # (e.g. if int, use (int, value), if str, use (str, value))
        # This helps if Meshtastic packet sometimes gives int, sometimes string for same node.
        # For now, we assume the caller (on_receive_text_message) provides a consistent
        # sender_id (e.g. the integer node_num if available, else the string node ID).
        # Let's just use sender_id directly as provided by on_receive_text_message's buffer_key logic.
        session_key = sender_id

        try:
            tx_session_id, chunk_num, total_chunks, hex_payload_part = (
                self._parse_chunk(message_text)
            )
        except InvalidChunkFormatError as e:
            server_logger.error(
                f"Invalid chunk format from sender {sender_id}: {e}. Message: '{message_text}'"
            )
            # Potentially raise e here if the caller should handle it for NACK.
            # For now, just logging and returning None, or let the caller handle.
            raise  # Reraise for the caller to potentially NACK.

        log_ctx = f"[Sender: {sender_id}, Session: {tx_session_id}]"

        if session_key not in self.active_sessions:
            self.active_sessions[session_key] = {}

        sender_sessions = self.active_sessions[session_key]

        if tx_session_id not in sender_sessions:
            server_logger.info(
                f"{log_ctx} New reassembly session started. Expecting {total_chunks} chunks."
            )
            sender_sessions[tx_session_id] = {
                "chunks": {},
                "total_chunks": total_chunks,
                "last_update_time": current_time,
                "sender_id_str": str(sender_id),  # Store original sender_id for replies
            }

        session_data = sender_sessions[tx_session_id]

        # Check for consistency in total_chunks
        if session_data["total_chunks"] != total_chunks:
            error_msg = (
                f"{log_ctx} Mismatched total_chunks. Expected "
                f"{session_data['total_chunks']}, got {total_chunks}. Discarding session."
            )
            server_logger.error(error_msg)
            del sender_sessions[tx_session_id]
            raise MismatchedTotalChunksError(error_msg)

        # Check for duplicate chunk
        if chunk_num in session_data["chunks"]:
            # Optional: could compare payloads to see if it's a true duplicate or retransmission of different data
            # For now, assume same chunk_num for same session_id is a duplicate to ignore or flag.
            # Story 2.1 Scenario: Duplicate chunk implies ignoring it.
            server_logger.warning(
                f"{log_ctx} Duplicate chunk {chunk_num}/{total_chunks} received. Ignoring."
            )
            # Not raising DuplicateChunkError as per story requirement to ignore.
            # If strict error handling is needed for duplicates (e.g. NACK), raise here.
            return None  # Or raise DuplicateChunkError if caller should be aware

        session_data["chunks"][chunk_num] = hex_payload_part
        session_data["last_update_time"] = current_time
        server_logger.debug(
            f"{log_ctx} Added chunk {chunk_num}/{total_chunks}. "
            f"Collected {len(session_data['chunks'])} chunks."
        )

        # Check if all chunks are received
        if len(session_data["chunks"]) == session_data["total_chunks"]:
            server_logger.info(
                f"{log_ctx} All {total_chunks} chunks received. Attempting reassembly."
            )
            # Reassemble in correct order
            reassembled_hex = ""
            for i in range(1, total_chunks + 1):
                if i not in session_data["chunks"]:
                    # This should not happen if len matches total_chunks and all chunk_nums are valid
                    # but as a safeguard:
                    error_msg = f"{log_ctx} Reassembly failed: Missing chunk {i} despite expected completion."
                    server_logger.error(error_msg)
                    del sender_sessions[tx_session_id]  # Clean up inconsistent session
                    raise ReassemblyError(error_msg)  # Should be a specific error type

                reassembled_hex += session_data["chunks"][i]

            server_logger.info(f"{log_ctx} Reassembly successful.")
            # Clean up completed session
            del sender_sessions[tx_session_id]
            if not sender_sessions:  # If no more sessions for this sender
                del self.active_sessions[session_key]
            return reassembled_hex

        return None  # Not all chunks received yet

    def cleanup_stale_sessions(self) -> List[Dict[str, str]]:
        """
        Iterates through active reassembly sessions, removes any that have timed out,
        and returns a list of details for NACK messages for timed-out sessions.

        Returns:
            A list of dictionaries, where each dictionary contains:
            {'sender_id_str': str, 'tx_session_id': str, 'error_message': str}
            for each session that timed out.
        """
        current_time = time.time()
        timed_out_sessions_for_nack: List[Dict[str, str]] = []
        stale_sender_tx_session_pairs_to_remove: List[Tuple[Any, str]] = []

        active_session_keys = list(self.active_sessions.keys())
        for session_key in active_session_keys:
            sender_sessions = self.active_sessions[session_key]
            active_tx_ids = list(sender_sessions.keys())

            for tx_session_id in active_tx_ids:
                session_data = sender_sessions[tx_session_id]
                if (
                    current_time - session_data["last_update_time"]
                    > self.timeout_seconds
                ):
                    original_sender_id_str = session_data.get(
                        "sender_id_str", str(session_key)  # Fallback
                    )
                    error_detail = (
                        f"Reassembly timeout after {self.timeout_seconds}s. "
                        f"Received {len(session_data['chunks'])}/"
                        f"{session_data['total_chunks']} chunks."
                    )
                    server_logger.warning(
                        f"[Sender: {original_sender_id_str}, Session: {tx_session_id}] "
                        f"{error_detail} Discarding."
                    )
                    timed_out_sessions_for_nack.append(
                        {
                            "sender_id_str": original_sender_id_str,
                            "tx_session_id": tx_session_id,
                            "error_message": "Reassembly timeout",
                        }
                    )
                    stale_sender_tx_session_pairs_to_remove.append(
                        (session_key, tx_session_id)
                    )

        for session_key, tx_session_id in stale_sender_tx_session_pairs_to_remove:
            if (
                session_key in self.active_sessions
                and tx_session_id in self.active_sessions[session_key]
            ):
                del self.active_sessions[session_key][tx_session_id]
                if not self.active_sessions[
                    session_key
                ]:  # If this sender has no more sessions
                    del self.active_sessions[session_key]

        if timed_out_sessions_for_nack:
            server_logger.info(
                f"Identified {len(timed_out_sessions_for_nack)} stale reassembly sessions for cleanup and NACK."
            )
        return timed_out_sessions_for_nack

    # Placeholder for a method that might be needed to get session details for NACKs
    def get_session_sender_id_str(
        self, session_key: Any, tx_session_id: str
    ) -> Optional[str]:
        """Retrieves the original sender ID string for a session, if active."""
        if (
            session_key in self.active_sessions
            and tx_session_id in self.active_sessions[session_key]
        ):
            return self.active_sessions[session_key][tx_session_id].get("sender_id_str")
        return None

    def get_active_sessions_info(self) -> List[Dict[str, Any]]:
        """
        Returns information about all active reassembly sessions for GUI display.

        Returns:
            A list of dictionaries, each containing:
            {
                'session_id': str,
                'sender': str,
                'chunks_received': int,
                'total_chunks': int,
                'elapsed_seconds': float
            }
        """
        current_time = time.time()
        sessions_info = []

        for session_key, sender_sessions in self.active_sessions.items():
            for tx_session_id, session_data in sender_sessions.items():
                elapsed = current_time - session_data.get("last_update_time", current_time)
                sessions_info.append({
                    'session_id': tx_session_id,
                    'sender': session_data.get("sender_id_str", str(session_key)),
                    'chunks_received': len(session_data.get("chunks", {})),
                    'total_chunks': session_data.get("total_chunks", 0),
                    'elapsed_seconds': elapsed,
                })

        return sessions_info
