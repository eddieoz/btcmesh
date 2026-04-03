import unittest
import subprocess
import sys
import os
from unittest.mock import patch, MagicMock, call, ANY, Mock
from btcmesh_cli import cli_main

SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "btcmesh_cli.py")


class TestBtcmeshCliStory61(unittest.TestCase):
    def run_cli(self, args):
        """Helper to run the CLI script with args and return (exitcode, stdout, stderr)."""
        cmd = [sys.executable, SCRIPT_PATH] + args
        proc = subprocess.run(cmd, capture_output=True, text=True)
        return proc.returncode, proc.stdout, proc.stderr

    def test_valid_args(self):
        # Use dummy but valid-looking hex and dest
        dest = "!abcdef12"
        tx_hex = "deadbeefcafebabe"
        Args = type("Args", (), {"destination": dest, "tx": tx_hex, "dry_run": True})
        with patch("builtins.print") as mock_print:
            code = cli_main(args=Args)
        self.assertEqual(code, 0)
        printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list)
        self.assertIn(dest, printed)
        self.assertIn(tx_hex, printed)
        self.assertIn("Arguments parsed successfully", printed)

    def test_missing_destination(self):
        tx_hex = "deadbeefcafebabe"

        def fake_parse_args():
            print("usage: btcmesh_cli.py [-d DEST] -tx TX [--dry-run]")
            raise SystemExit(2)

        with patch(
            "argparse.ArgumentParser.parse_args", side_effect=fake_parse_args
        ), patch("builtins.print") as mock_print:
            with self.assertRaises(SystemExit):
                cli_main(args=None)
        printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list)
        self.assertIn("usage", printed.lower())

    def test_missing_tx(self):
        def fake_parse_args():
            print("usage: btcmesh_cli.py [-d DEST] -tx TX [--dry-run]")
            raise SystemExit(2)

        with patch(
            "argparse.ArgumentParser.parse_args", side_effect=fake_parse_args
        ), patch("builtins.print") as mock_print:
            with self.assertRaises(SystemExit):
                cli_main(args=None)
        printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list)
        self.assertIn("usage", printed.lower())

    def test_invalid_hex(self):
        dest = "!abcdef12"
        bad_hex = "deadbeefZZZ"
        Args = type("Args", (), {"destination": dest, "tx": bad_hex, "dry_run": True})
        with patch("builtins.print") as mock_print, self.assertRaises(ValueError):
            cli_main(args=Args)
        printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list)
        self.assertIn("Invalid raw transaction hex", printed)

    def test_odd_length_hex(self):
        dest = "!abcdef12"
        bad_hex = "abcde"
        Args = type("Args", (), {"destination": dest, "tx": bad_hex, "dry_run": True})
        with patch("builtins.print") as mock_print, self.assertRaises(ValueError):
            cli_main(args=Args)
        printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list)
        self.assertIn("Invalid raw transaction hex", printed)


class TestBtcmeshCliStory63(unittest.TestCase):
    CHUNK_SIZE = 170  # hex chars (85 bytes)

    def test_single_chunk(self):
        dest = "!abcdef12"
        tx_hex = "a" * 100  # 50 bytes, fits in one chunk
        Args = type("Args", (), {"destination": dest, "tx": tx_hex, "dry_run": True})
        with patch("builtins.print") as mock_print:
            code = cli_main(args=Args)
        self.assertEqual(code, 0)
        printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list)
        self.assertIn("BTC_TX|", printed)
        self.assertIn("|1/1|", printed)
        self.assertIn(tx_hex, printed)

    def test_multi_chunk(self):
        dest = "!abcdef12"
        tx_hex = "b" * 450  # 225 bytes, should be 3 chunks (170, 170, 110)
        Args = type("Args", (), {"destination": dest, "tx": tx_hex, "dry_run": True})
        with patch("builtins.print") as mock_print:
            code = cli_main(args=Args)
        self.assertEqual(code, 0)
        printed_lines = [
            str(call.args[0])
            for call in mock_print.call_args_list
            if str(call.args[0]).startswith("BTC_TX|")
        ]
        self.assertEqual(len(printed_lines), 3)
        for i, line in enumerate(printed_lines, 1):
            self.assertIn(f"|{i}/3|", line)
        self.assertTrue(
            all(len(line.split("|")[-1]) <= self.CHUNK_SIZE for line in printed_lines)
        )
        self.assertIn(tx_hex[:170], printed_lines[0])
        self.assertIn(tx_hex[170:340], printed_lines[1])
        self.assertIn(tx_hex[340:], printed_lines[2])

    def test_chunk_size_boundary(self):
        dest = "!abcdef12"
        tx_hex = "c" * self.CHUNK_SIZE  # Exactly one chunk
        Args = type("Args", (), {"destination": dest, "tx": tx_hex, "dry_run": True})
        with patch("builtins.print") as mock_print:
            code = cli_main(args=Args)
        self.assertEqual(code, 0)
        printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list)
        self.assertIn("|1/1|", printed)
        self.assertIn(tx_hex, printed)

    def test_chunk_size_limit_enforced(self):
        dest = "!abcdef12"
        tx_hex = "e" * 510  # 3 chunks: 170, 170, 170
        Args = type("Args", (), {"destination": dest, "tx": tx_hex, "dry_run": True})
        with patch("builtins.print") as mock_print:
            code = cli_main(args=Args)
        self.assertEqual(code, 0)
        printed_lines = [
            str(call.args[0])
            for call in mock_print.call_args_list
            if str(call.args[0]).startswith("BTC_TX|")
        ]
        self.assertEqual(len(printed_lines), 3)
        for line in printed_lines:
            self.assertLessEqual(len(line.split("|")[-1]), self.CHUNK_SIZE)

    @unittest.skip("Temporarily skipped")
    def test_session_id_looks_unique(self):
        dest = "!abcdef12"
        tx_hex = "d" * 100
        Args1 = type("Args", (), {"destination": dest, "tx": tx_hex, "dry_run": True})
        Args2 = type("Args", (), {"destination": dest, "tx": tx_hex, "dry_run": True})
        with patch("builtins.print") as mock_print1:
            cli_main(args=Args1)
        with patch("builtins.print") as mock_print2:
            cli_main(args=Args2)
        import re

        printed1 = "\n".join(str(call.args[0]) for call in mock_print1.call_args_list)
        printed2 = "\n".join(str(call.args[0]) for call in mock_print2.call_args_list)
        sid1 = re.search(r"BTC_TX\|([^|]+)\|", printed1)
        sid2 = re.search(r"BTC_TX\|([^|]+)\|", printed2)
        self.assertIsNotNone(sid1)
        self.assertIsNotNone(sid2)
        self.assertNotEqual(sid1.group(1), sid2.group(1))
        self.assertTrue(len(sid1.group(1)) >= 8)

    def test_chunks_printed_in_order(self):
        dest = "!abcdef12"
        tx_hex = "".join(f"{i%10}" for i in range(510))  # 3 chunks
        Args = type("Args", (), {"destination": dest, "tx": tx_hex, "dry_run": True})
        with patch("builtins.print") as mock_print:
            code = cli_main(args=Args)
        self.assertEqual(code, 0)
        printed_lines = [
            str(call.args[0])
            for call in mock_print.call_args_list
            if str(call.args[0]).startswith("BTC_TX|")
        ]
        payloads = [line.split("|", 3)[-1] for line in printed_lines]
        self.assertEqual("".join(payloads), tx_hex)


class TestMeshtasticCliInitializationStory62(unittest.TestCase):
    """
    TDD for Story 6.2: Meshtastic interface initialization in btcmesh-cli.py
    Covers:
      - Successful connection (auto-detect and config port)
      - Device not found
      - Import error (meshtastic not installed)
      - Logging of all attempts and errors
    """

    def setUp(self):
        # Patch meshtastic and its components in sys.modules
        self.mock_meshtastic_module = MagicMock()
        self.mock_serial_interface_module = MagicMock()
        self.MockMeshtasticSerialInterfaceClass = MagicMock()
        self.mock_serial_interface_module.SerialInterface = (
            self.MockMeshtasticSerialInterfaceClass
        )
        self.mock_meshtastic_module.serial_interface = self.mock_serial_interface_module
        self.MockNoDeviceError = type("NoDeviceError", (Exception,), {})
        self.MockMeshtasticError = type("MeshtasticError", (Exception,), {})
        self.mock_meshtastic_module.NoDeviceError = self.MockNoDeviceError
        self.mock_meshtastic_module.MeshtasticError = self.MockMeshtasticError
        self.sys_modules_patcher = patch.dict(
            sys.modules,
            {
                "meshtastic": self.mock_meshtastic_module,
                "meshtastic.serial_interface": self.mock_serial_interface_module,
            },
        )
        self.sys_modules_patcher.start()
        # Patch config loader for port
        self.config_loader_patcher = patch(
            "core.config_loader.get_meshtastic_serial_port"
        )
        self.mock_get_serial_port = self.config_loader_patcher.start()
        # Patch logger setup for CLI
        self.logger_patcher = patch(
            "core.logger_setup.setup_logger", return_value=MagicMock()
        )
        self.mock_setup_logger = self.logger_patcher.start()

    def tearDown(self):
        self.sys_modules_patcher.stop()
        self.config_loader_patcher.stop()
        self.logger_patcher.stop()

    def test_successful_autodetect(self):
        self.mock_get_serial_port.return_value = None
        mock_iface = self.MockMeshtasticSerialInterfaceClass.return_value
        mock_iface.devicePath = "/dev/ttyUSB0"
        # Simulate CLI init function (to be implemented)
        # Should log attempt and success
        # ...
        # self.mock_setup_logger().info.assert_any_call('Attempting to initialize Meshtastic interface (auto-detect)...')
        # self.mock_setup_logger().info.assert_any_call('Meshtastic interface initialized successfully. Device: /dev/ttyUSB0')

    def test_successful_with_config_port(self):
        self.mock_get_serial_port.return_value = "/dev/ttyS0"
        mock_iface = self.MockMeshtasticSerialInterfaceClass.return_value
        mock_iface.devicePath = "/dev/ttyS0"
        # Simulate CLI init function (to be implemented)
        # Should log attempt and success
        # ...

    def test_no_device_error(self):
        self.mock_get_serial_port.return_value = None
        self.MockMeshtasticSerialInterfaceClass.side_effect = self.MockNoDeviceError(
            "No device"
        )
        # Simulate CLI init function (to be implemented)
        # Should log error and exit
        # ...

    def test_import_error(self):
        # Remove meshtastic from sys.modules and patch import to raise ImportError
        with patch.dict(
            "sys.modules", {"meshtastic": None, "meshtastic.serial_interface": None}
        ):
            with patch("builtins.__import__", side_effect=ImportError):
                # Simulate CLI init function (to be implemented)
                # Should log error and exit
                # ...
                pass

    def test_logging_on_all_attempts(self):
        # Should log every connection attempt and error
        # ...
        pass


class TestMeshtasticCliChunkedSendingStory63(unittest.TestCase):
    """
    TDD for Story 6.3: Chunked transaction sending via Meshtastic in CLI.
    Covers multi-chunk, single-chunk, send errors, and logging.
    """

    def setUp(self):
        self.mock_iface = MagicMock()
        self.mock_logger = MagicMock()

    def make_args(self, dest, tx_hex, dry_run=False):
        return type(
            "Args", (), {"destination": dest, "tx": tx_hex, "dry_run": dry_run}
        )()

    def assert_printed_substring(self, mock_print, substring):
        found = any(
            substring in str(call.args[0]) for call in mock_print.call_args_list
        )
        assert found, f"Did not find print call containing: {substring}"

    @unittest.skip("Temporarily skipped")
    def test_multi_chunk_transaction_sends_all(self):
        dest = "!abcdef12"
        tx_hex = "a" * 450  # 3 chunks
        self.mock_iface.sendText.return_value = None
        args = self.make_args(dest, tx_hex)
        session_id = "testsession_multi"
        args.session_id = session_id

        def message_receiver(timeout, session_id):
            yield f"BTC_CHUNK_ACK|{session_id}|1|OK|REQUEST_CHUNK|2"
            yield f"BTC_CHUNK_ACK|{session_id}|2|OK|REQUEST_CHUNK|3"
            yield f"BTC_CHUNK_ACK|{session_id}|3|OK|ALL_CHUNKS_RECEIVED"
            yield f"BTC_ACK|{session_id}|SUCCESS|TXID:testtxid_multi"

        with patch("builtins.print") as mock_print:
            ret = cli_main(
                args=args,
                injected_iface=self.mock_iface,
                injected_logger=self.mock_logger,
                injected_message_receiver=message_receiver,
            )
        self.assertEqual(ret, 0)
        self.assertEqual(self.mock_iface.sendText.call_count, 3)
        self.assert_printed_substring(mock_print, "Sent chunk 1/3 for session")
        self.assert_printed_substring(mock_print, "Sent chunk 2/3 for session")
        self.assert_printed_substring(mock_print, "Sent chunk 3/3 for session")
        self.assert_printed_substring(
            mock_print, "All transaction chunks sent for session"
        )
        self.assert_printed_substring(
            mock_print,
            "Transaction successfully broadcast by relay. TXID: testtxid_multi",
        )

    @unittest.skip("Temporarily skipped")
    def test_single_chunk_transaction_sends_one(self):
        dest = "!abcdef12"
        tx_hex = "b" * 100  # 1 chunk
        self.mock_iface.sendText.return_value = None
        args = self.make_args(dest, tx_hex)
        session_id = "testsession_single"
        args.session_id = session_id

        def message_receiver(timeout, session_id):
            yield f"BTC_CHUNK_ACK|{session_id}|1|OK|ALL_CHUNKS_RECEIVED"
            yield f"BTC_ACK|{session_id}|SUCCESS|TXID:testtxid_single"

        with patch("builtins.print") as mock_print:
            ret = cli_main(
                args=args,
                injected_iface=self.mock_iface,
                injected_logger=self.mock_logger,
                injected_message_receiver=message_receiver,
            )
        self.assertEqual(ret, 0)
        self.assertEqual(self.mock_iface.sendText.call_count, 1)
        self.assert_printed_substring(mock_print, "Sent chunk 1/1 for session")
        self.assert_printed_substring(
            mock_print, "All transaction chunks sent for session"
        )
        self.assert_printed_substring(
            mock_print,
            "Transaction successfully broadcast by relay. TXID: testtxid_single",
        )

    @unittest.skip("Temporarily skipped")
    def test_error_sending_chunk_logs_and_prints(self):
        dest = "!abcdef12"
        tx_hex = "c" * 300  # 2 chunks

        def sendText_side_effect(*args, **kwargs):
            # Raise on first chunk
            raise Exception("Send failed")

        self.mock_iface.sendText.side_effect = sendText_side_effect
        args = self.make_args(dest, tx_hex)

        def dummy_message_receiver(timeout, session_id):
            if False:
                yield  # never yields

        with patch("builtins.print") as mock_print, self.assertRaises(Exception):
            cli_main(
                args=args,
                injected_iface=self.mock_iface,
                injected_logger=self.mock_logger,
                injected_message_receiver=dummy_message_receiver,
            )
        self.assert_printed_substring(mock_print, "Error sending chunk 1/2 for session")
        found_log = any(
            "Error sending chunk 1/2 for session" in str(call.args[0])
            for call in self.mock_logger.error.call_args_list
        )
        assert (
            found_log
        ), "Did not find logger.error call containing: Error sending chunk 1/2 for session"

    @unittest.skip("Temporarily skipped")
    def test_logging_on_all_chunking_and_sending(self):
        dest = "!abcdef12"
        tx_hex = "d" * 340  # 2 chunks
        self.mock_iface.sendText.return_value = None
        args = self.make_args(dest, tx_hex)
        session_id = "testsession_logging"
        args.session_id = session_id

        def message_receiver(timeout, session_id):
            yield f"BTC_CHUNK_ACK|{session_id}|1|OK|REQUEST_CHUNK|2"
            yield f"BTC_CHUNK_ACK|{session_id}|2|OK|ALL_CHUNKS_RECEIVED"

        with patch("builtins.print") as mock_print:
            cli_main(
                args=args,
                injected_iface=self.mock_iface,
                injected_logger=self.mock_logger,
                injected_message_receiver=message_receiver,
            )
        # Assert logger.info called for each chunk sent and for session completion
        info_calls = [
            str(call.args[0]) for call in self.mock_logger.info.call_args_list
        ]
        self.assertTrue(
            any(
                f"Sent chunk 1/2 for session {session_id}" in msg for msg in info_calls
            ),
            "Missing log for chunk 1",
        )
        self.assertTrue(
            any(
                f"Sent chunk 2/2 for session {session_id}" in msg for msg in info_calls
            ),
            "Missing log for chunk 2",
        )
        self.assertTrue(
            any(
                f"All transaction chunks sent for session {session_id}" in msg
                for msg in info_calls
            ),
            "Missing log for session completion",
        )


class TestMeshtasticCliAckNackListeningStory64(unittest.TestCase):
    """
    TDD for Story 6.4: Listen for ACK/NACK in btcmesh-cli.py.
    Covers success, error, timeout, unrelated messages, and logging.
    """

    def setUp(self):
        from btcmesh_cli import cli_main, generate_session_id

        self.cli_main = cli_main
        self.dest = "!abcdef12"
        self.tx_hex = "a" * 100  # 1 chunk
        self.session_id = generate_session_id()
        self.mock_iface = MagicMock()
        self.mock_logger = MagicMock()

    def make_args(self, dest, tx_hex):
        Args = type(
            "Args",
            (),
            {
                "destination": dest,
                "tx": tx_hex,
                "dry_run": False,
                "session_id": self.session_id,
            },
        )
        return Args

    @unittest.skip("Temporarily skipped")
    def test_receives_btc_ack_for_session(self):
        # Simulate receiving BTC_ACK for the session AFTER chunks are done
        txid = "abc123txid"

        # Message for completing chunk phase (1 chunk)
        chunk_ack_final_msg = (
            f"BTC_CHUNK_ACK|{self.session_id}|1|OK|ALL_CHUNKS_RECEIVED"
        )
        # Message for final session ACK
        session_ack_msg = f"BTC_ACK|{self.session_id}|SUCCESS|TXID:{txid}"

        def mock_message_receiver(timeout, session_id):
            yield chunk_ack_final_msg  # Complete chunking phase
            yield session_ack_msg  # Actual message being tested

        args = self.make_args(self.dest, self.tx_hex)
        # args.session_id is set in make_args

        with patch("builtins.print") as mock_print:
            ret = self.cli_main(
                args=args,
                injected_iface=self.mock_iface,
                injected_logger=self.mock_logger,
                injected_message_receiver=mock_message_receiver,
            )

        # Should print success with TXID and return 0
        printed_output = "\n".join(
            str(call.args[0]) for call in mock_print.call_args_list
        )
        expected_success_print = (
            f"Transaction successfully broadcast by relay. TXID: {txid}"
        )

        self.assertEqual(ret, 0, "CLI should return 0 on successful session ACK.")
        self.assertIn(
            expected_success_print,
            printed_output,
            "Did not print success message with TXID",
        )
        self.mock_logger.info.assert_any_call(
            f"Received ACK for session {self.session_id}: {session_ack_msg}"
        )

    @unittest.skip("Temporarily skipped")
    def test_receives_btc_nack_for_session(self):
        # Simulate receiving BTC_NACK for the session AFTER chunks are done
        nack_reason = "Test session NACK reason"

        # Message for completing chunk phase (1 chunk)
        chunk_ack_final_msg = (
            f"BTC_CHUNK_ACK|{self.session_id}|1|OK|ALL_CHUNKS_RECEIVED"
        )
        # Message for final session NACK
        session_nack_msg = f"BTC_NACK|{self.session_id}|ERROR|{nack_reason}"

        def mock_message_receiver(timeout, session_id):
            yield chunk_ack_final_msg  # Complete chunking phase
            yield session_nack_msg  # Actual message being tested

        args = self.make_args(self.dest, self.tx_hex)  # tx_hex is 1 chunk from setUp

        with patch("builtins.print") as mock_print:
            ret = self.cli_main(
                args=args,
                injected_iface=self.mock_iface,
                injected_logger=self.mock_logger,
                injected_message_receiver=mock_message_receiver,
            )

        printed_output = "\n".join(
            str(call.args[0]) for call in mock_print.call_args_list
        )
        expected_error_print = f"Relay reported an error: {nack_reason}"

        self.assertEqual(ret, 1, "CLI should return 1 on session NACK.")
        self.assertIn(
            expected_error_print,
            printed_output,
            f"Did not print session NACK error message. Output: {printed_output}",
        )
        self.mock_logger.info.assert_any_call(
            f"Received NACK for session {self.session_id}: {session_nack_msg}"
        )

    def test_timeout_waiting_for_ack_nack(self):
        # Simulate no ACK/NACK received within timeout
        # Should print timeout message and exit 2
        pass

    def test_ignores_unrelated_messages(self):
        # Simulate receiving unrelated messages (wrong session or not ACK/NACK)
        # Should not exit or print success/error for those
        pass

    def test_logging_on_ack_nack_and_timeout(self):
        # Should log all received ACK/NACK and timeouts
        pass


class TestCliStopAndWaitARQ(unittest.TestCase):
    def setUp(self):
        from btcmesh_cli import cli_main, generate_session_id
        from unittest.mock import Mock, MagicMock

        self.cli_main = cli_main
        self.dest = "!abcdef12"
        self.tx_hex = "a" * 340  # Ensure 2 chunks for this test case
        self.session_id = generate_session_id()  # Use dynamic session_id
        self.mock_iface = Mock()
        self.sent_chunks = []
        self.mock_iface.sendText = self.mock_sendText  # Assign method directly
        self.mock_logger = MagicMock()  # Use MagicMock for the logger

    def mock_sendText(self, text, destinationId):
        self.sent_chunks.append((text, destinationId))

    def mock_message_receiver(self, timeout, session_id):
        # For chunk 1
        yield f"BTC_CHUNK_ACK|{session_id}|1|OK|REQUEST_CHUNK|2"
        # For chunk 2
        yield f"BTC_CHUNK_ACK|{session_id}|2|OK|ALL_CHUNKS_RECEIVED"
        # Final session ACK
        yield f"BTC_ACK|{session_id}|SUCCESS|TXID:stopwait_txid"

    def test_cli_stop_and_wait_sends_chunks_in_order(self):
        Args = type(
            "Args",
            (),
            {
                "destination": self.dest,
                "tx": self.tx_hex,
                "session_id": self.session_id,
                "dry_run": False,
            },
        )
        with patch("builtins.print") as mock_print:
            result = self.cli_main(
                args=Args,
                injected_iface=self.mock_iface,
                injected_logger=self.mock_logger,  # Pass the mock_logger
                injected_message_receiver=self.mock_message_receiver,
            )
        # Should send exactly 2 chunks, in order, waiting for each ACK
        self.assertEqual(len(self.sent_chunks), 2)
        self.assertTrue(
            self.sent_chunks[0][0].startswith(f"BTC_TX|{self.session_id}|1/2|")
        )
        self.assertTrue(
            self.sent_chunks[1][0].startswith(f"BTC_TX|{self.session_id}|2/2|")
        )
        self.assertEqual(result, 0)
        printed_output = "\n".join(
            str(call.args[0]) for call in mock_print.call_args_list
        )
        self.assertIn(
            "Transaction successfully broadcast by relay. TXID: stopwait_txid",
            printed_output,
        )


class TestCliNackAndAbortHandling(unittest.TestCase):
    def setUp(self):
        from btcmesh_cli import cli_main
        from unittest.mock import Mock, MagicMock

        self.cli_main = cli_main
        self.dest = "!abcdef12"
        self.tx_hex = "a" * 340  # 2 chunks of 170
        self.session_id = "testsession456"
        self.sent_chunks = []
        self.mock_iface = Mock()
        self.mock_iface.sendText = self.mock_sendText
        self.mock_logger = MagicMock()

        # Messages used by tests in this class
        self.nack_msg_chunk1 = (
            f"BTC_NACK|{self.session_id}|1|ERROR|NACK for chunk 1 test"
        )
        self.ack_msg_chunk1 = f"BTC_CHUNK_ACK|{self.session_id}|1|OK|REQUEST_CHUNK|2"
        self.ack_msg_chunk2_final = (
            f"BTC_CHUNK_ACK|{self.session_id}|2|OK|ALL_CHUNKS_RECEIVED"
        )
        self.final_session_ack = (
            f"BTC_ACK|{self.session_id}|SUCCESS|TXID:final_nack_handling_test"
        )

    def mock_sendText(self, text, destinationId):
        self.sent_chunks.append((text, destinationId))

    @unittest.skip("Temporarily skipped")
    def test_nack_retries_and_aborts(self):
        # Simulate NACK for chunk 1, 3 times, then CLI should abort
        # The message_receiver here should only provide NACKs for chunk 1.
        # The CLI should retry chunk 1 three times (initial + 2 retries = 3 sends)
        # After the third NACK is processed, it should abort.
        def message_receiver(timeout, session_id):
            yield self.nack_msg_chunk1  # For 1st send of chunk 1
            yield self.nack_msg_chunk1  # For 2nd send of chunk 1 (1st retry)
            yield self.nack_msg_chunk1  # For 3rd send of chunk 1 (2nd retry)
            # No more messages, CLI should abort after processing 3rd NACK

        Args = type(
            "Args",
            (),
            {
                "destination": self.dest,
                "tx": self.tx_hex,
                "session_id": self.session_id,
                "dry_run": False,
            },
        )

        with patch("builtins.print") as mock_print, self.assertRaises(SystemExit) as cm:
            self.cli_main(
                args=Args,
                injected_iface=self.mock_iface,
                injected_logger=self.mock_logger,
                injected_message_receiver=message_receiver,
            )

        self.assertEqual(cm.exception.code, 2, "CLI should exit with code 2 on abort.")
        self.assertEqual(
            len(self.sent_chunks),
            3,
            "Should send chunk 1 three times (initial + 2 retries)",
        )

        printed_output = "\n".join(
            str(call.args[0]) for call in mock_print.call_args_list
        )
        expected_abort_print = f"Aborting session after 3 NACKs for chunk 1/2"
        self.assertIn(
            expected_abort_print,
            printed_output,
            f"Did not print correct abort message. Output: {printed_output}",
        )

        self.mock_logger.error.assert_any_call(
            f"Aborting session {self.session_id} after 3 NACKs for chunk 1/2"
        )
        # Check retry messages
        self.assertIn(
            f"Retrying chunk 1/2 (attempt 2 of 3) due to NACK", printed_output
        )
        self.assertIn(
            f"Retrying chunk 1/2 (attempt 3 of 3) due to NACK", printed_output
        )

class TestCliTimeoutAndRetriesOnNoAck(unittest.TestCase):
    def setUp(self):
        from btcmesh_cli import cli_main, generate_session_id
        from unittest.mock import Mock

        self.cli_main = cli_main
        self.dest = "!abcdef12"
        self.tx_hex = "a" * 340  # 2 chunks of 170, ensuring it's multi-chunk
        self.session_id = generate_session_id()
        self.mock_iface = Mock()
        self.sent_chunks = []
        self.mock_iface.sendText = self.mock_sendText
        self.mock_logger = Mock()

    def mock_sendText(self, text, destinationId):
        self.sent_chunks.append((text, destinationId))

    @unittest.skip("Temporarily skipped")
    def test_timeout_and_retries_on_no_ack(self):
        # Simulate no ACK/NACK for chunk 1 (generator yields nothing)
        def message_receiver(timeout, session_id):
            if False:
                yield  # never yields

        Args = type(
            "Args",
            (),
            {
                "destination": self.dest,
                "tx": self.tx_hex,
                "session_id": self.session_id,
                "dry_run": False,
            },
        )
        with patch("builtins.print") as mock_print, self.assertRaises(SystemExit) as cm:
            self.cli_main(
                args=Args,
                injected_iface=self.mock_iface,
                injected_message_receiver=message_receiver,
            )
        self.assertEqual(len(self.sent_chunks), 3)  # 3 retries
        printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list)
        # BDD: Should print retry message for each attempt
        self.assertIn("Retrying chunk 1/2 (attempt 2 of 3) due to timeout", printed)
        self.assertIn("Retrying chunk 1/2 (attempt 3 of 3) due to timeout", printed)
        # BDD: Should print abort message after 3 failures
        self.assertIn(
            "Aborting session after 3 failed attempts to send chunk 1/2", printed
        )

    @unittest.skip("Temporarily skipped")
    def test_prints_ack_and_nack_messages(self):
        # Simulate NACK for chunk 1, then ACK on retry, then completion
        nack_msg_chunk1 = f"BTC_NACK|{self.session_id}|1|ERROR|Test NACK for chunk 1"
        ack_msg_chunk1_retry = f"BTC_CHUNK_ACK|{self.session_id}|1|OK|REQUEST_CHUNK|2"
        ack_msg_chunk2_final = (
            f"BTC_CHUNK_ACK|{self.session_id}|2|OK|ALL_CHUNKS_RECEIVED"
        )
        final_session_ack = f"BTC_ACK|{self.session_id}|SUCCESS|TXID:acknack_txid"

        def message_receiver(timeout, session_id):
            yield nack_msg_chunk1  # NACK for 1st attempt of chunk 1
            yield ack_msg_chunk1_retry  # ACK for 2nd attempt of chunk 1 (after CLI retry)
            yield ack_msg_chunk2_final  # ACK for 1st attempt of chunk 2
            yield final_session_ack  # Final session ACK

        Args = type(
            "Args",
            (),
            {
                "destination": self.dest,
                "tx": self.tx_hex,  # tx_hex is 2 chunks from setUp
                "session_id": self.session_id,
                "dry_run": False,
            },
        )

        with patch("builtins.print") as mock_print:
            ret = 0
            try:
                ret = self.cli_main(
                    args=Args,
                    injected_iface=self.mock_iface,
                    injected_logger=self.mock_logger,
                    injected_message_receiver=message_receiver,
                )
            except SystemExit as e:
                ret = e.code  # Capture exit code if SystemExit is raised

        printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list)

        self.assertEqual(
            ret,
            0,
            f"CLI should return 0 after successful retries and completion. Output: {printed}",
        )
        self.assertIn(f"Received NACK for chunk 1/2: Test NACK for chunk 1", printed)
        self.assertIn(f"Retrying chunk 1/2 (attempt 2 of 3) due to NACK", printed)
        self.assertIn(f"Received ACK for chunk 1/2", printed)  # For the ACK after retry
        self.assertIn(
            f"All transaction chunks sent for session {self.session_id}.", printed
        )  # For final chunk completion
        self.assertIn(
            f"Transaction successfully broadcast by relay. TXID: acknack_txid", printed
        )  # For final session ACK print

        # Assert logger calls for NACK and retry
        self.mock_logger.warning.assert_any_call(
            f"Received NACK for chunk 1/2 in session {self.session_id}: Test NACK for chunk 1"
        )
        self.mock_logger.warning.assert_any_call(
            f"Retrying chunk 1/2 (attempt 2 of 3) due to NACK"
        )

class TestDryRunWithoutMeshtasticStory65(unittest.TestCase):
    """
    TDD for Story 6.5: Dry Run Without Meshtastic Connection.
    Verifies that dry run mode works without a Meshtastic device connected.
    """

    def test_dry_run_skips_meshtastic_initialization(self):
        """Verify dry run returns before Meshtastic init is called."""
        dest = "!abcdef12"
        tx_hex = "deadbeefcafebabe"
        Args = type("Args", (), {"destination": dest, "tx": tx_hex, "dry_run": True})

        # Patch initialize_meshtastic_interface_cli to track if it's called
        # (and silence prints to keep output clean)
        with patch(
            "btcmesh_cli.initialize_meshtastic_interface_cli"
        ) as mock_init_meshtastic, patch("builtins.print"):
            code = cli_main(args=Args)

        self.assertEqual(code, 0)
        # Meshtastic initialization should NOT be called when dry_run is True
        mock_init_meshtastic.assert_not_called()

    def test_dry_run_prints_simulated_chunks(self):
        """Verify dry run prints simulated chunk messages."""
        dest = "!abcdef12"
        tx_hex = "a" * 450  # 3 chunks
        Args = type("Args", (), {"destination": dest, "tx": tx_hex, "dry_run": True})

        with patch("builtins.print") as mock_print:
            code = cli_main(args=Args)

        self.assertEqual(code, 0)
        printed_lines = [
            str(call.args[0])
            for call in mock_print.call_args_list
            if str(call.args[0]).startswith("BTC_TX|")
        ]
        # Should print 3 chunks
        self.assertEqual(len(printed_lines), 3)
        for i, line in enumerate(printed_lines, 1):
            self.assertIn(f"|{i}/3|", line)

    def test_dry_run_works_without_meshtastic_installed(self):
        """
        Verify dry run works even if meshtastic module is unavailable.
        This simulates the scenario where no Meshtastic device is connected
        and the import would fail.
        """
        dest = "!abcdef12"
        tx_hex = "deadbeefcafebabe"
        Args = type("Args", (), {"destination": dest, "tx": tx_hex, "dry_run": True})

        # Patch to simulate meshtastic not being available
        with patch.dict(
            sys.modules, {"meshtastic": None, "meshtastic.serial_interface": None}
        ), patch("builtins.print") as mock_print:
            code = cli_main(args=Args)

        self.assertEqual(code, 0)
        printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list)
        self.assertIn("Arguments parsed successfully", printed)
        self.assertIn("BTC_TX|", printed)

    def test_dry_run_exits_successfully(self):
        """Verify dry run exits with code 0."""
        dest = "!abcdef12"
        tx_hex = "cafebabe"
        Args = type("Args", (), {"destination": dest, "tx": tx_hex, "dry_run": True})

        with patch("builtins.print"):
            code = cli_main(args=Args)

        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
