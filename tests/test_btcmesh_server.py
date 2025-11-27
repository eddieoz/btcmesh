import unittest
from unittest.mock import MagicMock, call, patch, Mock

# import logging # Unused
import sys

# Import the function to be tested
from btcmesh_server import (
    initialize_meshtastic_interface,
    on_receive_text_message,
    send_meshtastic_reply,
    _format_node_id,
)

# server_logger will be patched using its path in btcmesh_server

from core.reassembler import (
    InvalidChunkFormatError,
    MismatchedTotalChunksError,
    ReassemblyError,
    CHUNK_PREFIX,  # Import CHUNK_PREFIX directly
    TransactionReassembler,
)

# Import the module to be tested AFTER mocks are in sys.modules
# import btcmesh_server # Redundant, direct imports below are used
# from btcmesh_server import (                             # REMOVE THIS LINE
#     # initialize_meshtastic_interface,  # Redefined, covered by top import # REMOVE THIS LINE
#     # on_receive_text_message,  # Redefined, covered by top import # REMOVE THIS LINE
#     # _format_node_id, # Now imported from top-level from btcmesh_server # REMOVE THIS LINE
#     # send_meshtastic_reply,  # Redefined, covered by top import # REMOVE THIS LINE
#     # _extract_session_id_from_raw_chunk, # Unused # REMOVE THIS LINE
# ) # REMOVE THIS LINE


# Define a class to be used as a spec for the Meshtastic interface mock
# in TestMessageHandling. This helps ensure the mock behaves like a real interface.
# class MockSerialInterfaceForMessageHandling: # Commenting out for now
#     """A mock class for specifying the interface of a Meshtastic SerialInterface.
#     Attributes and methods used by on_receive_text_message should be defined here.
#     """
#     def __init__(self, my_node_num=0xabcdef, devicePath='/dev/mock'):
#         self.myInfo = MagicMock()
#         self.myInfo.my_node_num = my_node_num
#         self.devicePath = devicePath
#         # Add other attributes/methods if on_receive_text_message uses them
#         # e.g. self.nodes = {}


class TestMeshtasticInitialization(unittest.TestCase):

    def setUp(self):
        # Mock the Meshtastic library and its components in sys.modules
        # This allows the imports inside initialize_meshtastic_interface to
        # resolve to our mocks
        self.mock_meshtastic_module = MagicMock()
        self.mock_serial_interface_module = MagicMock()

        # This is the class we want to control (e.g., SerialInterface)
        self.MockMeshtasticSerialInterfaceClass = MagicMock()
        self.mock_serial_interface_module.SerialInterface = (
            self.MockMeshtasticSerialInterfaceClass
        )

        self.mock_meshtastic_module.serial_interface = self.mock_serial_interface_module

        # Define mock exceptions that will be imported by the function under test
        self.MockNoDeviceError = type("NoDeviceError", (Exception,), {})
        self.MockMeshtasticError = type("MeshtasticError", (Exception,), {})
        self.mock_meshtastic_module.NoDeviceError = self.MockNoDeviceError
        self.mock_meshtastic_module.MeshtasticError = self.MockMeshtasticError

        # Mock PortNum if it were to be used directly from
        # meshtastic.mesh_pb2 in the callback
        self.mock_mesh_pb2_module = MagicMock()
        self.MockPortNum = MagicMock()
        # If comparing with actual enum values:
        # self.MockPortNum.TEXT_MESSAGE_APP = 1 # or whatever value it has
        # For now, the code uses string comparison 'TEXT_MESSAGE_APP' for
        # portnum in decoded packet
        self.mock_mesh_pb2_module.PortNum = self.MockPortNum

        # Patch sys.modules so that 'import meshtastic' and its sub-imports
        # get our mocks
        self.sys_modules_patcher = patch.dict(
            sys.modules,
            {
                "meshtastic": self.mock_meshtastic_module,
                "meshtastic.serial_interface": self.mock_serial_interface_module,
                "meshtastic.mesh_pb2": self.mock_mesh_pb2_module,  # For PortNum
                "pubsub": MagicMock(),  # Mock pubsub as it's imported in main
                "dotenv": MagicMock(),  # Mock dotenv used by config_loader
            },
        )
        self.sys_modules_patcher.start()

        # Patch the logger used within btcmesh_server
        self.logger_patcher = patch("btcmesh_server.server_logger", MagicMock())
        self.mock_logger = self.logger_patcher.start()

        # If btcmesh_server.server_logger was used directly (it is),
        # we can capture its original state if needed
        # For these tests, we mostly care about asserting calls on mock_logger.

        # Patch the config loader used by initialize_meshtastic_interface
        self.config_loader_patcher = patch("btcmesh_server.get_meshtastic_serial_port")
        self.mock_get_serial_port_config = self.config_loader_patcher.start()
        # Default behavior: no port configured, so auto-detect is attempted
        self.mock_get_serial_port_config.return_value = None

        # Patch load_app_config in btcmesh_server module scope if called there
        # and also in core.config_loader if tests directly/indirectly call it.
        self.load_config_patcher_server = patch(
            "btcmesh_server.load_app_config", MagicMock()
        )
        self.load_config_patcher_server.start()

        self.load_config_patcher_core = patch(
            "core.config_loader.load_app_config", MagicMock()
        )
        self.load_config_patcher_core.start()

    def tearDown(self):
        self.sys_modules_patcher.stop()
        self.logger_patcher.stop()
        self.config_loader_patcher.stop()
        self.load_config_patcher_server.stop()
        self.load_config_patcher_core.stop()

    def test_initialize_meshtastic_successful_autodetect(self):
        """Test successful init when no port is specified (arg/config) -> auto."""
        # Explicitly ensure config returns None
        self.mock_get_serial_port_config.return_value = None
        mock_iface_instance = self.MockMeshtasticSerialInterfaceClass.return_value
        mock_iface_instance.devicePath = "/dev/ttyUSB0"  # Example path
        mock_iface_instance.myInfo = MagicMock()
        mock_iface_instance.myInfo.my_node_num = 0xDEADBEEF

        iface = initialize_meshtastic_interface()  # No port argument

        self.assertIsNotNone(iface)
        # Called with no devPath
        self.MockMeshtasticSerialInterfaceClass.assert_called_once_with()
        self.mock_get_serial_port_config.assert_called_once()  # Check config
        expected_log_calls = [
            call.info("Attempting to initialize Meshtastic interface (auto-detect)..."),
            call.info(
                f"Meshtastic interface initialized successfully. Device: "
                f"{mock_iface_instance.devicePath}, My Node Num: !deadbeef"
            ),
        ]
        self.mock_logger.info.assert_has_calls(expected_log_calls, any_order=False)

    def test_initialize_meshtastic_successful_with_config_port(self):
        """Test successful init when port is provided by .env config."""
        configured_port = "/dev/ttyS0"
        self.mock_get_serial_port_config.return_value = configured_port
        mock_iface_instance = self.MockMeshtasticSerialInterfaceClass.return_value
        mock_iface_instance.devicePath = configured_port
        mock_iface_instance.myInfo = MagicMock()
        mock_iface_instance.myInfo.my_node_num = "!configPortNode"

        iface = initialize_meshtastic_interface()  # No port arg, use config

        self.assertIsNotNone(iface)
        self.MockMeshtasticSerialInterfaceClass.assert_called_once_with(
            devPath=configured_port
        )
        self.mock_get_serial_port_config.assert_called_once()
        expected_log_calls = [
            call.info(
                f"Attempting to initialize Meshtastic interface on port "
                f"{configured_port}..."
            ),
            call.info(
                f"Meshtastic interface initialized successfully. Device: "
                f"{mock_iface_instance.devicePath}, My Node Num: !configPortNode"
            ),
        ]
        self.mock_logger.info.assert_has_calls(expected_log_calls, any_order=False)

    def test_initialize_meshtastic_successful_with_override_port(self):
        """Test successful init when port is provided by arg (overrides config)."""
        override_port = "/dev/ttyACM1"
        # Simulate a different configured port
        self.mock_get_serial_port_config.return_value = "/dev/ttyS0"

        mock_iface_instance = self.MockMeshtasticSerialInterfaceClass.return_value
        mock_iface_instance.devicePath = override_port
        mock_iface_instance.myInfo = MagicMock()
        mock_iface_instance.myInfo.my_node_num = "!overrideNode"

        # Port argument overrides config
        iface = initialize_meshtastic_interface(port=override_port)

        self.assertIsNotNone(iface)
        self.MockMeshtasticSerialInterfaceClass.assert_called_once_with(
            devPath=override_port
        )
        # Config should not be called if port arg is present
        self.mock_get_serial_port_config.assert_not_called()
        expected_log_calls = [
            call.info(
                f"Attempting to initialize Meshtastic interface on port "
                f"{override_port}..."
            ),
            call.info(
                f"Meshtastic interface initialized successfully. Device: "
                f"{mock_iface_instance.devicePath}, My Node Num: !overrideNode"
            ),
        ]
        self.mock_logger.info.assert_has_calls(expected_log_calls, any_order=False)

    def test_initialize_meshtastic_successful_with_str_node_id(self):
        """Test init when my_node_num is str like !<hex> (auto-detect path)."""
        self.mock_get_serial_port_config.return_value = None  # Auto-detect
        mock_iface_instance = self.MockMeshtasticSerialInterfaceClass.return_value
        mock_iface_instance.devicePath = "/dev/ttyUSB1"
        mock_iface_instance.myInfo = MagicMock()
        # Example string node ID
        mock_iface_instance.myInfo.my_node_num = "!abcdef12"

        iface = initialize_meshtastic_interface()
        self.assertIsNotNone(iface)
        self.MockMeshtasticSerialInterfaceClass.assert_called_once_with()  # Auto
        self.mock_get_serial_port_config.assert_called_once()
        expected_log_calls = [
            call.info("Attempting to initialize Meshtastic interface (auto-detect)..."),
            call.info(
                f"Meshtastic interface initialized successfully. Device: "
                f"{mock_iface_instance.devicePath}, My Node Num: !abcdef12"
            ),
        ]
        self.mock_logger.info.assert_has_calls(expected_log_calls, any_order=False)

    def test_initialize_meshtastic_no_device_error_autodetect(self):
        self.mock_get_serial_port_config.return_value = None  # Auto-detect
        self.MockMeshtasticSerialInterfaceClass.side_effect = self.MockNoDeviceError(
            "No Meshtastic device found mock"
        )
        iface = initialize_meshtastic_interface()
        self.assertIsNone(iface)
        self.MockMeshtasticSerialInterfaceClass.assert_called_once_with()
        self.mock_get_serial_port_config.assert_called_once()
        self.mock_logger.error.assert_any_call(
            "No Meshtastic device found. Ensure it is connected and "
            "drivers are installed."
        )
        self.mock_logger.info.assert_called_with(
            "Attempting to initialize Meshtastic interface (auto-detect)..."
        )

    def test_initialize_meshtastic_no_device_error_with_config_port(self):
        configured_port = "/dev/ttyFAIL"
        self.mock_get_serial_port_config.return_value = configured_port
        self.MockMeshtasticSerialInterfaceClass.side_effect = self.MockNoDeviceError(
            "No Meshtastic device found mock"
        )
        iface = initialize_meshtastic_interface()
        self.assertIsNone(iface)
        self.MockMeshtasticSerialInterfaceClass.assert_called_once_with(
            devPath=configured_port
        )
        self.mock_get_serial_port_config.assert_called_once()
        self.mock_logger.error.assert_any_call(
            "No Meshtastic device found. Ensure it is connected and "
            "drivers are installed."
        )
        self.mock_logger.info.assert_called_with(
            f"Attempting to initialize Meshtastic interface on port "
            f"{configured_port}..."
        )

    def test_initialize_meshtastic_generic_meshtastic_error(self):
        # This will use auto-detect path due to setUp
        error_message = "A generic Meshtastic error mock"
        self.MockMeshtasticSerialInterfaceClass.side_effect = self.MockMeshtasticError(
            error_message
        )
        iface = initialize_meshtastic_interface()
        self.assertIsNone(iface)
        self.MockMeshtasticSerialInterfaceClass.assert_called_once_with()
        self.mock_get_serial_port_config.assert_called_once()
        self.mock_logger.error.assert_any_call(
            f"Meshtastic library error during initialization: {error_message}"
        )
        self.mock_logger.info.assert_called_with(
            "Attempting to initialize Meshtastic interface (auto-detect)..."
        )

    def test_initialize_meshtastic_unexpected_error(self):
        # This will use auto-detect path
        self.mock_get_serial_port_config.return_value = None
        error_message = "A totally unexpected error!"
        self.MockMeshtasticSerialInterfaceClass.side_effect = RuntimeError(
            error_message
        )

        iface = initialize_meshtastic_interface()
        self.assertIsNone(iface)
        self.mock_logger.error.assert_any_call(
            f"An unexpected error occurred during Meshtastic initialization: {error_message}",
            exc_info=True,
        )

    @unittest.skip("Temporarily skipped")
    def test_initialize_meshtastic_import_error(self):
        # Manipulate sys.modules so config loader won't affect it directly
        # regarding meshtastic import
        self.sys_modules_patcher.stop()
        temp_sys_modules_patch = patch.dict(
            sys.modules,
            {k: v for k, v in sys.modules.items() if not k.startswith("meshtastic")},
        )
        temp_sys_modules_patch.start()

        # Stop config loader patch if it interferes with ImportError for meshtastic
        self.config_loader_patcher.stop()
        iface = initialize_meshtastic_interface()
        self.config_loader_patcher.start()  # Restart for other tests

        temp_sys_modules_patch.stop()
        self.sys_modules_patcher.start()
        self.assertIsNone(iface)
        self.mock_logger.error.assert_any_call(
            "Meshtastic library not found. Please install it "
            "(e.g., pip install meshtastic)."
        )


class TestMessageHandling(unittest.TestCase):
    def setUp(self):
        # Patch the logger
        self.patcher_logger = patch("btcmesh_server.server_logger", MagicMock())
        self.mock_logger = self.patcher_logger.start()

        # Patch the transaction reassembler instance that is used in btcmesh_server
        self.patcher_reassembler = patch(
            "btcmesh_server.transaction_reassembler", autospec=True
        )
        self.mock_reassembler = self.patcher_reassembler.start()
        # Set CHUNK_PREFIX on the mock reassembler instance.
        # This is NOT used by the SUT's startswith() check, which uses a direct import.
        self.mock_reassembler.CHUNK_PREFIX = CHUNK_PREFIX

        # Patch send_meshtastic_reply
        self.patcher_send_reply = patch(
            "btcmesh_server.send_meshtastic_reply", autospec=True
        )
        self.mock_send_reply = self.patcher_send_reply.start()

        # Patch _extract_session_id_from_raw_chunk
        self.patcher_extract_id = patch(
            "btcmesh_server._extract_session_id_from_raw_chunk", autospec=True
        )
        self.mock_extract_id = self.patcher_extract_id.start()

        # Create a mock Meshtastic interface instance
        self.mock_iface = MagicMock()
        self.mock_iface.myInfo = MagicMock()
        self.mock_iface.myInfo.my_node_num = 0xABCDEF  # Server's node number

    def tearDown(self):
        self.patcher_logger.stop()
        self.patcher_reassembler.stop()
        self.patcher_send_reply.stop()
        self.patcher_extract_id.stop()

    def test_receive_standard_text_message_for_server(self):
        """Test receiving a standard (non-BTC_TX) text message for the server."""
        sender_node_id_int = 0xFEEDFACE
        sender_node_id_str_formatted = _format_node_id(
            sender_node_id_int
        )  # "!feedface"

        server_node_id_str_formatted = "!abcdef"  # Our server's ID, string formatted

        message_text = "Hello from Meshtastic!"

        # Packet construction for a direct message to the server
        # Using top-level 'toId' (string) which on_receive_text_message checks first.
        packet = {
            "from": sender_node_id_int,
            "toId": server_node_id_str_formatted,  # String formatted node ID
            "decoded": {
                # 'to': server_node_id_int, # Not strictly needed if toId is present and used first
                "portnum": "TEXT_MESSAGE_APP",
                "text": message_text,
            },
            "id": "packet_std_text",
            "channel": 0,  # Indicates a direct message
        }

        on_receive_text_message(packet, self.mock_iface)

        # For a standard text message, these should NOT be called.
        self.mock_reassembler.add_chunk.assert_not_called()
        self.mock_send_reply.assert_not_called()

    @unittest.skip("Temporarily skipped")
    def test_receive_btc_tx_chunk_partial_no_reassembly(self):
        """Test receiving a BTC_TX chunk that is part of a larger transaction (no full reassembly yet)."""
        sender_node_id_int = 0x54321
        # sender_node_id_str_formatted = _format_node_id(sender_node_id_int) # For logging, if used

        server_node_id_str_formatted = "!abcdef"  # Our server's ID

        session_id = "sess2_partial"
        message_text = f"{CHUNK_PREFIX}{session_id}|1/2|partial_payload_data"

        # Simulate that add_chunk will be called but won't return a full transaction yet
        self.mock_reassembler.add_chunk.return_value = None

        packet = {
            "from": sender_node_id_int,
            "toId": server_node_id_str_formatted,  # Message for our server
            "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": message_text},
            "id": "packet_btc_partial",
            "channel": 0,
        }

        on_receive_text_message(packet, self.mock_iface)

        # Crucial assertions for this test:
        # 1. add_chunk should be called with the correct sender ID and message text.
        #    The sender_id passed to add_chunk by on_receive_text_message is the raw integer packet['from'].
        self.mock_reassembler.add_chunk.assert_called_once_with(
            sender_node_id_int, message_text
        )

        # 2. No reply should be sent for a partial (non-error) chunk reception.
        self.mock_send_reply.assert_not_called()

        # Optional: Minimal log assertion to confirm it took the BTC_TX path if needed,
        # but primary focus is on add_chunk call.
        # Example log: server_logger.info(f"Potential BTC transaction chunk from {sender_id_str_formatted}. Processing...")
        # self.mock_logger.info.assert_any_call(
        #     f"Potential BTC transaction chunk from {sender_node_id_str_formatted}. Processing..."
        # )

    @unittest.skip("Temporarily skipped")
    def test_receive_btc_tx_chunk_success_reassembly(self):
        """Test receiving a BTC_TX chunk that leads to successful reassembly and triggers broadcast logic."""
        sender_node_id_int = 0x12345  # Example sender
        server_node_id_str_formatted = "!abcdef"  # Our server's ID

        session_id = "sess_success_reassembly"
        # Simulate a single chunk transaction for simplicity, or the last chunk
        message_text = f"{CHUNK_PREFIX}{session_id}|1/1|deadbeefcafebabe"
        reassembled_hex_payload = "deadbeefcafebabe"  # Expected result from reassembler

        # Configure the mock reassembler to return the complete payload
        self.mock_reassembler.add_chunk.return_value = reassembled_hex_payload
        # Patch _extract_session_id_from_raw_chunk to return the correct session_id
        self.mock_extract_id.return_value = session_id

        packet = {
            "from": sender_node_id_int,
            "toId": server_node_id_str_formatted,
            "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": message_text},
            "id": "packet_btc_success",
            "channel": 0,
        }

        on_receive_text_message(packet, self.mock_iface)

        # 1. add_chunk should be called correctly.
        self.mock_reassembler.add_chunk.assert_called_once_with(
            sender_node_id_int, message_text
        )

        # 2. Since there is no RPC connection, a NACK should be sent for broadcast failure.
        expected_nack_msg = (
            f"BTC_NACK|{session_id}|ERROR|Broadcast failed: No RPC connection"
        )
        self.mock_send_reply.assert_called_once_with(
            self.mock_iface, "!12345", expected_nack_msg, session_id
        )

        # 3. Assert the log message for successful reassembly (optional, for completeness).
        sender_node_id_str_formatted_for_log = _format_node_id(sender_node_id_int)
        expected_log_reassembly_success = (
            f"[Sender: {sender_node_id_str_formatted_for_log}] Successfully reassembled transaction: "
            f"{reassembled_hex_payload[:50]}... (len: {len(reassembled_hex_payload)})"
        )
        self.mock_logger.info.assert_any_call(expected_log_reassembly_success)

    @unittest.skip("Temporarily skipped")
    def test_receive_btc_tx_chunk_invalid_format_sends_nack(self):
        """Test that InvalidChunkFormatError from add_chunk results in a NACK."""
        sender_node_id_int = 0x67890  # Example sender
        server_node_id_str_formatted = "!abcdef"  # Our server's ID

        session_id_for_nack = "sess_invalid_fmt"
        # This message format might be parsable up to a point by add_chunk before it determines the error
        # or _parse_chunk within add_chunk might raise it.
        # For this test, we assume add_chunk itself is the source of the exception due to internal parsing.
        malformed_message_text = (
            f"{CHUNK_PREFIX}{session_id_for_nack}|bad_chunk_format|payload"
        )
        exception_message = "Test: Invalid chunk format detected by reassembler"

        # Configure mocks
        self.mock_reassembler.add_chunk.side_effect = InvalidChunkFormatError(
            exception_message
        )
        self.mock_extract_id.return_value = (
            session_id_for_nack  # Used for NACK message construction
        )

        packet = {
            "from": sender_node_id_int,
            "toId": server_node_id_str_formatted,
            "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": malformed_message_text},
            "id": "packet_btc_invalid_format",
            "channel": 0,
        }

        on_receive_text_message(packet, self.mock_iface)

        # 1. add_chunk should be called.
        self.mock_reassembler.add_chunk.assert_called_once_with(
            sender_node_id_int, malformed_message_text
        )

        # 2. _extract_session_id_from_raw_chunk should be called for the NACK.
        self.mock_extract_id.assert_called_once_with(malformed_message_text)

        # 3. A NACK should be sent.
        sender_id_str_for_reply = _format_node_id(sender_node_id_int)
        # NACK format: BTC_NACK|<tx_session_id>|ERROR|<ErrorTypeString>: <exception_details>
        # ErrorTypeString for InvalidChunkFormatError is "Invalid ChunkFormat"
        expected_nack_detail = f"Invalid ChunkFormat: {exception_message}"
        expected_nack_message = (
            f"BTC_NACK|{session_id_for_nack}|ERROR|{expected_nack_detail}"
        )

        self.mock_send_reply.assert_called_once_with(
            self.mock_iface,
            sender_id_str_for_reply,
            expected_nack_message,
            session_id_for_nack,
        )

        # 4. Assert the error log.
        expected_error_log = (
            f"[Sender: {sender_id_str_for_reply}, Session: {session_id_for_nack}] "
            f"Reassembly error: {exception_message}. Sending NACK."
        )
        self.mock_logger.error.assert_any_call(expected_error_log)

    @unittest.skip("Temporarily skipped")
    def test_receive_btc_tx_chunk_mismatched_total_sends_nack(self):
        """Test that MismatchedTotalChunksError from add_chunk results in a NACK."""
        sender_node_id_int = 0xABCDE  # Example sender
        server_node_id_str_formatted = "!abcdef"  # Our server's ID

        session_id_for_nack = "sess_mismatch_total"
        # A valid-looking chunk message; the error comes from reassembler's state
        chunk_message_text = (
            f"{CHUNK_PREFIX}{session_id_for_nack}|1/3|payload_part_for_mismatch"
        )
        exception_message = "Test: Mismatched total chunks detected by reassembler"

        # Configure mocks
        self.mock_reassembler.add_chunk.side_effect = MismatchedTotalChunksError(
            exception_message
        )
        self.mock_extract_id.return_value = session_id_for_nack  # Used for NACK

        packet = {
            "from": sender_node_id_int,
            "toId": server_node_id_str_formatted,
            "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": chunk_message_text},
            "id": "packet_btc_mismatch_total",
            "channel": 0,
        }

        on_receive_text_message(packet, self.mock_iface)

        # 1. add_chunk should be called.
        self.mock_reassembler.add_chunk.assert_called_once_with(
            sender_node_id_int, chunk_message_text
        )

        # 2. _extract_session_id_from_raw_chunk should be called for the NACK.
        self.mock_extract_id.assert_called_once_with(chunk_message_text)

        # 3. A NACK should be sent.
        sender_id_str_for_reply = _format_node_id(sender_node_id_int)
        # ErrorTypeString for MismatchedTotalChunksError is "MismatchedTotalChunks"
        expected_nack_detail = f"MismatchedTotalChunks: {exception_message}"
        expected_nack_message = (
            f"BTC_NACK|{session_id_for_nack}|ERROR|{expected_nack_detail}"
        )

        self.mock_send_reply.assert_called_once_with(
            self.mock_iface,
            sender_id_str_for_reply,
            expected_nack_message,
            session_id_for_nack,
        )

        # 4. Assert the error log.
        expected_error_log = (
            f"[Sender: {sender_id_str_for_reply}, Session: {session_id_for_nack}] "
            f"Reassembly error: {exception_message}. Sending NACK."
        )
        self.mock_logger.error.assert_any_call(expected_error_log)

    def test_receive_btc_tx_chunk_other_reassembly_error_no_nack_by_default(self):
        """Test that a generic ReassemblyError from add_chunk does NOT send a NACK by default."""
        sender_node_id_int = 0xFEDCB  # Example sender
        server_node_id_str_formatted = "!abcdef"  # Our server's ID

        session_id_for_log = "sess_other_err"
        chunk_message_text = (
            f"{CHUNK_PREFIX}{session_id_for_log}|1/1|payload_for_other_error"
        )
        exception_message = "Test: Generic reassembly problem"

        # Configure mocks
        # Ensure the correct ReassemblyError is imported for this test to be meaningful
        # from core.reassembler import ReassemblyError # Already imported at top of file
        self.mock_reassembler.add_chunk.side_effect = ReassemblyError(exception_message)
        self.mock_extract_id.return_value = (
            session_id_for_log  # Used for logging context
        )

        packet = {
            "from": sender_node_id_int,
            "toId": server_node_id_str_formatted,
            "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": chunk_message_text},
            "id": "packet_btc_other_error",
            "channel": 0,
        }

        on_receive_text_message(packet, self.mock_iface)

        # 1. add_chunk should be called.
        self.mock_reassembler.add_chunk.assert_called_once_with(
            sender_node_id_int, chunk_message_text
        )

        # 2. _extract_session_id_from_raw_chunk should be called for logging context.
        self.mock_extract_id.assert_called_once_with(chunk_message_text)

        # 3. A NACK should NOT be sent for a generic ReassemblyError by default.
        self.mock_send_reply.assert_not_called()

        # 4. Assert the error log.
        sender_id_str_for_log = _format_node_id(sender_node_id_int)
        expected_error_log = (
            f"[Sender: {sender_id_str_for_log}, Session: {session_id_for_log}] "
            f"General reassembly error: {exception_message}. "
            f"Notifying sender may be needed."
        )
        self.mock_logger.error.assert_any_call(expected_error_log)

    def test_receive_btc_tx_chunk_unexpected_error_no_nack(self):
        """Test that an unexpected Exception from add_chunk does NOT send a NACK."""
        sender_node_id_int = 0x98765  # Example sender
        server_node_id_str_formatted = "!abcdef"  # Our server's ID

        session_id_for_log = "sess_unexpected_err"
        chunk_message_text = (
            f"{CHUNK_PREFIX}{session_id_for_log}|1/1|payload_for_unexpected_error"
        )
        exception_message = "Test: Totally unexpected problem during add_chunk"
        test_exception = Exception(exception_message)

        # Configure mocks
        self.mock_reassembler.add_chunk.side_effect = test_exception
        self.mock_extract_id.return_value = (
            session_id_for_log  # Used for logging context
        )

        packet = {
            "from": sender_node_id_int,
            "toId": server_node_id_str_formatted,
            "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": chunk_message_text},
            "id": "packet_btc_unexpected_error",
            "channel": 0,
        }

        on_receive_text_message(packet, self.mock_iface)

        # 1. add_chunk should be called.
        self.mock_reassembler.add_chunk.assert_called_once_with(
            sender_node_id_int, chunk_message_text
        )

        # 2. _extract_session_id_from_raw_chunk should be called for logging context.
        self.mock_extract_id.assert_called_once_with(chunk_message_text)

        # 3. A NACK should NOT be sent for an unexpected exception.
        self.mock_send_reply.assert_not_called()

        # 4. Assert the error log, ensuring exc_info=True.
        sender_id_str_for_log = _format_node_id(sender_node_id_int)
        expected_error_log_message = (
            f"[Sender: {sender_id_str_for_log}, Session: {session_id_for_log}] "
            f"Unexpected error processing chunk: {exception_message}. "  # Note: str(test_exception) is exception_message
            f"Not NACKing automatically."
        )

        # Check if any error log call matches the message and has exc_info=True
        found_log_with_exc_info = False
        for call_args_item in self.mock_logger.error.call_args_list:
            args, kwargs = call_args_item
            if (
                args
                and args[0] == expected_error_log_message
                and kwargs.get("exc_info") is True
            ):
                found_log_with_exc_info = True
                break
        self.assertTrue(
            found_log_with_exc_info,
            f"Expected error log '{expected_error_log_message}' with exc_info=True not found. "
            f"Actual calls: {self.mock_logger.error.call_args_list}",
        )

    def test_receive_btc_tx_chunk_not_for_server(self):
        """Test that a BTC_TX chunk not addressed to the server is ignored by reassembler."""
        sender_node_id_int = 0x112233
        # server_node_id_int = self.mock_iface.myInfo.my_node_num # 0xabcdef
        server_node_id_formatted = _format_node_id(
            self.mock_iface.myInfo.my_node_num
        )  # "!abcdef"

        other_node_id_str = "!feedbeef"  # Message addressed to this node

        session_id = "sess_not_for_us"
        message_text = f"{CHUNK_PREFIX}{session_id}|1/1|some_payload"

        packet = {
            "from": sender_node_id_int,
            "toId": other_node_id_str,  # Key: Addressed to another node
            "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": message_text},
            "id": "packet_btc_not_for_server",
            "channel": 0,  # Direct message
        }

        on_receive_text_message(packet, self.mock_iface)

        # Assertions:
        self.mock_reassembler.add_chunk.assert_not_called()
        self.mock_send_reply.assert_not_called()

        # Verify the specific log message for ignoring DM not addressed to us
        expected_log = f"Received message not for this node. To: {other_node_id_str}, MyID: {server_node_id_formatted}, From: {_format_node_id(sender_node_id_int)}"
        self.mock_logger.debug.assert_any_call(expected_log)

        # Ensure no BTC transaction processing logs occurred (e.g., "Potential BTC transaction chunk...")
        # This can be done by checking that certain calls were *not* made after the specific ignore log.
        # For simplicity, we rely on add_chunk_not_called primarily.

    def test_receive_standard_text_message_not_for_server(self):
        """Test that a standard text message not for the server is ignored."""
        sender_node_id_int = 0x445566
        server_node_id_formatted = _format_node_id(
            self.mock_iface.myInfo.my_node_num
        )  # "!abcdef"

        other_node_id_str = "!anotherNodeStd"  # Message addressed to this node
        message_text = "This is a standard message for someone else."

        packet = {
            "from": sender_node_id_int,
            "toId": other_node_id_str,  # Addressed to another node
            "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": message_text},
            "id": "packet_std_not_for_server",
            "channel": 0,  # Direct message
        }

        on_receive_text_message(packet, self.mock_iface)

        # Assertions:
        self.mock_reassembler.add_chunk.assert_not_called()
        self.mock_send_reply.assert_not_called()

        # Verify the specific log message for ignoring DM not addressed to us
        expected_log = f"Received message not for this node. To: {other_node_id_str}, MyID: {server_node_id_formatted}, From: {_format_node_id(sender_node_id_int)}"
        self.mock_logger.debug.assert_any_call(expected_log)

    def test_receive_non_text_message_for_server(self):
        """Test receiving a non-text (e.g., position) direct message for the server."""
        sender_node_id_int = 0x778899
        sender_node_id_formatted = _format_node_id(sender_node_id_int)
        server_node_id_formatted = _format_node_id(
            self.mock_iface.myInfo.my_node_num
        )  # "!abcdef"

        portnum_for_test = "POSITION_APP"  # Example non-text portnum
        packet_id = "packet_non_text"

        packet = {
            "from": sender_node_id_int,
            "toId": server_node_id_formatted,  # Addressed to our server
            "decoded": {
                "portnum": portnum_for_test,
                # No 'text' field for many non-text messages
            },
            "id": packet_id,
            "channel": 0,  # Direct message
        }

        on_receive_text_message(packet, self.mock_iface)

        # Assertions:
        self.mock_reassembler.add_chunk.assert_not_called()
        self.mock_send_reply.assert_not_called()

        # Verify the specific log message for non-text DMs
        expected_log = (
            f"Received direct message, but not TEXT_MESSAGE_APP. "
            f"Portnum: {portnum_for_test}, From: {sender_node_id_formatted}, "
            f"ID: {packet_id}"
        )
        self.mock_logger.debug.assert_any_call(expected_log)

    def test_receive_packet_no_decoded_field(self):
        """Test receiving a packet that is missing the 'decoded' field."""
        sender_node_id_int = 0x121212
        server_node_id_formatted = _format_node_id(self.mock_iface.myInfo.my_node_num)
        packet_id = "packet_no_decoded"

        # Packet is missing the 'decoded' key entirely
        packet = {
            "from": sender_node_id_int,
            "toId": server_node_id_formatted,  # Still a DM to us
            # 'decoded': { ... } -> MISSING
            "id": packet_id,
            "channel": 0,
        }

        on_receive_text_message(packet, self.mock_iface)

        # Assertions:
        self.mock_reassembler.add_chunk.assert_not_called()
        self.mock_send_reply.assert_not_called()

        # Verify the specific log message
        expected_log = f"Received packet without 'decoded' content: {packet_id}"
        self.mock_logger.debug.assert_any_call(expected_log)

    def test_receive_packet_no_text_field(self):
        """Test TEXT_MESSAGE_APP packet for server but missing 'text' field."""
        sender_node_id_int = 0xABABAB
        sender_node_id_formatted = _format_node_id(sender_node_id_int)
        server_node_id_formatted = _format_node_id(self.mock_iface.myInfo.my_node_num)
        packet_id = "packet_no_text_field"

        # Scenario 1: 'text' field is missing
        packet_missing_text = {
            "from": sender_node_id_int,
            "toId": server_node_id_formatted,
            "decoded": {
                "portnum": "TEXT_MESSAGE_APP",
                # 'text': ... -> MISSING
            },
            "id": packet_id + "_missing",
            "channel": 0,
        }

        on_receive_text_message(packet_missing_text, self.mock_iface)
        self.mock_reassembler.add_chunk.assert_not_called()
        self.mock_send_reply.assert_not_called()
        expected_log_missing = f"Direct text message with no text from {sender_node_id_formatted}: {packet_missing_text.get('id')}"
        self.mock_logger.debug.assert_any_call(expected_log_missing)
        self.mock_logger.reset_mock()  # Reset for next scenario
        self.mock_reassembler.reset_mock()
        self.mock_send_reply.reset_mock()

        # Scenario 2: 'text' field is None
        packet_text_is_none = {
            "from": sender_node_id_int,
            "toId": server_node_id_formatted,
            "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": None},
            "id": packet_id + "_none",
            "channel": 0,
        }
        on_receive_text_message(packet_text_is_none, self.mock_iface)
        self.mock_reassembler.add_chunk.assert_not_called()
        self.mock_send_reply.assert_not_called()
        expected_log_none = f"Direct text message with no text from {sender_node_id_formatted}: {packet_text_is_none.get('id')}"
        self.mock_logger.debug.assert_any_call(expected_log_none)
        self.mock_logger.reset_mock()
        self.mock_reassembler.reset_mock()
        self.mock_send_reply.reset_mock()

        # Scenario 3: 'text' field is empty string
        packet_text_is_empty = {
            "from": sender_node_id_int,
            "toId": server_node_id_formatted,
            "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": ""},
            "id": packet_id + "_empty",
            "channel": 0,
        }
        on_receive_text_message(packet_text_is_empty, self.mock_iface)
        self.mock_reassembler.add_chunk.assert_not_called()
        self.mock_send_reply.assert_not_called()
        expected_log_empty = f"Direct text message with no text from {sender_node_id_formatted}: {packet_text_is_empty.get('id')}"
        self.mock_logger.debug.assert_any_call(expected_log_empty)

    def test_receive_packet_from_self(self):
        """Test that packets sent from the server to itself are ignored."""
        server_node_id_int = self.mock_iface.myInfo.my_node_num  # 0xabcdef
        server_node_id_formatted = _format_node_id(server_node_id_int)  # "!abcdef"
        packet_id_base = "packet_from_self"

        # Scenario 1: BTC_TX chunk from self to self
        btc_tx_message_from_self = f"{CHUNK_PREFIX}self_sess|1/1|payload_from_self"
        packet_btc_from_self = {
            "from": server_node_id_int,
            "toId": server_node_id_formatted,
            "decoded": {
                "portnum": "TEXT_MESSAGE_APP",
                "text": btc_tx_message_from_self,
            },
            "id": packet_id_base + "_btc",
            "channel": 0,
        }

        on_receive_text_message(packet_btc_from_self, self.mock_iface)
        self.mock_reassembler.add_chunk.assert_not_called()
        self.mock_send_reply.assert_not_called()
        # This log assumes a new log message is added to SUT for ignoring self-messages
        expected_log_text_btc = (
            btc_tx_message_from_self[:30] + "..."
            if len(btc_tx_message_from_self) > 30
            else btc_tx_message_from_self
        )
        expected_log_self_btc = f"Ignoring DM from self. From: {server_node_id_formatted}, To: {server_node_id_formatted}, Text: '{expected_log_text_btc}'"
        self.mock_logger.debug.assert_any_call(expected_log_self_btc)

        self.mock_logger.reset_mock()
        self.mock_reassembler.reset_mock()
        self.mock_send_reply.reset_mock()

        # Scenario 2: Standard text message from self to self
        std_text_from_self = "Hello me!"
        packet_std_from_self = {
            "from": server_node_id_int,
            "toId": server_node_id_formatted,
            "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": std_text_from_self},
            "id": packet_id_base + "_std",
            "channel": 0,
        }
        on_receive_text_message(packet_std_from_self, self.mock_iface)
        self.mock_reassembler.add_chunk.assert_not_called()
        self.mock_send_reply.assert_not_called()
        expected_log_text_std = (
            std_text_from_self[:30] + "..."
            if len(std_text_from_self) > 30
            else std_text_from_self
        )
        expected_log_self_std = f"Ignoring DM from self. From: {server_node_id_formatted}, To: {server_node_id_formatted}, Text: '{expected_log_text_std}'"
        self.mock_logger.debug.assert_any_call(expected_log_self_std)

    def test_receive_broadcast_btc_tx_chunk_ignored(self):
        """Test that a BTC_TX chunk sent as a broadcast is ignored."""
        sender_node_id_int = 0xB20ADC57  # Example sender (valid hex)
        sender_node_id_formatted = _format_node_id(sender_node_id_int)
        server_node_id_formatted = _format_node_id(self.mock_iface.myInfo.my_node_num)

        broadcast_dest_id_str = "!ffffffff"  # Meshtastic broadcast address

        session_id = "sess_broadcast_btc"
        message_text = f"{CHUNK_PREFIX}{session_id}|1/1|broadcast_payload"

        # Simulate a broadcast packet by setting 'toId' to broadcast and channel to 0 (for pubsub text)
        # or by setting channel > 0 (though on_receive_text_message may not be called by pubsub then)
        # For this test, we rely on the toId check in on_receive_text_message
        packet = {
            "from": sender_node_id_int,
            "toId": broadcast_dest_id_str,  # Addressed to broadcast
            # 'channel': 1, # Alternatively, a non-zero channel indicates broadcast
            "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": message_text},
            "id": "packet_broadcast_btc",
            # channel: 0 is implied if not present for DMs, pubsub might filter based on channel already
        }

        on_receive_text_message(packet, self.mock_iface)

        self.mock_reassembler.add_chunk.assert_not_called()
        self.mock_send_reply.assert_not_called()

        # Expect a log that it was not for this node
        expected_log = f"Received message not for this node. To: {broadcast_dest_id_str}, MyID: {server_node_id_formatted}, From: {sender_node_id_formatted}"
        self.mock_logger.debug.assert_any_call(expected_log)

    def test_receive_broadcast_standard_text_ignored(self):
        """Test that a standard text message sent as a broadcast is ignored."""
        sender_node_id_int = (
            0xB20ADC57  # Example sender (same as other broadcast test for consistency)
        )
        sender_node_id_formatted = _format_node_id(sender_node_id_int)
        server_node_id_formatted = _format_node_id(self.mock_iface.myInfo.my_node_num)

        broadcast_dest_id_str = "!ffffffff"  # Meshtastic broadcast address
        message_text = "This is a standard broadcast message."

        packet = {
            "from": sender_node_id_int,
            "toId": broadcast_dest_id_str,  # Addressed to broadcast
            "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": message_text},
            "id": "packet_broadcast_std",
        }

        on_receive_text_message(packet, self.mock_iface)

        self.mock_reassembler.add_chunk.assert_not_called()
        self.mock_send_reply.assert_not_called()

        expected_log = f"Received message not for this node. To: {broadcast_dest_id_str}, MyID: {server_node_id_formatted}, From: {sender_node_id_formatted}"
        self.mock_logger.debug.assert_any_call(expected_log)


class TestMeshtasticReplySending(unittest.TestCase):
    def setUp(self):
        # Mock the logger
        self.patcher_logger = patch("btcmesh_server.server_logger")
        self.mock_logger = self.patcher_logger.start()

        # Mock the Meshtastic interface and node objects
        self.mock_iface = MagicMock()
        self.mock_node = MagicMock()
        self.mock_iface.getNode.return_value = self.mock_node

    def tearDown(self):
        self.patcher_logger.stop()
        # Ensure all mocks are reset if necessary, though patch.stop handles it

    @unittest.skip("Temporarily skipped")
    def test_send_reply_success_ack(self):
        """Test sending a successful ACK reply."""
        dest_id = "!dummyNodeId1"
        session_id = "sess123"
        txid = "sampletxid012345"
        message = f"BTC_ACK|{session_id}|SUCCESS|TXID:{txid}"

        result = send_meshtastic_reply(self.mock_iface, dest_id, message, session_id)

        self.assertTrue(result)
        self.mock_iface.getNode.assert_called_once_with(dest_id)
        self.mock_node.sendText.assert_called_once_with(text=message, wantAck=False)
        self.mock_logger.info.assert_any_call(
            f"[Session: {session_id}] Attempting to send reply to {dest_id}: "
            f"'{message}'"
        )
        self.mock_logger.info.assert_any_call(
            f"[Session: {session_id}] Successfully sent reply to {dest_id}: "
            f"'{message}'"
        )

    @unittest.skip("Temporarily skipped")
    def test_send_reply_success_nack_no_session_id(self):
        """Test sending a successful NACK reply without a session ID."""
        dest_id = "!dummyNodeId2"
        error_details = "Reassembly timeout"
        message = f"BTC_NACK||ERROR|{error_details}"  # Empty session_id

        result = send_meshtastic_reply(
            self.mock_iface, dest_id, message, tx_session_id=None
        )

        self.assertTrue(result)
        self.mock_iface.getNode.assert_called_once_with(dest_id)
        self.mock_node.sendText.assert_called_once_with(text=message, wantAck=False)
        self.mock_logger.info.assert_any_call(
            f"Attempting to send reply to {dest_id}: '{message}'"
        )
        self.mock_logger.info.assert_any_call(
            f"Successfully sent reply to {dest_id}: '{message}'"
        )

    def test_send_reply_invalid_destination_id_format(self):
        """Test sending reply with an invalid destination_id format."""
        dest_id = "dummyNodeId3"  # Missing '!'
        message = "BTC_NACK||ERROR|Invalid destination"
        session_id = "sess456"

        result = send_meshtastic_reply(self.mock_iface, dest_id, message, session_id)

        self.assertFalse(result)
        self.mock_iface.getNode.assert_not_called()
        self.mock_node.sendText.assert_not_called()
        self.mock_logger.error.assert_called_once_with(
            f"[Session: {session_id}] Cannot send reply: Invalid "
            f"destination_id format '{dest_id}'. Must start with '!'. "
            f"Message: '{message}'"
        )

    @unittest.skip("Temporarily skipped")
    def test_send_reply_destination_node_not_found(self):
        """Test sending reply when destination node is not found."""
        self.mock_iface.getNode.return_value = None
        dest_id = "!nonExistentNode"
        message = "BTC_NACK||ERROR|Node not found"
        session_id = "sess789"

        result = send_meshtastic_reply(self.mock_iface, dest_id, message, session_id)

        self.assertFalse(result)
        self.mock_iface.getNode.assert_called_once_with(dest_id)
        self.mock_node.sendText.assert_not_called()
        self.mock_logger.error.assert_called_once_with(
            f"[Session: {session_id}] Node {dest_id} not found in mesh. "
            f"Cannot send reply: '{message}'"
        )

    @unittest.skip("Temporarily skipped")
    def test_send_reply_sendtext_raises_exception(self):
        """Test sending reply when node.sendText() raises an exception."""
        self.mock_node.sendText.side_effect = Exception("Send failed")
        dest_id = "!errorNode"
        message = "BTC_ACK|sessErr|SUCCESS|TXID:errtxid"
        session_id = "sessErr"

        result = send_meshtastic_reply(self.mock_iface, dest_id, message, session_id)

        self.assertFalse(result)
        self.mock_iface.getNode.assert_called_once_with(dest_id)
        self.mock_node.sendText.assert_called_once_with(text=message, wantAck=False)
        self.mock_logger.error.assert_called_once_with(
            f"[Session: {session_id}] Failed to send reply to {dest_id}: "
            f"Send failed. Message: '{message}'",
            exc_info=True,
        )

    def test_send_reply_no_interface(self):
        """Test sending reply when Meshtastic interface is None."""
        dest_id = "!noIfaceNode"
        message = "BTC_NACK|noIface|ERROR|No interface"
        session_id = "noIface"

        result = send_meshtastic_reply(None, dest_id, message, session_id)

        self.assertFalse(result)
        # getNode should not be called on None
        self.mock_iface.getNode.assert_not_called()
        self.mock_logger.error.assert_called_once_with(
            f"[Session: {session_id}] Cannot send reply: "
            f"Meshtastic interface is not available."
        )

    @unittest.skip("Temporarily skipped")
    def test_send_reply_attribute_error_on_getnode(self):
        """Test AttributeError when calling getNode (iface is misconfigured)."""
        self.mock_iface.getNode.side_effect = AttributeError("Fake getnode error")
        dest_id = "!attrErrorNode"
        message = "Info message"
        session_id = "attrSess"

        result = send_meshtastic_reply(self.mock_iface, dest_id, message, session_id)

        self.assertFalse(result)
        self.mock_iface.getNode.assert_called_once_with(dest_id)
        self.mock_logger.error.assert_called_once_with(
            f"[Session: {session_id}] AttributeError while sending reply to "
            f"{dest_id}: Fake getnode error. Ensure interface and node "
            f"objects are valid. Message: '{message}'",
            exc_info=True,
        )


class TestTransactionReassemblerStory21(unittest.TestCase):
    def setUp(self):
        # Patch logger for log assertions
        self.logger_patcher = patch("core.reassembler.server_logger", MagicMock())
        self.mock_logger = self.logger_patcher.start()
        self.reassembler = TransactionReassembler(
            timeout_seconds=1
        )  # Short timeout for test
        self.sender_id = 12345
        self.session_id = "story21sess"

    def tearDown(self):
        self.logger_patcher.stop()

    def test_logs_on_new_session_and_chunk(self):
        chunk1 = f"BTC_TX|{self.session_id}|1/2|AAA"
        self.reassembler.add_chunk(self.sender_id, chunk1)
        # Should log new session start and chunk add
        log_ctx = f"[Sender: {self.sender_id}, Session: {self.session_id}]"
        self.mock_logger.info.assert_any_call(
            f"{log_ctx} New reassembly session started. Expecting 2 chunks."
        )
        self.mock_logger.debug.assert_any_call(
            f"{log_ctx} Added chunk 1/2. Collected 1 chunks."
        )

    def test_logs_on_duplicate_chunk(self):
        chunk1 = f"BTC_TX|{self.session_id}|1/2|AAA"
        self.reassembler.add_chunk(self.sender_id, chunk1)
        self.reassembler.add_chunk(self.sender_id, chunk1)  # Duplicate
        log_ctx = f"[Sender: {self.sender_id}, Session: {self.session_id}]"
        self.mock_logger.warning.assert_any_call(
            f"{log_ctx} Duplicate chunk 1/2 received. Ignoring."
        )

    def test_logs_on_out_of_order_and_reassembly_success(self):
        chunk2 = f"BTC_TX|{self.session_id}|2/2|BBB"
        chunk1 = f"BTC_TX|{self.session_id}|1/2|AAA"
        self.reassembler.add_chunk(self.sender_id, chunk2)
        self.reassembler.add_chunk(self.sender_id, chunk1)
        log_ctx = f"[Sender: {self.sender_id}, Session: {self.session_id}]"
        self.mock_logger.debug.assert_any_call(
            f"{log_ctx} Added chunk 2/2. Collected 1 chunks."
        )
        self.mock_logger.debug.assert_any_call(
            f"{log_ctx} Added chunk 1/2. Collected 2 chunks."
        )
        self.mock_logger.info.assert_any_call(
            f"{log_ctx} All 2 chunks received. Attempting reassembly."
        )
        self.mock_logger.info.assert_any_call(f"{log_ctx} Reassembly successful.")

    def test_logs_on_timeout(self):
        chunk1 = f"BTC_TX|{self.session_id}|1/2|AAA"
        self.reassembler.add_chunk(self.sender_id, chunk1)
        import time as _time

        _time.sleep(1.1)
        self.reassembler.cleanup_stale_sessions()
        log_ctx = f"[Sender: {self.sender_id}, Session: {self.session_id}]"
        self.mock_logger.warning.assert_any_call(
            f"{log_ctx} Reassembly timeout after 1s. Received 1/2 chunks. Discarding."
        )
        self.mock_logger.info.assert_any_call(
            "Identified 1 stale reassembly sessions for cleanup and NACK."
        )

    def test_logs_timeout_value_on_init(self):
        # The info log for timeout value should be called on init
        self.mock_logger.info.assert_any_call(
            "TransactionReassembler initialized with timeout: 1s"
        )


class TestHexValidationStory22(unittest.TestCase):
    def setUp(self):
        from core.reassembler import TransactionReassembler

        self.reassembler = TransactionReassembler(timeout_seconds=1)
        self.sender_id = 54321
        self.session_id = "hexval22"

    def test_valid_hex_string(self):
        """Given a valid hex string, When validated, Then it passes validation."""
        valid_hex = "deadbeefCAFEBABE0123456789abcdef"
        # Should not raise
        try:
            int(valid_hex, 16)
        except ValueError:
            self.fail("Valid hex string did not pass validation")

    def test_invalid_hex_string(self):
        """Given an invalid hex string, When validated, Then it fails validation and logs error."""
        invalid_hex = "deadbeefZZZ01234"
        with self.assertRaises(ValueError):
            int(invalid_hex, 16)

    def test_integration_reassembled_hex_validation(self):
        """Given a reassembled payload, When it is not valid hex, Then the server should log and prepare NACK."""
        # Simulate reassembly
        chunk1 = f"BTC_TX|{self.session_id}|1/2|deadbeef"
        chunk2 = f"BTC_TX|{self.session_id}|2/2|ZZZ01234"  # Invalid hex part
        self.reassembler.add_chunk(self.sender_id, chunk1)
        reassembled = self.reassembler.add_chunk(self.sender_id, chunk2)
        self.assertEqual(reassembled, "deadbeefZZZ01234")
        # Now validate
        with self.assertRaises(ValueError):
            int(reassembled, 16)

        # In the real server, this would trigger a NACK and log an error


class TestTransactionDecodeStory23(unittest.TestCase):
    def setUp(self):
        from core.transaction_parser import decode_raw_transaction_hex

        self.decode = decode_raw_transaction_hex

    def test_valid_raw_transaction_hex(self):
        """Given a valid raw transaction hex, When decoded, Then it returns a dict with fields."""
        # This is a minimal valid Bitcoin tx (version 1, 1 input, 1 output, locktime 0)
        # 01000000 (version 1)
        # 01 (input count)
        # 00..00 (32 bytes prev txid) + 00000000 (vout) + 00 (script len) + ffffffff (sequence)
        # 01 (output count)
        # 00e1f50500000000 (8 bytes value = 1 BTC)
        # 00 (script len)
        # 00000000 (locktime)
        raw_hex = (
            "01000000"
            + "01"
            + "00" * 32
            + "00000000"
            + "00"
            + "ffffffff"
            + "01"
            + "00e1f50500000000"
            + "00"
            + "00000000"
        )
        result = self.decode(raw_hex)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["version"], 1)
        self.assertEqual(result["input_count"], 1)
        self.assertEqual(result["locktime"], 0)
        # output_count is None (placeholder)

    def test_malformed_raw_transaction_hex(self):
        """Given a malformed raw transaction hex, When decoded, Then it raises ValueError and logs error."""
        bad_hex = "deadbeef"  # Too short to be a valid tx
        with self.assertRaises(ValueError):
            self.decode(bad_hex)


class TestTransactionSanityChecksStory31(unittest.TestCase):
    def setUp(self):
        # Minimal stub for validation logic, to be replaced by actual import
        self.valid_tx = {
            "version": 1,
            "input_count": 1,
            "output_count": 1,
            "locktime": 0,
        }
        self.no_inputs_tx = {
            "version": 1,
            "input_count": 0,
            "output_count": 1,
            "locktime": 0,
        }
        self.no_outputs_tx = {
            "version": 1,
            "input_count": 1,
            "output_count": 0,
            "locktime": 0,
        }
        # The actual validation function will be implemented in core.transaction_parser

    def test_no_inputs_fails_validation(self):
        """Given a decoded transaction with zero inputs, When validated, Then it fails and NACK is prepared."""
        from core.transaction_parser import basic_sanity_check

        valid, error = basic_sanity_check(self.no_inputs_tx)
        self.assertFalse(valid)
        self.assertIn("No inputs", error)

    def test_no_outputs_fails_validation(self):
        """Given a decoded transaction with zero outputs, When validated, Then it fails and NACK is prepared."""
        from core.transaction_parser import basic_sanity_check

        valid, error = basic_sanity_check(self.no_outputs_tx)
        self.assertFalse(valid)
        self.assertIn("No outputs", error)

    def test_valid_tx_passes_validation(self):
        """Given a decoded transaction with at least one input and one output, When validated, Then it passes."""
        from core.transaction_parser import basic_sanity_check

        valid, error = basic_sanity_check(self.valid_tx)
        self.assertTrue(valid)
        self.assertIsNone(error)


class TestBitcoinRpcConfigStory41(unittest.TestCase):
    def setUp(self):
        self.env_keys = [
            "BITCOIN_RPC_HOST",
            "BITCOIN_RPC_PORT",
            "BITCOIN_RPC_USER",
            "BITCOIN_RPC_PASSWORD",
        ]
        self.default_env = {
            "BITCOIN_RPC_HOST": "127.0.0.1",
            "BITCOIN_RPC_PORT": "8332",
            "BITCOIN_RPC_USER": "testuser",
            "BITCOIN_RPC_PASSWORD": "testpass",
        }

    def test_all_fields_present_in_env(self):
        """Given all required RPC fields in .env, When loaded, Then config is correct."""
        from core.config_loader import load_bitcoin_rpc_config

        with unittest.mock.patch.dict("os.environ", self.default_env, clear=True):
            config = load_bitcoin_rpc_config()
            self.assertEqual(config["host"], "127.0.0.1")
            self.assertEqual(config["port"], 8332)
            self.assertEqual(config["user"], "testuser")
            self.assertEqual(config["password"], "testpass")

    def test_missing_required_field_raises(self):
        """Given missing required RPC fields, When loaded, Then error is raised or logged."""
        from core.config_loader import load_bitcoin_rpc_config

        env = self.default_env.copy()
        del env["BITCOIN_RPC_USER"]
        with unittest.mock.patch.dict("os.environ", env, clear=True):
            with self.assertRaises(ValueError):
                load_bitcoin_rpc_config()

    def test_partial_fields_use_defaults(self):
        """Given only host and port in .env, When loaded, Then user/password missing triggers error."""
        from core.config_loader import load_bitcoin_rpc_config

        env = {
            "BITCOIN_RPC_HOST": "10.0.0.2",
            "BITCOIN_RPC_PORT": "18443",
        }
        with unittest.mock.patch.dict("os.environ", env, clear=True):
            with self.assertRaises(ValueError):
                load_bitcoin_rpc_config()


class TestBitcoinRpcConnectionStory42(unittest.TestCase):
    def setUp(self):
        self.valid_config = {
            "host": "127.0.0.1",
            "port": 8332,
            "user": "testuser",
            "password": "testpass",
        }

    def test_valid_config_node_reachable(self):
        """Given valid config and node reachable, When connecting, Then connection is established."""
        with unittest.mock.patch("core.rpc_client.requests.post") as mock_post:
            from core.rpc_client import BitcoinRPCClient

            # Configure the mock to return a successful response
            mock_response = MagicMock()
            mock_response.json.return_value = {"result": {"chain": "main"}, "error": None}
            mock_post.return_value = mock_response

            # Call the method
            rpc = BitcoinRPCClient(self.valid_config)

            # Assertions
            self.assertIsNotNone(rpc)
            mock_post.assert_called_once_with(
                rpc.uri,
                data='{"jsonrpc": "1.0", "id": "btcmesh", "method": "getblockchaininfo", "params": []}',
                headers={'Content-Type': 'application/json'},
                proxies={},
                timeout=30
            )
            

    def test_non_int_port_invalid_config_raises(self):
        """Given invalid config, When connecting, Then error is raised."""
        from core.rpc_client import BitcoinRPCClient

        bad_config = self.valid_config.copy()
        bad_config["port"] = "notanint"

        # Assertions
        with self.assertRaises(Exception):
            # Call the method
            BitcoinRPCClient(bad_config)

    def test_no_port_invalid_config_raises(self):
        """Given invalid config, When connecting, Then error is raised."""
        from core.rpc_client import BitcoinRPCClient

        bad_config = self.valid_config.copy()
        bad_config["port"] = None

        # Assertions
        with self.assertRaises(Exception):
            # Call the method
            BitcoinRPCClient(bad_config)

    def test_no_host_invalid_config_raises(self):
        """Given invalid config, When connecting, Then error is raised."""
        from core.rpc_client import BitcoinRPCClient

        bad_config = self.valid_config.copy()
        bad_config["host"] = None

        # Assertions
        with self.assertRaises(Exception):
            # Call the method
            BitcoinRPCClient(bad_config)

    def test_rpc_request_retries_on_connection_error_three_times_last_success(self):
        """Given valid config but node unreachable, When connecting, retries twice, succeeds on third try."""
        with unittest.mock.patch("core.rpc_client.requests.post") as mock_post:
            from core.rpc_client import BitcoinRPCClient

            # Mock the response to raise ConnectionError for the first two calls and success on last
            mock_post.side_effect = [
                ConnectionError("Connection error"), 
                ConnectionError("Connection error"),
                MagicMock(json=MagicMock(return_value={"result": {"chain": "main"}, "error": None}))
            ]

            # Call the method
            rpc = BitcoinRPCClient(self.valid_config)

            # Assertions
            self.assertIsNotNone(rpc)
            self.assertEqual(mock_post.call_count, 3)  # Ensure post was called three times

    def test_rpc_request_retries_on_connection_error_second_success(self):
        """Given valid config but node unreachable on first try, retries and suceeds on second try."""
        with unittest.mock.patch("core.rpc_client.requests.post") as mock_post:
            from core.rpc_client import BitcoinRPCClient

            # Mock the response to raise ConnectionError for the first call and success on the second
            mock_post.side_effect = [
                ConnectionError("Connection error"), 
                MagicMock(json=MagicMock(return_value={"result": {"chain": "main"}, "error": None}))
            ]

            # Call the method
            rpc = BitcoinRPCClient(self.valid_config)

            # Assertions
            self.assertIsNotNone(rpc)
            self.assertEqual(mock_post.call_count, 2)  # Ensure post was called two times

    def test_rpc_request_retries_on_connection_error_three_times_failure(self):
        """Given valid config but node unreachable, When connecting, retries 3 times, fails."""
        with unittest.mock.patch("core.rpc_client.requests.post") as mock_post:
            from core.rpc_client import BitcoinRPCClient

            # Mock the response to raise ConnectionError
            mock_post.side_effect = ConnectionError("Connection error")

            # Assert that the ConnectionError is raised after 3 attempts
            with self.assertRaises(ConnectionError) as context:
                # Call the method
                rpc = BitcoinRPCClient(self.valid_config)

            # Assertions
            self.assertTrue("Connection error" in str(context.exception))
            self.assertEqual(mock_post.call_count, 3)  # Ensure post was called three times


class TestBitcoinRpcBroadcastStory43(unittest.TestCase):
    def setUp(self):
        self.config = {
            'user': 'testuser',
            'password': 'testpass',
            'host': 'localhost',
            'port': 8332
        }
        self.valid_tx_hex = "0100000001abcdef..."
        self.txid = "deadbeefcafebabe1234567890abcdef1234567890abcdef"

    def test_successful_broadcast_returns_txid(self):
        """Given valid hex and RPC connection, When broadcast, Then TXID is returned."""
        from core.rpc_client import BitcoinRPCClient

        # Mock connect to prevent actual connection, and requests.post for the broadcast call
        with unittest.mock.patch.object(BitcoinRPCClient, 'connect'), \
            unittest.mock.patch('requests.post') as mock_post:
            # Create client (connect is mocked so no actual connection)
            client = BitcoinRPCClient(self.config)

            # Simulate a successful response from the RPC server
            mock_post.return_value.json.return_value = {
                "result": self.txid,
                "error": None
            }

            # Call the method
            txid, error = client.broadcast_transaction(self.valid_tx_hex)

            # Assertions
            self.assertEqual(txid, self.txid, "TXID returned should match expected TXID.")
            self.assertIsNone(error, "There should be no error for valid transaction.")

    def test_rpc_error_returns_error_message(self):
        """Given valid hex but RPC error, When broadcast, Then error message is returned."""
        from core.rpc_client import BitcoinRPCClient

        with unittest.mock.patch.object(BitcoinRPCClient, 'connect'), \
            unittest.mock.patch('requests.post') as mock_post:
            client = BitcoinRPCClient(self.config)

            # Simulate an error response from the RPC server
            mock_post.return_value.json.return_value = {
                "result": None,
                "error": {"code": -26, "message": "txn-mempool-conflict"}
            }

            # Call the method
            txid, error = client.broadcast_transaction(self.valid_tx_hex)

            # Assertions
            self.assertIsNone(txid)
            self.assertIn("txn-mempool-conflict", error)

    def test_no_rpc_connection_returns_error(self):
        """Given connection failure during broadcast, Then txid=None and error message is returned."""
        from core.rpc_client import BitcoinRPCClient
        import requests

        with unittest.mock.patch.object(BitcoinRPCClient, 'connect'), \
            unittest.mock.patch('requests.post') as mock_post:
            client = BitcoinRPCClient(self.config)

            # Simulate connection failure when trying to broadcast
            mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

            txid, error = client.broadcast_transaction(self.valid_tx_hex)

            self.assertIsNone(txid)
            self.assertIsNotNone(error)
            self.assertIn("Connection refused", error)


class TestReassemblyTimeoutConfigStory52(unittest.TestCase):
    def setUp(self):
        self.default_timeout = 30
        self.env_key = "REASSEMBLY_TIMEOUT_SECONDS"
        self.env = {
            "BITCOIN_RPC_HOST": "127.0.0.1",
            "BITCOIN_RPC_PORT": "8332",
            "BITCOIN_RPC_USER": "user",
            "BITCOIN_RPC_PASSWORD": "pass",
        }

    def test_timeout_loaded_from_env(self):
        from core.config_loader import load_reassembly_timeout

        env = self.env.copy()
        env[self.env_key] = "42"
        with unittest.mock.patch.dict("os.environ", env, clear=True):
            timeout, source = load_reassembly_timeout()
            self.assertEqual(timeout, 42)
            self.assertEqual(source, "env")

    def test_timeout_missing_uses_default(self):
        from core.config_loader import load_reassembly_timeout

        with unittest.mock.patch.dict("os.environ", self.env, clear=True):
            timeout, source = load_reassembly_timeout()
            self.assertEqual(timeout, self.default_timeout)
            self.assertEqual(source, "default")

    def test_timeout_invalid_uses_default_and_logs_warning(self):
        from core.config_loader import load_reassembly_timeout

        env = self.env.copy()
        env[self.env_key] = "notanint"
        with unittest.mock.patch.dict("os.environ", env, clear=True):
            with unittest.mock.patch("core.config_loader.server_logger") as mock_logger:
                timeout, source = load_reassembly_timeout()
                self.assertEqual(timeout, self.default_timeout)
                self.assertEqual(source, "default")
                mock_logger.warning.assert_any_call(
                    "Invalid REASSEMBLY_TIMEOUT_SECONDS value 'notanint'. Using default: 30s."
                )

    def test_timeout_zero_or_negative_uses_default_and_logs_warning(self):
        from core.config_loader import load_reassembly_timeout

        for bad_val in ["0", "-5"]:
            env = self.env.copy()
            env[self.env_key] = bad_val
            with unittest.mock.patch.dict("os.environ", env, clear=True):
                with unittest.mock.patch(
                    "core.config_loader.server_logger"
                ) as mock_logger:
                    timeout, source = load_reassembly_timeout()
                    self.assertEqual(timeout, self.default_timeout)
                    self.assertEqual(source, "default")
                    mock_logger.warning.assert_any_call(
                        f"Invalid REASSEMBLY_TIMEOUT_SECONDS value '{bad_val}'. Using default: 30s."
                    )


class TestReliableSessionChunkTransfer(unittest.TestCase):
    def setUp(self):
        # Patch the logger
        self.logger_patcher = patch("btcmesh_server.server_logger", MagicMock())
        self.mock_logger = self.logger_patcher.start()

    def tearDown(self):
        self.logger_patcher.stop()

    def test_session_initialization_ack(self):
        """
        Given a client wants to send a transaction,
        When it sends BTC_SESSION_START|<session_id>|<total_chunks>|<chunk_size> to the server,
        Then the server should respond with BTC_SESSION_ACK|<session_id>|READY|REQUEST_CHUNK|1.
        """
        session_id = "sess123"
        total_chunks = 5
        chunk_size = 170
        client_node_id = "!abcdef01"
        server_node_id = "!deadbeef"
        packet = {
            "decoded": {
                "portnum": "TEXT_MESSAGE_APP",
                "text": f"BTC_SESSION_START|{session_id}|{total_chunks}|{chunk_size}",
            },
            "from": client_node_id,
            "to": server_node_id,
        }
        mock_iface = MagicMock()
        mock_iface.myInfo = MagicMock()
        mock_iface.myInfo.my_node_num = server_node_id
        mock_send_reply = MagicMock()
        on_receive_text_message(
            packet, interface=mock_iface, send_reply_func=mock_send_reply
        )
        expected_ack = f"BTC_SESSION_ACK|{session_id}|READY|REQUEST_CHUNK|1"
        mock_send_reply.assert_called_with(
            mock_iface, client_node_id, expected_ack, session_id
        )

    def test_chunk_1_ack_and_request_next(self):
        """
        Given a session is initialized and the server has requested chunk 1,
        When the client sends BTC_CHUNK|<session_id>|1/<total_chunks>|<hex_payload>,
        Then the server responds with BTC_CHUNK_ACK|<session_id>|1|OK|REQUEST_CHUNK|2 and is ready for the next chunk.
        """
        session_id = "sess456"
        total_chunks = 3
        chunk_size = 170
        client_node_id = "!abcdef02"
        server_node_id = "!deadbeef"
        chunk_payload = "deadbeefcafebabe"
        # Simulate session already initialized (server has requested chunk 1)
        # For now, we assume the server is stateless for this test, or we can mock the reassembler/session state as needed.
        # Send the chunk message
        packet = {
            "decoded": {
                "portnum": "TEXT_MESSAGE_APP",
                "text": f"BTC_CHUNK|{session_id}|1/{total_chunks}|{chunk_payload}",
            },
            "from": client_node_id,
            "to": server_node_id,
        }
        mock_iface = MagicMock()
        mock_iface.myInfo = MagicMock()
        mock_iface.myInfo.my_node_num = server_node_id
        mock_send_reply = MagicMock()
        # Call the handler
        from btcmesh_server import on_receive_text_message

        on_receive_text_message(
            packet, interface=mock_iface, send_reply_func=mock_send_reply
        )
        expected_ack = f"BTC_CHUNK_ACK|{session_id}|1|OK|REQUEST_CHUNK|2"
        mock_send_reply.assert_called_with(
            mock_iface, client_node_id, expected_ack, session_id
        )

    def test_chunk_timeout_and_retries(self):
        """
        Given a chunk is sent and not ACKed within 30 seconds,
        When the client retries up to 3 times,
        Then the server only processes the first valid chunk and ignores duplicates.
        """
        session_id = "sess789"
        total_chunks = 2
        chunk_payload = "cafebabe1234"
        client_node_id = "!abcdef03"
        server_node_id = "!deadbeef"
        # Simulate the server's session state (mock or patch as needed)
        # For now, we assume the server is stateless and just checks for duplicates
        packet = {
            "decoded": {
                "portnum": "TEXT_MESSAGE_APP",
                "text": f"BTC_CHUNK|{session_id}|1/{total_chunks}|{chunk_payload}",
            },
            "from": client_node_id,
            "to": server_node_id,
        }
        mock_iface = MagicMock()
        mock_iface.myInfo = MagicMock()
        mock_iface.myInfo.my_node_num = server_node_id
        mock_send_reply = MagicMock()
        # First send: should ACK
        from btcmesh_server import on_receive_text_message

        on_receive_text_message(
            packet, interface=mock_iface, send_reply_func=mock_send_reply
        )
        expected_ack = f"BTC_CHUNK_ACK|{session_id}|1|OK|REQUEST_CHUNK|2"
        mock_send_reply.assert_called_with(
            mock_iface, client_node_id, expected_ack, session_id
        )
        mock_send_reply.reset_mock()
        # Retry 1: should be ignored (no duplicate ACK)
        on_receive_text_message(
            packet, interface=mock_iface, send_reply_func=mock_send_reply
        )
        mock_send_reply.assert_not_called()
        # Retry 2: should be ignored
        on_receive_text_message(
            packet, interface=mock_iface, send_reply_func=mock_send_reply
        )
        mock_send_reply.assert_not_called()

    def test_session_abort(self):
        """
        Given a session is active,
        When either side sends BTC_SESSION_ABORT|<session_id>|<reason>,
        Then the other side stops processing and logs the abort.
        """
        session_id = "sess999"
        client_node_id = "!abcdef04"
        server_node_id = "!deadbeef"
        abort_reason = "User requested abort"
        packet = {
            "decoded": {
                "portnum": "TEXT_MESSAGE_APP",
                "text": f"BTC_SESSION_ABORT|{session_id}|{abort_reason}",
            },
            "from": client_node_id,
            "to": server_node_id,
        }
        mock_iface = MagicMock()
        mock_iface.myInfo = MagicMock()
        mock_iface.myInfo.my_node_num = server_node_id
        mock_send_reply = MagicMock()
        with patch("btcmesh_server.server_logger") as mock_logger:
            on_receive_text_message(
                packet,
                interface=mock_iface,
                send_reply_func=mock_send_reply,
                logger=mock_logger,
            )
            # Should log the abort reason
            mock_logger.info.assert_any_call(
                f"Session {session_id} aborted by {client_node_id}: {abort_reason}"
            )
            # Should not send any reply
            mock_send_reply.assert_not_called()


class TestMultipleConcurrentSessions(unittest.TestCase):
    def setUp(self):
        # Patch the logger
        self.patcher_logger = patch("btcmesh_server.server_logger", MagicMock())
        self.mock_logger = self.patcher_logger.start()

        # Patch the transaction reassembler instance that is used in btcmesh_server
        self.patcher_reassembler = patch(
            "btcmesh_server.transaction_reassembler", autospec=True
        )
        self.mock_reassembler = self.patcher_reassembler.start()
        self.mock_reassembler.CHUNK_PREFIX = CHUNK_PREFIX

        # Patch send_meshtastic_reply
        self.patcher_send_reply = patch(
            "btcmesh_server.send_meshtastic_reply", autospec=True
        )
        self.mock_send_reply = self.patcher_send_reply.start()

        # Patch _extract_session_id_from_raw_chunk
        self.patcher_extract_id = patch(
            "btcmesh_server._extract_session_id_from_raw_chunk", autospec=True
        )
        self.mock_extract_id = self.patcher_extract_id.start()

        # Create a mock Meshtastic interface instance
        self.mock_iface = MagicMock()
        self.mock_iface.myInfo = MagicMock()
        self.mock_iface.myInfo.my_node_num = 0xABCDEF  # Server's node number

    def tearDown(self):
        self.patcher_logger.stop()
        self.patcher_reassembler.stop()
        self.patcher_send_reply.stop()
        self.patcher_extract_id.stop()

    def test_multiple_sessions_are_independent(self):
        """Test that the server tracks and reassembles multiple sessions independently."""
        # Simulate two clients with different session IDs
        client1_id = 0x111111
        client2_id = 0x222222
        session1 = "sessA"
        session2 = "sessB"
        chunk1a = f"{CHUNK_PREFIX}{session1}|1/2|AAA"
        chunk1b = f"{CHUNK_PREFIX}{session1}|2/2|BBB"
        chunk2a = f"{CHUNK_PREFIX}{session2}|1/2|XXX"
        chunk2b = f"{CHUNK_PREFIX}{session2}|2/2|YYY"
        # Set up the reassembler to return None for first chunk, and a hex string for the second
        self.mock_reassembler.add_chunk.side_effect = [
            None,  # client1, chunk1
            None,  # client2, chunk1
            "AAABBB",  # client1, chunk2 (reassembled)
            "XXYYYY",  # client2, chunk2 (reassembled)
        ]
        # Patch _extract_session_id_from_raw_chunk to return the correct session
        self.mock_extract_id.side_effect = [session1, session2]
        # Interleave chunks: client1 chunk1, client2 chunk1, client1 chunk2, client2 chunk2
        packets = [
            {
                "from": client1_id,
                "toId": "!abcdef",
                "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": chunk1a},
                "id": "p1a",
                "channel": 0,
            },
            {
                "from": client2_id,
                "toId": "!abcdef",
                "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": chunk2a},
                "id": "p2a",
                "channel": 0,
            },
            {
                "from": client1_id,
                "toId": "!abcdef",
                "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": chunk1b},
                "id": "p1b",
                "channel": 0,
            },
            {
                "from": client2_id,
                "toId": "!abcdef",
                "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": chunk2b},
                "id": "p2b",
                "channel": 0,
            },
        ]
        from btcmesh_server import on_receive_text_message

        for packet in packets:
            on_receive_text_message(
                packet, self.mock_iface, send_reply_func=self.mock_send_reply
            )
        # Assert add_chunk was called with correct sender/session for each chunk
        expected_calls = [
            call(client1_id, chunk1a),
            call(client2_id, chunk2a),
            call(client1_id, chunk1b),
            call(client2_id, chunk2b),
        ]
        self.mock_reassembler.add_chunk.assert_has_calls(expected_calls)
        # Assert that both sessions were reassembled independently (i.e., both reassembled_hex returned)
        # The reply function should be called for each reassembly (simulate NACK for no RPC, as in other tests)
        self.assertGreaterEqual(self.mock_send_reply.call_count, 2)
        # Optionally, check that the correct session IDs were used in replies
        reply_session_ids = [args[3] for args, _ in self.mock_send_reply.call_args_list]
        self.assertIn(session1, reply_session_ids)
        self.assertIn(session2, reply_session_ids)


class TestAckNackAndErrorHandling(unittest.TestCase):
    def setUp(self):
        self.patcher_logger = patch("btcmesh_server.server_logger", MagicMock())
        self.mock_logger = self.patcher_logger.start()
        self.patcher_reassembler = patch(
            "btcmesh_server.transaction_reassembler", autospec=True
        )
        self.mock_reassembler = self.patcher_reassembler.start()
        self.mock_reassembler.CHUNK_PREFIX = CHUNK_PREFIX
        self.patcher_send_reply = patch(
            "btcmesh_server.send_meshtastic_reply", autospec=True
        )
        self.mock_send_reply = self.patcher_send_reply.start()
        self.patcher_extract_id = patch(
            "btcmesh_server._extract_session_id_from_raw_chunk", autospec=True
        )
        self.mock_extract_id = self.patcher_extract_id.start()
        self.mock_iface = MagicMock()
        self.mock_iface.myInfo = MagicMock()
        self.mock_iface.myInfo.my_node_num = 0xABCDEF

    def tearDown(self):
        self.patcher_logger.stop()
        self.patcher_reassembler.stop()
        self.patcher_send_reply.stop()
        self.patcher_extract_id.stop()

    def test_ack_on_valid_chunk(self):
        sender_node_id = 0x12345
        session_id = "sess_ack"
        chunk_msg = f"BTC_TX|{session_id}|1/2|deadbeef"
        self.mock_reassembler.add_chunk.return_value = None
        packet = {
            "from": sender_node_id,
            "toId": "!abcdef",
            "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": chunk_msg},
            "id": "packet_ack",
            "channel": 0,
        }
        from btcmesh_server import on_receive_text_message

        on_receive_text_message(
            packet, self.mock_iface, send_reply_func=self.mock_send_reply
        )
        # Should ACK chunk 1 and request next
        expected_ack = f"BTC_CHUNK_ACK|{session_id}|1|OK|REQUEST_CHUNK|2"
        self.mock_send_reply.assert_called_with(
            self.mock_iface, "!12345", expected_ack, session_id
        )

    def test_nack_on_invalid_chunk(self):
        sender_node_id = 0x23456
        session_id = "sess_nack"
        chunk_msg = f"BTC_TX|{session_id}|bad/format|badhex"
        self.mock_reassembler.add_chunk.side_effect = InvalidChunkFormatError(
            "bad format"
        )
        self.mock_extract_id.return_value = session_id
        packet = {
            "from": sender_node_id,
            "toId": "!abcdef",
            "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": chunk_msg},
            "id": "packet_nack",
            "channel": 0,
        }
        from btcmesh_server import on_receive_text_message

        on_receive_text_message(
            packet, self.mock_iface, send_reply_func=self.mock_send_reply
        )
        expected_nack = f"BTC_NACK|{session_id}|ERROR|Invalid ChunkFormat: bad format"
        self.mock_send_reply.assert_called_with(
            self.mock_iface, "!23456", expected_nack, session_id
        )

    def test_duplicate_chunk_handling(self):
        sender_node_id = 0x34567
        session_id = "sess_dup"
        chunk_msg = f"BTC_TX|{session_id}|1/2|deadbeef"
        # Simulate duplicate: first call returns None, second raises duplicate warning
        self.mock_reassembler.add_chunk.side_effect = [
            None,
            InvalidChunkFormatError("Duplicate chunk"),
        ]
        packet = {
            "from": sender_node_id,
            "toId": "!abcdef",
            "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": chunk_msg},
            "id": "packet_dup",
            "channel": 0,
        }
        from btcmesh_server import on_receive_text_message

        # First call: valid
        on_receive_text_message(
            packet, self.mock_iface, send_reply_func=self.mock_send_reply
        )
        # Second call: duplicate
        on_receive_text_message(
            packet, self.mock_iface, send_reply_func=self.mock_send_reply
        )
        # Should NACK on duplicate
        expected_nack = (
            f"BTC_NACK|{session_id}|ERROR|Invalid ChunkFormat: Duplicate chunk"
        )
        self.mock_send_reply.assert_called_with(
            self.mock_iface, "!34567", expected_nack, session_id
        )


if __name__ == "__main__":
    unittest.main()
