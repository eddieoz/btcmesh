# Server GUI Log Color Specification

This document defines how server log messages should be color-coded in the BTCMesh Server GUI activity log.

## Color Categories

| Color | Meaning | When to Use |
|-------|---------|-------------|
| 🟢 GREEN | Success/Connected | Successful operations, connections established |
| 🔴 RED | Error/Failure | Errors, failures, disconnects |
| 🟠 ORANGE | Warning | Warnings, potential issues requiring attention |
| ⚪ WHITE | Info/Normal | General information, status updates |

---

## GREEN Messages (Success/Connected)

These indicate successful operations and should give the operator confidence.

| Log Message Pattern | Log Level |
|---------------------|-----------|
| `Connected to Bitcoin Core RPC node successfully.` | INFO |
| `Meshtastic interface initialized successfully. Device: ..., My Node Num: ...` | INFO |
| `Registered Meshtastic message handler. Waiting for messages...` | INFO |
| `Successfully queued reply to {destination}: '...'` | INFO |
| `Successfully reassembled transaction: ...` | INFO |
| `Broadcast success. TXID: {txid}` | INFO |

**Keywords for detection:** `successfully`, `success`, `txid:`

---

## RED Messages (Errors/Failures)

These indicate problems that need attention.

| Log Message Pattern | Log Level |
|---------------------|-----------|
| `Failed to connect to Bitcoin Core RPC node: ...` | ERROR |
| `Failed to initialize Meshtastic interface. Exiting.` | ERROR |
| `No Meshtastic device found. Ensure it is connected...` | ERROR |
| `Meshtastic library error during initialization: ...` | ERROR |
| `Meshtastic library not found. Please install it...` | ERROR |
| `PubSub library not found. Please install it...` | ERROR |
| `Failed to subscribe to Meshtastic messages: ...` | ERROR |
| `Cannot send reply: Meshtastic interface is not available.` | ERROR |
| `Cannot send reply: Invalid destination_id format...` | ERROR |
| `Broadcast failed: ... Sending NACK.` | ERROR |
| `Reassembly error: ... Sending NACK.` | ERROR |
| `General reassembly error: ...` | ERROR |
| `Unexpected error processing chunk: ...` | ERROR |
| `Unhandled exception in main loop: ...` | ERROR |
| `Unhandled exception in main function: ...` | ERROR |
| `Cannot send timeout NACK: Meshtastic interface not available...` | ERROR |
| `Closing Meshtastic interface...` | INFO |
| `Session timed out. Sending NACK: ...` | INFO |
| `Session {id} aborted by {sender}: {reason}` | INFO |

**Detection rules:**
- All messages with log level >= ERROR
- INFO messages containing: `failed`, `nack`, `timed out`, `abort`, `cannot`, `closing`

**Note:** We use `timed out` (past tense) not `timeout` (noun) because `timeout` would incorrectly match config messages like `"Loaded reassembly timeout from env: 120s"`.

---

## ORANGE Messages (Warnings)

These indicate potential issues that may need attention.

| Log Message Pattern | Log Level |
|---------------------|-----------|
| `Received non-standard string node ID format: ...` | WARNING |

**Detection rules:**
- All messages with log level >= WARNING (but < ERROR)

---

## WHITE Messages (Info/Normal)

These are informational messages showing normal operation.

| Log Message Pattern | Log Level |
|---------------------|-----------|
| `Starting BTC Mesh Relay Server...` | INFO |
| `TransactionReassembler initialized with timeout: ...` | INFO |
| `rpc: {bitcoin_rpc}.` | INFO |
| `Attempting to initialize Meshtastic interface...` | INFO |
| `Attempting to send reply to ...` | INFO |
| `Potential BTC transaction chunk from ... Processing...` | INFO |
| `Std direct text from ... (not BTC_TX): '...'` | INFO |
| `Stop signal received. Shutting down...` | INFO |
| `Server shutting down by user request (Ctrl+C).` | INFO |

**Detection rules:**
- All other INFO messages not matching success or error keywords

---

## Implementation

Update `get_log_color()` in `core/gui_common.py`:

```python
def get_log_color(level: int, msg: str,
                  success_keywords: Optional[list] = None,
                  error_keywords: Optional[list] = None) -> Optional[Tuple]:
    """Determine the color for a log message based on level and content."""
    if success_keywords is None:
        success_keywords = ['successfully', 'success', 'txid:']
    if error_keywords is None:
        error_keywords = ['failed', 'nack', 'timed out', 'abort',
                         'cannot', 'closing']

    # ERROR level always red
    if level >= logging.ERROR:
        return COLOR_ERROR

    # WARNING level always orange
    if level >= logging.WARNING:
        return COLOR_WARNING

    # For INFO level, check content
    msg_lower = msg.lower()

    # Check for error keywords first (more specific)
    for keyword in error_keywords:
        if keyword in msg_lower:
            return COLOR_ERROR

    # Check for success keywords
    for keyword in success_keywords:
        if keyword in msg_lower:
            return COLOR_SUCCESS

    # Default: white/none
    return None
```

**Key changes from current implementation:**
1. Added `error_keywords` parameter for INFO-level error detection
2. Changed success keywords from `['success', 'ack', 'txid', 'broadcast']` to `['successfully', 'success', 'txid:']`
   - Removed `'ack'` - was matching `BTC_NACK` (false positive)
   - Removed `'broadcast'` - was matching `Broadcast failed` (false positive)
   - Added `'successfully'` - more specific
   - Changed `'txid'` to `'txid:'` - more specific
3. Error keywords checked before success keywords (more specific matching)
