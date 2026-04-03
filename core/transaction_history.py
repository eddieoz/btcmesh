"""Transaction history storage and retrieval.

Provides persistent storage for completed transaction records (success and failure).
Used by btcmesh_server to record broadcast results, and by GUI to display history.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# Default path relative to project root
DEFAULT_HISTORY_FILE = "data/transaction_history.json"


class TransactionHistory:
    """Manages persistent transaction history storage.

    Stores completed transactions (success and failure) in a JSON file.
    Thread-safe for concurrent access.

    Example:
        history = TransactionHistory()
        history.add(
            session_id="a1b2c",
            sender="!12345678",
            status="success",
            txid="abc123...def789",
            raw_tx="0100000001..."
        )
        entries = history.get_all()
    """

    def __init__(self, filepath: str = DEFAULT_HISTORY_FILE):
        """Initialize TransactionHistory.

        Args:
            filepath: Path to the JSON history file. Defaults to data/transaction_history.json.
                      Parent directory will be created if it doesn't exist.
        """
        self._filepath = Path(filepath)
        self._lock = threading.Lock()
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Create the data directory and history file if they don't exist."""
        # Create parent directory if needed
        self._filepath.parent.mkdir(parents=True, exist_ok=True)

        # Create empty history file if it doesn't exist
        if not self._filepath.exists():
            self._save_data({"version": 1, "transactions": []})

    def _load_data(self) -> Dict[str, Any]:
        """Load history data from file.

        Returns:
            Dict with 'version' and 'transactions' keys.
        """
        try:
            with open(self._filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Ensure required structure
                if "transactions" not in data:
                    data["transactions"] = []
                if "version" not in data:
                    data["version"] = 1
                return data
        except (json.JSONDecodeError, FileNotFoundError):
            # Return empty structure on error
            return {"version": 1, "transactions": []}

    def _save_data(self, data: Dict[str, Any]) -> None:
        """Save history data to file.

        Args:
            data: Dict with 'version' and 'transactions' keys.
        """
        with open(self._filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add(
        self,
        session_id: str,
        sender: str,
        status: str,
        txid: Optional[str] = None,
        error: Optional[str] = None,
        raw_tx: Optional[str] = None
    ) -> None:
        """Add a transaction entry to history.

        Args:
            session_id: The transaction session ID (e.g., "a1b2c").
            sender: The sender node ID (e.g., "!12345678").
            status: Either "success" or "failed".
            txid: The transaction ID (for successful broadcasts).
            error: The error message (for failed broadcasts).
            raw_tx: The raw transaction hex string.
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "sender": sender,
            "status": status,
            "txid": txid,
            "error": error,
            "raw_tx": raw_tx
        }

        with self._lock:
            data = self._load_data()
            # Insert at beginning (newest first)
            data["transactions"].insert(0, entry)
            self._save_data(data)

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all transaction entries.

        Returns:
            List of transaction entries, newest first.
        """
        with self._lock:
            data = self._load_data()
            return data.get("transactions", [])

    def clear(self) -> None:
        """Clear all transaction history.

        Primarily useful for testing.
        """
        with self._lock:
            self._save_data({"version": 1, "transactions": []})

    @property
    def filepath(self) -> Path:
        """Return the path to the history file."""
        return self._filepath
