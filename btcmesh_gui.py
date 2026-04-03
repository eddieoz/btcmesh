#!/usr/bin/env python3
"""
BTCMesh GUI Client - Kivy-based graphical interface for sending Bitcoin transactions
via Meshtastic LoRa relay.

This GUI wraps the btcmesh_cli module, displaying its log output in a graphical interface.
"""
import threading
import queue
import logging
import argparse
import io
import sys
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Any
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.clipboard import Clipboard
from kivy.properties import StringProperty, BooleanProperty

# Import shared GUI components
from core.gui_common import (
    # Colors
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_ERROR,
    COLOR_WARNING,
    COLOR_BG,
    COLOR_BG_LIGHT,
    COLOR_SECUNDARY,
    COLOR_DISCONNECTED,
    # Classes
    ConnectionState,
    StatusLog,
    # Functions
    get_log_color,
    get_print_color,
    create_separator,
    create_section_label,
    create_title,
    create_action_button,
    create_clear_button,
    create_refresh_button,
    create_popup_button,
)

# Import Meshtastic utilities from core
from core.meshtastic_utils import (
    scan_meshtastic_devices,
    get_own_node_name,
    get_known_nodes,
    format_node_display,
)


# Import btcmesh_cli functions
from btcmesh_cli import (
    is_valid_hex,
    cli_main,
    EXAMPLE_RAW_TX,
)

# Device selection constants
NO_DEVICES_TEXT = "No devices found"
SCANNING_TEXT = "Scanning..."

# Node selection constants
NO_NODES_TEXT = "No nodes found"
MANUAL_ENTRY_TEXT = "Enter manually..."

# Set window size for desktop testing
Window.size = (450, 700)

# Connection states (using ConnectionState from gui_common)
STATE_DISCONNECTED = ConnectionState('Meshtastic: Not connected', COLOR_DISCONNECTED)
STATE_CONNECTION_FAILED = ConnectionState('Meshtastic: Connection failed', COLOR_ERROR)
STATE_CONNECTION_ERROR = ConnectionState('Meshtastic: Error', COLOR_ERROR)


@dataclass
class ResultAction:
    """Represents the actions to take in response to a result from a background thread.

    This dataclass separates the logic of determining what to do from the actual
    GUI updates, making the logic testable without Kivy.
    """
    # Connection label updates
    connection_text: Optional[str] = None
    connection_color: Optional[Tuple] = None

    # Log messages to display: list of (message, color) tuples
    log_messages: List[Tuple[str, Optional[Tuple]]] = field(default_factory=list)

    # State changes
    stop_sending: bool = False

    # Popup actions
    show_success_popup: Optional[str] = None  # txid if success popup should be shown

    # Interface to store (for 'connected' result type)
    store_iface: Optional[Any] = None


def process_result(result: tuple) -> ResultAction:
    """Process a result tuple and return the actions to take.

    This is a pure function that determines what GUI actions should be performed
    based on the result, without actually performing them.

    Args:
        result: A tuple where result[0] is the result type string

    Returns:
        A ResultAction describing what GUI updates to make
    """
    action = ResultAction()
    result_type = result[0]

    if result_type == 'connected':
        iface = result[1]
        node_id = result[2]
        node_name = result[3] if len(result) > 3 else None
        action.store_iface = iface
        if node_name:
            action.connection_text = f'Meshtastic: Connected - {node_name} ({node_id})'
            action.log_messages.append((f"Connected to Meshtastic device: {node_name} ({node_id})", COLOR_SUCCESS))
        else:
            action.connection_text = f'Meshtastic: Connected ({node_id})'
            action.log_messages.append((f"Connected to Meshtastic device: {node_id}", COLOR_SUCCESS))
        action.connection_color = COLOR_SUCCESS

    elif result_type == 'connection_failed':
        action.connection_text = STATE_CONNECTION_FAILED.text
        action.connection_color = STATE_CONNECTION_FAILED.color
        # Use specific error message if provided, otherwise generic message
        error_msg = result[1] if len(result) > 1 and result[1] else "Failed to connect to Meshtastic device"
        action.log_messages.append((error_msg, COLOR_ERROR))

    elif result_type == 'connection_error':
        error = result[1]
        action.connection_text = STATE_CONNECTION_ERROR.text
        action.connection_color = STATE_CONNECTION_ERROR.color
        action.log_messages.append((f"Connection error: {error}", COLOR_ERROR))

    elif result_type == 'connection_initializing':
        # Device is still initializing - show informational message
        action.log_messages.append(("Device is initializing, please wait...", COLOR_WARNING))
        action.connection_text = 'Meshtastic: Initializing...'
        action.connection_color = COLOR_WARNING

    elif result_type == 'log':
        msg = result[1]
        level = result[2]
        color = get_log_color(level, msg)
        action.log_messages.append((msg, color))

    elif result_type == 'print':
        msg = result[1]
        color = get_print_color(msg)
        action.log_messages.append((msg, color))

        # Detect success message with TXID and trigger popup
        # CLI prints: "Transaction successfully broadcast by relay. TXID: <txid>"
        if 'TXID:' in msg and 'successfully' in msg.lower():
            # Extract TXID from message
            txid_start = msg.find('TXID:') + 5
            txid = msg[txid_start:].strip().split()[0] if txid_start > 5 else 'Unknown'
            action.show_success_popup = txid
            action.stop_sending = True

    elif result_type == 'cli_finished':
        exit_code = result[1]
        if exit_code == 0:
            action.log_messages.append(("Transaction completed successfully!", COLOR_SUCCESS))
        else:
            action.log_messages.append((f"CLI exited with code {exit_code}", COLOR_ERROR))
        action.stop_sending = True

    elif result_type == 'tx_success':
        txid = result[1]
        action.log_messages.append(("Transaction broadcast successful!", COLOR_SUCCESS))
        action.log_messages.append((f"TXID: {txid}", COLOR_SUCCESS))
        action.show_success_popup = txid
        action.stop_sending = True

    elif result_type == 'error':
        error = result[1]
        action.log_messages.append((f"Error: {error}", COLOR_ERROR))
        action.stop_sending = True

    elif result_type == 'aborted':
        action.log_messages.append(("Transaction aborted by user", COLOR_WARNING))
        action.stop_sending = True

    return action


def validate_send_inputs(dest: str, tx_hex: str, has_iface: bool, dry_run: bool = False,
                        own_node_id: Optional[str] = None) -> Optional[str]:
    """Validate the inputs for sending a transaction.

    This is a pure function that validates inputs without touching the GUI.

    Args:
        dest: The destination node ID
        tx_hex: The raw transaction hex (already cleaned of whitespace)
        has_iface: Whether the Meshtastic interface is connected
        dry_run: Whether this is a dry run (skips Meshtastic connection check)
        own_node_id: The node ID of the connected device (for self-send check)

    Returns:
        An error message string if validation fails, or None if inputs are valid
    """
    if not dest:
        return "Enter destination node ID"

    if not dest.startswith('!'):
        return "Destination must start with '!'"

    # Check for sending to own node
    if own_node_id and dest.lower() == own_node_id.lower():
        return "Cannot send to your own node"

    if not tx_hex:
        return "Enter transaction hex"

    if len(tx_hex) % 2 != 0:
        return "Hex must have even length"

    if not is_valid_hex(tx_hex):
        return "Invalid hex characters"

    if not has_iface and not dry_run:
        return "Meshtastic not connected"

    return None


class QueueLogHandler(logging.Handler):
    """Custom log handler that sends log records to a queue for GUI display."""

    def __init__(self, result_queue):
        super().__init__()
        self.result_queue = result_queue

    def emit(self, record):
        try:
            msg = self.format(record)
            level = record.levelno
            self.result_queue.put(('log', msg, level))
        except Exception:
            self.handleError(record)

class BTCMeshGUI(BoxLayout):
    """Main GUI widget."""

    status_text = StringProperty('Ready')
    is_sending = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 15
        self.spacing = 20

        self.iface = None
        self.send_thread = None
        self.result_queue = queue.Queue()
        self.abort_requested = False
        self._connection_monitor = None  # Track the connection state monitor

        self._build_ui()

        # Schedule periodic check for thread results
        Clock.schedule_interval(self._check_results, 0.1)

    def _build_ui(self):
        """Build the user interface."""
        # Title
        self.add_widget(create_title('BTCMesh Transaction Relay'))

        # Orange separator line
        self.add_widget(create_separator())

        # Device selection row
        self.add_widget(create_section_label('Your Device:'))

        device_selection_box = BoxLayout(size_hint_y=None, height=40, spacing=10)

        # Spinner (drop down list)
        self.device_spinner = Spinner(
            text=SCANNING_TEXT,
            values=[],
            size_hint_x=1,
            background_color=COLOR_BG_LIGHT,
            background_normal='',
            color=COLOR_SECUNDARY,
        )
        self.device_spinner.bind(text=self.on_device_selected)
        device_selection_box.add_widget(self.device_spinner)

        # Refresh button
        self.refresh_btn = create_refresh_button('Scan')
        self.refresh_btn.bind(on_press=self.on_refresh_devices)
        device_selection_box.add_widget(self.refresh_btn)

        self.add_widget(device_selection_box)

        # Destination input section
        self.add_widget(create_section_label('Destination Node ID:'))

        # Node selection row (Spinner + TextInput + Refresh)
        dest_selection_box = BoxLayout(size_hint_y=None, height=45, spacing=5)

        # Known nodes cache for mapping display text back to node id
        self.known_nodes = []

        # Spinner for known nodes
        self.node_spinner = Spinner(
            text=MANUAL_ENTRY_TEXT,
            values=[MANUAL_ENTRY_TEXT],
            size_hint_x=0.5,
            background_color=COLOR_BG_LIGHT,
            background_normal='',
            color=COLOR_SECUNDARY,
        )
        self.node_spinner.bind(text=self.on_node_selected)
        dest_selection_box.add_widget(self.node_spinner)

        # TextInput for destination (manual entry or selected from dropdown)
        self.dest_input = TextInput(
            hint_text='!node_id',
            multiline=False,
            size_hint_x=0.4,
            background_color=COLOR_BG_LIGHT,
            foreground_color=COLOR_SECUNDARY,
            cursor_color=COLOR_SECUNDARY,
        )
        dest_selection_box.add_widget(self.dest_input)

        # Refresh nodes button
        self.refresh_nodes_btn = create_refresh_button('Scan')
        self.refresh_nodes_btn.bind(on_press=self.on_refresh_nodes)
        dest_selection_box.add_widget(self.refresh_nodes_btn)

        self.add_widget(dest_selection_box)

        # TX Hex input
        self.add_widget(create_section_label('Raw Transaction Hex:'))
        self.tx_input = TextInput(
            hint_text='Paste raw transaction hex here...',
            multiline=True,
            size_hint_y=None,
            height=180,
            background_color=COLOR_BG_LIGHT,
            foreground_color=COLOR_SECUNDARY,
            cursor_color=COLOR_SECUNDARY,
        )
        self.add_widget(self.tx_input)

        # Dry run toggle
        dry_run_box = BoxLayout(size_hint_y=None, height=40, spacing=10)

        # Label first, takes remaining space
        dry_run_box.add_widget(create_section_label('Dry run (simulate only)'))

        # Toggle button on the right with fixed width
        self.dry_run_toggle = ToggleButton(
            text='NO',
            size_hint_x=None,
            width=60,
            background_color=COLOR_BG_LIGHT,
            background_normal='',
            background_down='',
        )

        def update_dry_run_toggle(instance, state):
            if state == 'down':
                instance.text = 'YES'
                instance.background_color = COLOR_PRIMARY
            else:
                instance.text = 'NO'
                instance.background_color = COLOR_BG_LIGHT

        self.dry_run_toggle.bind(state=update_dry_run_toggle)
        dry_run_box.add_widget(self.dry_run_toggle)

        self.add_widget(dry_run_box)

        # Orange separator line
        self.add_widget(create_separator())

        # Button row
        btn_box = BoxLayout(size_hint_y=None, height=50, spacing=10)

        self.send_btn = create_action_button('Send Transaction')
        self.send_btn.bind(on_press=self.on_send_pressed)
        btn_box.add_widget(self.send_btn)

        self.example_btn = create_action_button('Load Hex Example', color=COLOR_BG_LIGHT, bold=False)
        self.example_btn.bind(on_press=self.on_load_example)
        btn_box.add_widget(self.example_btn)

        self.abort_btn = create_action_button('Abort', color=COLOR_ERROR, disabled=True)
        self.abort_btn.bind(on_press=self.on_abort_pressed)
        btn_box.add_widget(self.abort_btn)

        self.add_widget(btn_box)

        # Connection status
        self.connection_label = Label(
            text=STATE_DISCONNECTED.text,
            size_hint_y=None,
            height=25,
            color=STATE_DISCONNECTED.color,
        )
        self.add_widget(self.connection_label)

        # Status/Log area
        self.add_widget(create_section_label('Activity Log:'))
        self.status_log = StatusLog(size_hint_y=1)
        self.add_widget(self.status_log)

        # Clear button at bottom
        self.clear_btn = create_clear_button(self.on_clear)
        self.add_widget(self.clear_btn)

        # Scan for devices on startup
        Clock.schedule_once(lambda dt: self._scan_devices(), 1)

    def _scan_devices(self):
        """Scan for available Meshtastic devices in background."""
        self.device_spinner.text = SCANNING_TEXT
        self.status_log.add_message("Scanning for Meshtastic devices...")

        def scan_thread():
            devices = scan_meshtastic_devices()
            self.result_queue.put(('devices_found', devices))

        threading.Thread(target=scan_thread, daemon=True).start()

    def _init_meshtastic(self, port=None):
        """Initialize Meshtastic interface in background.

        Args:
            port: Optional device path to connect to. If None, uses auto-detect.
        """
        self.status_log.add_message(f"Connecting to Meshtastic device{f' ({port})' if port else ''}...")

        def init_thread():
            try:
                import meshtastic.serial_interface

                iface = (
                    meshtastic.serial_interface.SerialInterface(devPath=port)
                    if port
                    else meshtastic.serial_interface.SerialInterface()
                )

                # Validate we got valid device info
                node_id = None
                if hasattr(iface, 'myInfo') and iface.myInfo and hasattr(iface.myInfo, 'my_node_num'):
                    node_id = f"!{iface.myInfo.my_node_num:x}"

                if not node_id or not node_id.startswith('!'):
                    # Interface created but device info invalid - likely no device connected
                    try:
                        iface.close()
                    except Exception:
                        pass
                    self.result_queue.put(('connection_failed', "Could not retrieve device info. Ensure device is connected.", None))
                    return

                node_name = get_own_node_name(iface)
                self.result_queue.put(('connected', iface, node_id, node_name))

            except ImportError:
                self.result_queue.put(('connection_error', "Meshtastic library not installed", None))
            except Exception as e:
                error_msg = str(e)
                # Check if this is a transient error from the Meshtastic library still initializing
                is_transient = any(x in error_msg.lower() for x in [
                    'resource temporarily unavailable',
                    'busy',
                ])
                if is_transient:
                    # Show as info message - device is still initializing
                    self.result_queue.put(('connection_initializing', error_msg, None))
                else:
                    # Provide more helpful error messages for common cases
                    if "No Meshtastic" in error_msg or "No serial" in error_msg:
                        error_msg = "No Meshtastic device found"
                    elif "Permission denied" in error_msg:
                        error_msg = f"Permission denied accessing {port or 'device'}"
                    elif "could not open port" in error_msg.lower():
                        error_msg = f"Could not open port {port or '(auto-detect)'}"
                    self.result_queue.put(('connection_error', error_msg, None))

        threading.Thread(target=init_thread, daemon=True).start()

    def _disconnect_device(self):
        """Disconnect current Meshtastic interface and reset connection status."""
        if self.iface:
            # Close interface in background thread to avoid blocking main thread
            # (iface.close() can block if device is in a bad state)
            iface_to_close = self.iface
            self.iface = None

            def close_thread():
                try:
                    iface_to_close.close()
                except Exception:
                    pass

            threading.Thread(target=close_thread, daemon=True).start()
        self.connection_label.text = STATE_DISCONNECTED.text
        self.connection_label.color = STATE_DISCONNECTED.color
        # Clear known nodes
        self.known_nodes = []
        self.node_spinner.values = [MANUAL_ENTRY_TEXT]
        self.node_spinner.text = MANUAL_ENTRY_TEXT

    def on_device_selected(self, spinner, text):
        """Handle device selection from dropdown."""
        if text in (NO_DEVICES_TEXT, SCANNING_TEXT, ''):
            return

        self._disconnect_device()
        self._init_meshtastic(port=text)

    def on_refresh_devices(self, instance):
        """Handle refresh button press to rescan devices."""
        self._disconnect_device()
        self._scan_devices()

    def on_node_selected(self, spinner, text):
        """Handle node selection from dropdown."""
        if text == MANUAL_ENTRY_TEXT:
            # Clear input for fresh manual entry
            self.dest_input.text = ''
            return
        if text in (NO_NODES_TEXT, ''):
            return

        # Find the node ID from the formatted display text
        for node in self.known_nodes:
            if format_node_display(node) == text:
                self.dest_input.text = node['id']
                break

    def on_refresh_nodes(self, instance):
        """Handle refresh button press to update known nodes list."""
        self._update_known_nodes()

    def _update_known_nodes(self):
        """Update the known nodes dropdown from the connected interface."""
        if not self.iface:
            self.node_spinner.values = [NO_NODES_TEXT]
            self.node_spinner.text = NO_NODES_TEXT
            self.known_nodes = []
            return

        nodes = get_known_nodes(self.iface)
        self.known_nodes = nodes

        if not nodes:
            self.node_spinner.values = [MANUAL_ENTRY_TEXT, NO_NODES_TEXT]
            self.node_spinner.text = MANUAL_ENTRY_TEXT
        else:
            # Format nodes for display and add manual entry option
            formatted_nodes = [format_node_display(n) for n in nodes]
            self.node_spinner.values = [MANUAL_ENTRY_TEXT] + formatted_nodes
            self.node_spinner.text = MANUAL_ENTRY_TEXT
            self.status_log.add_message(f"Found {len(nodes)} known node(s)", COLOR_SUCCESS)

    def _check_results(self, dt):
        """Check for results from background threads."""
        try:
            while True:
                result = self.result_queue.get_nowait()
                self._handle_result(result)
        except queue.Empty:
            pass

    def _handle_result(self, result):
        """Handle a result from a background thread.

        Uses process_result to determine actions, then applies them to the GUI.
        """
        # Handle devices_found specially since it needs spinner access
        if result[0] == 'devices_found':
            devices = result[1]
            if devices:
                self.device_spinner.values = devices
                if len(devices) == 1:
                    # Auto-select and connect to single device
                    self.device_spinner.text = devices[0]
                    self.status_log.add_message(f"Found 1 device: {devices[0]}", COLOR_SUCCESS)
                    self._init_meshtastic(port=devices[0])
                else:
                    # Multiple devices - show first but don't connect, let user choose
                    # Unbind to prevent auto-connect when setting text
                    self.device_spinner.unbind(text=self.on_device_selected)
                    self.device_spinner.text = devices[0]
                    self.device_spinner.bind(text=self.on_device_selected)
                    self.status_log.add_message(f"Found {len(devices)} devices - select one to connect", COLOR_WARNING)
            else:
                self.device_spinner.values = [NO_DEVICES_TEXT]
                self.device_spinner.text = NO_DEVICES_TEXT
                self.status_log.add_message("No Meshtastic devices found", COLOR_ERROR)
            return

        action = process_result(result)

        # Apply connection label updates
        if action.connection_text is not None:
            self.connection_label.text = action.connection_text
        if action.connection_color is not None:
            self.connection_label.color = action.connection_color

        # Store interface if provided
        if action.store_iface is not None:
            self.iface = action.store_iface

        # Add log messages first (before _update_known_nodes which also logs)
        for msg, color in action.log_messages:
            self.status_log.add_message(msg, color)

        # Fetch known nodes AFTER connection success message is logged
        if action.store_iface is not None:
            self._update_known_nodes()

        # Handle state changes
        if action.stop_sending:
            self.is_sending = False
            self.send_btn.disabled = False
            self.abort_btn.disabled = True
            self._set_controls_enabled(True)  # Re-enable input controls

        # Show popups
        if action.show_success_popup is not None:
            self._show_success_popup(action.show_success_popup)

    def _get_own_node_id(self) -> Optional[str]:
        """Get the node ID of the connected Meshtastic device.

        Returns:
            Node ID string (e.g., '!abcd1234') or None if not connected.
        """
        if not self.iface or not self.iface.myInfo:
            return None
        try:
            node_num = self.iface.myInfo.my_node_num
            return f"!{node_num:08x}"
        except (AttributeError, TypeError):
            return None

    def _set_controls_enabled(self, enabled: bool):
        """Enable or disable input controls during transaction send.

        Args:
            enabled: True to enable controls, False to disable them.

        Controls affected:
            - device_spinner: Device selection dropdown
            - refresh_btn: Device scan button
            - node_spinner: Known nodes dropdown
            - dest_input: Destination input field
            - refresh_nodes_btn: Node scan button
            - tx_input: Transaction hex input field
            - dry_run_toggle: Dry run toggle button
            - example_btn: Load Hex Example button
        """
        self.device_spinner.disabled = not enabled
        self.refresh_btn.disabled = not enabled
        self.node_spinner.disabled = not enabled
        self.dest_input.disabled = not enabled
        self.refresh_nodes_btn.disabled = not enabled
        self.tx_input.disabled = not enabled
        self.dry_run_toggle.disabled = not enabled
        self.example_btn.disabled = not enabled

    def on_send_pressed(self, instance):
        """Handle send button press."""
        dest = self.dest_input.text.strip()
        tx_hex = self.tx_input.text.strip().replace('\n', '').replace(' ', '')
        dry_run = self.dry_run_toggle.state == 'down'

        # Validation (dry_run skips Meshtastic connection check)
        own_node_id = self._get_own_node_id()
        error = validate_send_inputs(dest, tx_hex, bool(self.iface), dry_run, own_node_id=own_node_id)
        if error:
            self.status_log.add_message(f"Error: {error}", COLOR_ERROR)
            if error == "Meshtastic not connected":
                self._init_meshtastic()
            return

        # Start sending
        self.is_sending = True
        self.send_btn.disabled = True
        self.abort_btn.disabled = False
        self.abort_requested = False
        self._set_controls_enabled(False)  # Disable input controls during send
        self.status_log.clear()
        if dry_run:
            self.status_log.add_message(f"Starting DRY RUN transaction send to {dest}...")
        else:
            self.status_log.add_message(f"Starting transaction send to {dest}...")

        # Run send in background thread
        self.send_thread = threading.Thread(
            target=self._send_transaction_thread,
            args=(dest, tx_hex, dry_run),
            daemon=True
        )
        self.send_thread.start()

    def _send_transaction_thread(self, dest, tx_hex, dry_run):
        """Send transaction in background thread using cli_main."""
        gui_instance = self  # Reference to check abort_requested

        class AbortedException(Exception):
            """Raised when user requests abort."""
            pass

        try:
            # Create a custom logger that sends to our queue
            gui_logger = logging.getLogger('btcmesh_gui')
            gui_logger.setLevel(logging.DEBUG)
            gui_logger.handlers.clear()  # Remove any existing handlers

            queue_handler = QueueLogHandler(self.result_queue)
            queue_handler.setFormatter(logging.Formatter('%(message)s'))
            gui_logger.addHandler(queue_handler)

            # Create args namespace to pass to cli_main
            args = argparse.Namespace(
                destination=dest,
                tx=tx_hex,
                dry_run=dry_run,
                session_id=None  # Let cli_main generate one
            )

            # Capture print output by redirecting stdout
            class PrintCapture(io.StringIO):
                def __init__(self, result_queue):
                    super().__init__()
                    self.result_queue = result_queue
                    self.original_stdout = sys.stdout

                def write(self, text):
                    # Check for abort request
                    if gui_instance.abort_requested:
                        raise AbortedException()
                    # Write to original stdout for debugging
                    self.original_stdout.write(text)
                    # Send non-empty lines to the queue
                    text = text.strip()
                    if text:
                        self.result_queue.put(('print', text))
                    return len(text)

                def flush(self):
                    self.original_stdout.flush()

            # Check for abort before starting
            if self.abort_requested:
                self.result_queue.put(('aborted',))
                return

            # Run cli_main with our injected logger and interface
            print_capture = PrintCapture(self.result_queue)
            original_stdout = sys.stdout

            try:
                sys.stdout = print_capture
                exit_code = cli_main(
                    args=args,
                    injected_iface=self.iface,
                    injected_logger=gui_logger
                )
            finally:
                sys.stdout = original_stdout

            # Check for abort after completion
            if self.abort_requested:
                self.result_queue.put(('aborted',))
            else:
                self.result_queue.put(('cli_finished', exit_code))

        except AbortedException:
            self.result_queue.put(('aborted',))
        except Exception as e:
            gui_logger.error(f"GUI send error: {e}", exc_info=True)
            self.result_queue.put(('error', str(e)))

    def _show_success_popup(self, txid):
        """Show success popup with TXID."""
        # Create content with dark background
        content = BoxLayout(orientation='vertical', padding=30, spacing=15)
        with content.canvas.before:
            Color(*COLOR_BG)
            self._popup_bg = Rectangle(pos=content.pos, size=content.size)
        content.bind(pos=lambda inst, val: setattr(self._popup_bg, 'pos', val))
        content.bind(size=lambda inst, val: setattr(self._popup_bg, 'size', val))

        # Top spacer for space between popup top and content
        content.add_widget(Widget(size_hint_y=None, height=15))

        # Success title in green
        content.add_widget(Label(
            text='Transaction Sent!',
            font_size=32,
            bold=True,
            color=COLOR_SUCCESS,
            size_hint_y=None,
            height=50,
        ))

        # TXID label
        content.add_widget(Label(
            text='TXID:',
            font_size=24,
            color=(0.7, 0.7, 0.7, 1),
            size_hint_y=None,
            height=35,
        ))

        # TXID value in white (larger font, wrapping enabled)
        content.add_widget(Label(
            text=txid,
            font_size=24,
            color=COLOR_SECUNDARY,
            text_size=(380, None),
            size_hint_y=None,
            height=70,
            halign='center',
        ))

        # Spacer
        content.add_widget(Widget(size_hint_y=None, height=20))

        # Button column with Copy and OK buttons
        btn_row = BoxLayout(orientation='vertical', size_hint_y=None, height=110, spacing=10)

        # Copy button
        copy_btn = Button(
            text='Copy',
            background_color=COLOR_SECUNDARY,
            background_normal='',
            color=(0, 0, 0, 1),  # Black text
            bold=True,
            font_size=24,
        )

        def on_copy(instance):
            Clipboard.copy(txid)
            instance.text = 'Copied!'
            Clock.schedule_once(lambda dt: setattr(instance, 'text', 'Copy'), 1.5)

        copy_btn.bind(on_press=on_copy)
        btn_row.add_widget(copy_btn)

        # OK button styled like app buttons
        ok_btn = create_popup_button('OK', primary=True)
        btn_row.add_widget(ok_btn)

        content.add_widget(btn_row)

        # Calculate popup size based on content
        content_height = sum(child.height for child in content.children)
        padding_height = content.padding[1] + content.padding[3] if len(content.padding) == 4 else content.padding * 2
        spacing_height = content.spacing * (len(content.children) - 1)
        popup_height = content_height + padding_height + spacing_height
        # Width based on TXID text_size (380) + horizontal padding (30 * 2)
        popup_width = 440

        popup = Popup(
            title='',
            content=content,
            size_hint=(None, None),
            size=(popup_width, popup_height),
            auto_dismiss=True,
            separator_height=0,
            background_color=COLOR_BG,
            background='',
        )
        ok_btn.bind(on_press=popup.dismiss)
        popup.open()

    def on_load_example(self, instance):
        """Load example transaction hex."""
        self.tx_input.text = EXAMPLE_RAW_TX
        self.status_log.add_message("Loaded example transaction hex")

    def on_abort_pressed(self, instance):
        """Handle abort button press."""
        if self.is_sending:
            self.abort_requested = True
            self.status_log.add_message("Abort requested...", COLOR_WARNING)
            self.abort_btn.disabled = True

    def on_clear(self, instance):
        """Clear the status log."""
        self.status_log.clear()
        self.status_log.add_message("Log cleared")


class BTCMeshApp(App):
    """Main Kivy application."""

    def build(self):
        self.title = 'BTCMesh Client'
        Window.clearcolor = COLOR_BG
        return BTCMeshGUI()

    def on_stop(self):
        """Cleanup on app close."""
        if hasattr(self.root, 'iface') and self.root.iface:
            try:
                self.root.iface.close()
            except Exception:
                pass


def main():
    """Entry point for GUI."""
    BTCMeshApp().run()


if __name__ == '__main__':
    main()
