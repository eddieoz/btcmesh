"""Tests for base64 chunk encoding (protocol v1.1, BTC_TX64).

Hex spends 2 characters per transaction byte; base64 spends 1.33. Since a
Meshtastic text message is a fixed-size box, base64 carries ~48% more
transaction per packet, and under stop-and-wait ARQ every packet removed is a
full round trip removed.

These tests cover both directions (client chunking, server reassembly) and
assert that v1.0 hex behaviour is untouched.
"""

import base64
import unittest
from unittest.mock import patch

from btcmesh_cli import (
    CHUNK_SIZE,
    CHUNK_SIZE_B64,
    chunk_transaction,
    cli_main,
    encode_payload,
)
from core.reassembler import (
    CHUNK_PREFIX,
    CHUNK_PREFIX_B64,
    ENCODING_B64,
    ENCODING_HEX,
    InvalidChunkFormatError,
    MismatchedEncodingError,
    TransactionReassembler,
    match_chunk_prefix,
)

# Meshtastic Constants.DATA_PAYLOAD_LEN
MESHTASTIC_PAYLOAD_LIMIT = 233
# Longest message v1.0 already ships in production: "BTC_TX|xxxxx|1/3|" + 170
V1_ENVELOPE = 187


def tx_of_size(n_bytes, fill="ab"):
    """Synthetic raw transaction hex of exactly n_bytes."""
    return (fill * n_bytes)[: n_bytes * 2]


def build_messages(tx_hex, session_id="a1b2c", encoding=ENCODING_B64):
    """Client side: encode, chunk, and frame as wire messages."""
    prefix = CHUNK_PREFIX_B64 if encoding == ENCODING_B64 else CHUNK_PREFIX
    size = CHUNK_SIZE_B64 if encoding == ENCODING_B64 else CHUNK_SIZE
    chunks = chunk_transaction(encode_payload(tx_hex, encoding), size)
    total = len(chunks)
    return [
        f"{prefix}{session_id}|{i}/{total}|{payload}"
        for i, payload in enumerate(chunks, 1)
    ]


class TestPrefixMatching(unittest.TestCase):
    def test_hex_prefix(self):
        self.assertEqual(
            match_chunk_prefix("BTC_TX|a1b2c|1/2|deadbeef"),
            ("a1b2c|1/2|deadbeef", ENCODING_HEX),
        )

    def test_base64_prefix(self):
        self.assertEqual(
            match_chunk_prefix("BTC_TX64|a1b2c|1/2|3q2+7w=="),
            ("a1b2c|1/2|3q2+7w==", ENCODING_B64),
        )

    def test_base64_prefix_is_not_confused_for_hex(self):
        # "BTC_TX64|..." must NOT satisfy startswith("BTC_TX|"), otherwise a
        # v1.0 relay would misparse base64 as hex instead of ignoring it.
        self.assertFalse("BTC_TX64|a1b2c|1/1|3q2+7w==".startswith(CHUNK_PREFIX))

    def test_non_chunk_returns_none(self):
        self.assertIsNone(match_chunk_prefix("hello there"))
        self.assertIsNone(match_chunk_prefix("BTC_ACK|a1b2c|SUCCESS|TXID:ab"))


class TestEncodePayload(unittest.TestCase):
    def test_hex_is_passthrough(self):
        tx_hex = tx_of_size(64)
        self.assertEqual(encode_payload(tx_hex, ENCODING_HEX), tx_hex)

    def test_base64_roundtrip(self):
        tx_hex = tx_of_size(191)
        encoded = encode_payload(tx_hex, ENCODING_B64)
        self.assertEqual(base64.b64decode(encoded).hex(), tx_hex)

    def test_base64_is_denser_than_hex(self):
        tx_hex = tx_of_size(300)
        self.assertLess(len(encode_payload(tx_hex, ENCODING_B64)), len(tx_hex))

    def test_chunk_size_is_whole_base64_quanta(self):
        # Each chunk must be a multiple of 4 chars so it decodes independently.
        self.assertEqual(CHUNK_SIZE_B64 % 4, 0)


class TestBase64Reassembly(unittest.TestCase):
    def setUp(self):
        self.reassembler = TransactionReassembler(timeout_seconds=60)

    def test_roundtrip_returns_original_hex(self):
        tx_hex = tx_of_size(372)
        messages = build_messages(tx_hex)
        result = None
        for msg in messages:
            result = self.reassembler.add_chunk("!sender01", msg)
        self.assertEqual(result, tx_hex)

    def test_intermediate_chunks_return_none(self):
        messages = build_messages(tx_of_size(372))
        self.assertGreater(len(messages), 1)
        for msg in messages[:-1]:
            self.assertIsNone(self.reassembler.add_chunk("!sender01", msg))

    def test_single_chunk_transaction(self):
        tx_hex = tx_of_size(100)
        messages = build_messages(tx_hex)
        self.assertEqual(len(messages), 1)
        self.assertEqual(self.reassembler.add_chunk("!sender01", messages[0]), tx_hex)

    def test_hex_sessions_still_work(self):
        """v1.0 regression: a hex client must be unaffected."""
        tx_hex = tx_of_size(372)
        result = None
        for msg in build_messages(tx_hex, encoding=ENCODING_HEX):
            result = self.reassembler.add_chunk("!oldclient", msg)
        self.assertEqual(result, tx_hex)

    def test_hex_and_base64_senders_concurrently(self):
        hex_tx, b64_tx = tx_of_size(200), tx_of_size(260)
        hex_msgs = build_messages(hex_tx, "hexse", ENCODING_HEX)
        b64_msgs = build_messages(b64_tx, "b64se", ENCODING_B64)
        hex_result = b64_result = None
        # Interleave the two sessions from different senders.
        for h, b in zip(hex_msgs, b64_msgs):
            hex_result = self.reassembler.add_chunk("!hexnode", h) or hex_result
            b64_result = self.reassembler.add_chunk("!b64node", b) or b64_result
        for h in hex_msgs[len(b64_msgs):]:
            hex_result = self.reassembler.add_chunk("!hexnode", h) or hex_result
        self.assertEqual(hex_result, hex_tx)
        self.assertEqual(b64_result, b64_tx)

    def test_mixed_encoding_in_one_session_is_rejected(self):
        tx_hex = tx_of_size(372)
        b64_msgs = build_messages(tx_hex, "mixed", ENCODING_B64)
        hex_msgs = build_messages(tx_hex, "mixed", ENCODING_HEX)
        self.reassembler.add_chunk("!sender01", b64_msgs[0])
        with self.assertRaises(MismatchedEncodingError):
            self.reassembler.add_chunk("!sender01", hex_msgs[1])

    def test_corrupt_base64_raises_invalid_chunk_format(self):
        tx_hex = tx_of_size(100)
        msg = build_messages(tx_hex)[0]
        head, _, payload = msg.rpartition("|")
        corrupt = f"{head}|{'!' * len(payload)}"
        with self.assertRaises(InvalidChunkFormatError):
            self.reassembler.add_chunk("!sender01", corrupt)

    def test_truncated_base64_raises_invalid_chunk_format(self):
        tx_hex = tx_of_size(100)
        msg = build_messages(tx_hex)[0]
        head, _, payload = msg.rpartition("|")
        with self.assertRaises(InvalidChunkFormatError):
            self.reassembler.add_chunk("!sender01", f"{head}|{payload[:-3]}")


class TestChunkEconomics(unittest.TestCase):
    """The whole point of the change: fewer packets, therefore fewer round trips."""

    CASES = [
        # (tx bytes, description, expected hex chunks, expected base64 chunks)
        (191, "1-in 1-out P2WPKH", 3, 2),
        (222, "1-in 2-out P2WPKH", 3, 2),
        (372, "2-in 2-out P2WPKH", 5, 3),
        (600, "larger multi-input", 8, 5),
    ]

    def test_chunk_counts(self):
        for size, desc, want_hex, want_b64 in self.CASES:
            tx_hex = tx_of_size(size)
            with self.subTest(tx=desc):
                self.assertEqual(
                    len(build_messages(tx_hex, encoding=ENCODING_HEX)), want_hex
                )
                self.assertEqual(
                    len(build_messages(tx_hex, encoding=ENCODING_B64)), want_b64
                )

    def test_base64_never_needs_more_chunks_than_hex(self):
        for size in range(1, 1200, 7):
            tx_hex = tx_of_size(size)
            with self.subTest(tx_bytes=size):
                self.assertLessEqual(
                    len(build_messages(tx_hex, encoding=ENCODING_B64)),
                    len(build_messages(tx_hex, encoding=ENCODING_HEX)),
                )


class TestMessageFitsOnAir(unittest.TestCase):
    def test_common_transactions_stay_within_v1_envelope(self):
        # Up to 9 chunks the chunk counter is 1 digit, so messages are exactly
        # as long as the ones v1.0 already ships.
        for size in (191, 222, 372, 600, 1100):
            for msg in build_messages(tx_of_size(size)):
                with self.subTest(tx_bytes=size):
                    self.assertLessEqual(len(msg), V1_ENVELOPE)

    def test_large_transactions_stay_well_under_the_radio_limit(self):
        # 3-digit chunk counters widen the header by 4 chars.
        for msg in build_messages(tx_of_size(20000)):
            self.assertLessEqual(len(msg), MESHTASTIC_PAYLOAD_LIMIT)

    def test_hex_messages_unchanged(self):
        for msg in build_messages(tx_of_size(600), encoding=ENCODING_HEX):
            self.assertLessEqual(len(msg), V1_ENVELOPE)


class TestCliEncodingFlag(unittest.TestCase):
    DEST = "!abcdef12"

    def _dry_run(self, tx_hex, **extra):
        attrs = {"destination": self.DEST, "tx": tx_hex, "dry_run": True}
        attrs.update(extra)
        Args = type("Args", (), attrs)
        with patch("builtins.print") as mock_print:
            code = cli_main(args=Args)
        self.assertEqual(code, 0)
        return [str(c.args[0]) for c in mock_print.call_args_list]

    def test_default_is_hex_so_v1_relays_keep_working(self):
        """Receivers upgrade before senders: the client default stays v1.0."""
        tx_hex = tx_of_size(200)
        lines = self._dry_run(tx_hex)
        chunk_lines = [ln for ln in lines if ln.startswith(CHUNK_PREFIX)]
        self.assertTrue(chunk_lines)
        self.assertFalse([ln for ln in lines if ln.startswith(CHUNK_PREFIX_B64)])
        self.assertIn(tx_hex[:CHUNK_SIZE], chunk_lines[0])

    def test_base64_opt_in_emits_btc_tx64(self):
        tx_hex = tx_of_size(372)
        lines = self._dry_run(tx_hex, encoding=ENCODING_B64)
        chunk_lines = [ln for ln in lines if ln.startswith(CHUNK_PREFIX_B64)]
        self.assertEqual(len(chunk_lines), 3)
        for i, line in enumerate(chunk_lines, 1):
            self.assertIn(f"|{i}/3|", line)

    def test_opt_in_output_reassembles_back_to_the_original(self):
        """End-to-end without a radio: CLI output straight into the server."""
        tx_hex = tx_of_size(600)
        lines = self._dry_run(tx_hex, encoding=ENCODING_B64)
        reassembler = TransactionReassembler(timeout_seconds=60)
        result = None
        for line in [ln for ln in lines if ln.startswith(CHUNK_PREFIX_B64)]:
            result = reassembler.add_chunk("!sender01", line)
        self.assertEqual(result, tx_hex)

    def test_explicit_hex_matches_default(self):
        tx_hex = tx_of_size(372)
        with_flag = [
            ln
            for ln in self._dry_run(tx_hex, encoding=ENCODING_HEX, session_id="fixed")
            if ln.startswith(CHUNK_PREFIX)
        ]
        without = [
            ln
            for ln in self._dry_run(tx_hex, session_id="fixed")
            if ln.startswith(CHUNK_PREFIX)
        ]
        self.assertEqual(with_flag, without)


if __name__ == "__main__":
    unittest.main()
