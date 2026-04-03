"""Unit tests for core/transaction_history.py."""

import json
import os
import tempfile
import unittest
from pathlib import Path

from core.transaction_history import TransactionHistory


class TestTransactionHistory(unittest.TestCase):
    """Tests for TransactionHistory class."""

    def setUp(self):
        """Create a temporary file for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = os.path.join(self.temp_dir, "data", "test_history.json")
        self.history = TransactionHistory(filepath=self.temp_file)

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_creates_directory_and_file(self):
        """Test that directory and file are created on init."""
        self.assertTrue(Path(self.temp_file).exists())
        self.assertTrue(Path(self.temp_file).parent.exists())

    def test_empty_history_returns_empty_list(self):
        """Test that new history returns empty list."""
        entries = self.history.get_all()
        self.assertEqual(entries, [])

    def test_add_success_entry(self):
        """Test adding a successful transaction."""
        self.history.add(
            session_id="sess1",
            sender="!12345678",
            status="success",
            txid="abc123def456",
            raw_tx="0100000001..."
        )

        entries = self.history.get_all()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["session_id"], "sess1")
        self.assertEqual(entries[0]["sender"], "!12345678")
        self.assertEqual(entries[0]["status"], "success")
        self.assertEqual(entries[0]["txid"], "abc123def456")
        self.assertEqual(entries[0]["raw_tx"], "0100000001...")
        self.assertIsNone(entries[0]["error"])
        self.assertIn("timestamp", entries[0])

    def test_add_failed_entry(self):
        """Test adding a failed transaction."""
        self.history.add(
            session_id="sess2",
            sender="!deadbeef",
            status="failed",
            error="Insufficient fee",
            raw_tx="0200000001..."
        )

        entries = self.history.get_all()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["status"], "failed")
        self.assertEqual(entries[0]["error"], "Insufficient fee")
        self.assertIsNone(entries[0]["txid"])

    def test_newest_first_order(self):
        """Test that entries are returned newest first."""
        self.history.add(session_id="first", sender="!111", status="success")
        self.history.add(session_id="second", sender="!222", status="success")
        self.history.add(session_id="third", sender="!333", status="success")

        entries = self.history.get_all()
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0]["session_id"], "third")
        self.assertEqual(entries[1]["session_id"], "second")
        self.assertEqual(entries[2]["session_id"], "first")

    def test_persistence_across_instances(self):
        """Test that history persists when creating new instance."""
        self.history.add(session_id="persist", sender="!abc", status="success")

        # Create new instance pointing to same file
        new_history = TransactionHistory(filepath=self.temp_file)
        entries = new_history.get_all()

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["session_id"], "persist")

    def test_clear_removes_all_entries(self):
        """Test that clear() removes all entries."""
        self.history.add(session_id="a", sender="!1", status="success")
        self.history.add(session_id="b", sender="!2", status="failed")

        self.assertEqual(len(self.history.get_all()), 2)

        self.history.clear()

        self.assertEqual(len(self.history.get_all()), 0)

    def test_handles_corrupted_file(self):
        """Test that corrupted JSON file is handled gracefully."""
        # Write invalid JSON
        with open(self.temp_file, 'w') as f:
            f.write("not valid json{{{")

        # Should not raise, returns empty
        entries = self.history.get_all()
        self.assertEqual(entries, [])

        # Should be able to add new entries
        self.history.add(session_id="new", sender="!new", status="success")
        entries = self.history.get_all()
        self.assertEqual(len(entries), 1)

    def test_handles_missing_transactions_key(self):
        """Test handling of file with missing transactions key."""
        with open(self.temp_file, 'w') as f:
            json.dump({"version": 1}, f)

        entries = self.history.get_all()
        self.assertEqual(entries, [])

    def test_filepath_property(self):
        """Test that filepath property returns correct path."""
        self.assertEqual(self.history.filepath, Path(self.temp_file))

    def test_json_file_format(self):
        """Test that the JSON file has correct structure."""
        self.history.add(
            session_id="test",
            sender="!sender",
            status="success",
            txid="txid123",
            raw_tx="rawtx"
        )

        with open(self.temp_file, 'r') as f:
            data = json.load(f)

        self.assertIn("version", data)
        self.assertEqual(data["version"], 1)
        self.assertIn("transactions", data)
        self.assertIsInstance(data["transactions"], list)


class TestTransactionHistoryThreadSafety(unittest.TestCase):
    """Tests for thread safety of TransactionHistory."""

    def setUp(self):
        """Create a temporary file for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = os.path.join(self.temp_dir, "data", "thread_test.json")
        self.history = TransactionHistory(filepath=self.temp_file)

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_concurrent_writes(self):
        """Test that concurrent writes don't corrupt data."""
        import threading

        num_threads = 10
        entries_per_thread = 5

        def add_entries(thread_id):
            for i in range(entries_per_thread):
                self.history.add(
                    session_id=f"t{thread_id}_e{i}",
                    sender=f"!{thread_id:04x}",
                    status="success"
                )

        threads = [
            threading.Thread(target=add_entries, args=(i,))
            for i in range(num_threads)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        entries = self.history.get_all()
        self.assertEqual(len(entries), num_threads * entries_per_thread)


if __name__ == "__main__":
    unittest.main()
