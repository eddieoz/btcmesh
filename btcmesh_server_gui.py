#!/usr/bin/env python3
"""
BTCMesh Server GUI - Kivy-based graphical interface for running and monitoring
the BTCMesh relay server.

This GUI wraps the btcmesh_server module, providing visual status displays,
activity logging, and server controls.
"""
import logging
import os
import shutil
import threading
import queue
import re
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.uix.spinner import Spinner
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.properties import BooleanProperty
from kivy.core.clipboard import Clipboard

# Import shared GUI components
from core.gui_common import (
    # Colors
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_ERROR,
    COLOR_WARNING,
    COLOR_BG,
    COLOR_BG_LIGHT,
    COLOR_DISCONNECTED,
    COLOR_MAINNET,
    COLOR_TESTNET,
    COLOR_SIGNET,
    COLOR_SECUNDARY,
    # Classes
    ConnectionState,
    StatusLog,
    # Functions
    get_log_color,
    create_separator,
    create_section_label,
    create_title,
    create_action_button,
    create_clear_button,
    create_status_row,
    create_input_row,
    create_toggle_button,
    create_refresh_button,
    create_popup_button,
    create_popup_inline_button,
)

# Import server module
import btcmesh_server
from core.logger_setup import server_logger
from core.config_loader import load_app_config
from core.transaction_history import TransactionHistory


# Set window size for desktop
Window.size = (550, 920)

# Meshtastic connection states (text only - description is in separate label)
STATE_MESHTASTIC_DISCONNECTED = ConnectionState('Not connected', COLOR_DISCONNECTED)
STATE_MESHTASTIC_CONNECTED = ConnectionState('Connected', COLOR_SUCCESS)
STATE_MESHTASTIC_FAILED = ConnectionState('Connection failed', COLOR_ERROR)

# Bitcoin RPC connection states (text only - description is in separate label)
STATE_RPC_DISCONNECTED = ConnectionState('Not connected', COLOR_DISCONNECTED)
STATE_RPC_CONNECTED = ConnectionState('Connected', COLOR_SUCCESS)
STATE_RPC_FAILED = ConnectionState('Connection failed', COLOR_ERROR)

# Device selection constants
DEVICE_AUTO_DETECT = "Auto-detect"
DEVICE_SCANNING = "Scanning..."
DEVICE_NO_DEVICES = "No devices found"

# Path to .env file (same as config_loader.py)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DOTENV_PATH = os.path.join(PROJECT_ROOT, ".env")


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


def parse_log_for_status(message: str, level: int = None):  # noqa: ARG001
    """Parse a log message and return status update if applicable.

    Returns:
        Tuple of (status_type, data) or None if no status update needed.
    """
    # Bitcoin RPC status
    if "Connected to Bitcoin Core RPC node successfully" in message:
        # Extract host from "Host: localhost:8332" or "Host: *.onion"
        host_match = re.search(r'Host: ([^,]+)', message)
        host = host_match.group(1).strip() if host_match else None
        # Extract Tor status from "Tor: True" or "Tor: False"
        tor_match = re.search(r'Tor: (True|False)', message)
        is_tor = tor_match.group(1) == 'True' if tor_match else False
        # Extract chain from "Chain: main" or "Chain: testnet4" etc.
        chain_match = re.search(r'Chain: (\w+)', message)
        chain = chain_match.group(1) if chain_match else None
        return ('rpc_connected', {'host': host, 'is_tor': is_tor, 'chain': chain})
    if "Failed to connect to Bitcoin Core RPC node" in message:
        # Extract error message after the colon
        match = re.search(r'Failed to connect to Bitcoin Core RPC node: (.+?)(?:\. |$)', message)
        error = match.group(1) if match else "Connection failed"
        return ('rpc_failed', error)

    # Meshtastic status
    if "Meshtastic interface initialized successfully" in message:
        # Extract device path from "Device: /dev/ttyUSB0"
        device_match = re.search(r'Device: ([^,]+)', message)
        device = device_match.group(1).strip() if device_match else None
        # Validate device - reject invalid values like "None", "?", empty strings
        if device in (None, '', '?', 'None'):
            device = None
        # Extract node ID from "My Node Num: !abcdef12"
        node_match = re.search(r'My Node Num: (!?[0-9a-fA-F]+)', message)
        node_id = node_match.group(1) if node_match else None
        # If we don't have a valid node_id, treat as failed connection
        if not node_id or not node_id.startswith('!'):
            return ('meshtastic_failed', "Invalid device info")
        return ('meshtastic_connected', {'node_id': node_id, 'device': device})
    if "Failed to initialize Meshtastic interface" in message:
        return ('meshtastic_failed', "Could not initialize Meshtastic")
    if "Meshtastic interface created but could not retrieve device info" in message:
        return ('meshtastic_failed', "No device connected")
    if "No Meshtastic device found" in message:
        return ('meshtastic_failed', "No device found")

    # Server running status
    if "Registered Meshtastic message handler. Waiting for messages" in message:
        return ('server_started', None)
    if "Stop signal received. Shutting down" in message:
        return ('server_stopping', None)
    if "Closing Meshtastic interface" in message:
        return ('server_stopped', None)

    # PubSub errors
    if "PubSub library not found" in message:
        return ('pubsub_error', "PubSub library not found")

    return None


class BTCMeshServerGUI(BoxLayout):
    """Main server GUI widget."""

    is_running = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 15
        self.spacing = 20

        # Server state
        self._stop_event = threading.Event()
        self._server_thread = None
        self._log_handler = None

        # Thread-safe result queue for communication
        self.result_queue = queue.Queue()

        # Set background color
        with self.canvas.before:
            Color(*COLOR_BG)
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)

        self._build_ui()

        # Start polling for results from background threads
        Clock.schedule_interval(self._process_results, 0.1)

    def _update_rect(self, *args):
        """Update background rectangle on resize."""
        self.rect.pos = self.pos
        self.rect.size = self.size

    def _build_ui(self):
        """Build the GUI layout."""
        # Title
        self.add_widget(create_title('BTCMesh Relay Server'))

        # Orange separator line after title
        self.add_widget(create_separator())

        # Connection status section
        self.add_widget(create_section_label('Connection Status:'))
        self._build_status_section()

        # Orange separator line after status section
        self.add_widget(create_separator())

        # Active Sessions section
        self.add_widget(create_section_label('Active Sessions:'))
        self._build_active_sessions_section()

        # Orange separator line after active sessions section
        self.add_widget(create_separator())

        # Bitcoin RPC Settings section
        self.add_widget(create_section_label('Bitcoin RPC Settings:'))
        self._build_rpc_settings()

        # Orange separator line after RPC settings section
        self.add_widget(create_separator())

        # Meshtastic Device Settings section
        self.add_widget(create_section_label('Meshtastic Settings:'))
        self._build_meshtastic_settings()

        # Orange separator line after Meshtastic settings
        self.add_widget(create_separator())

        # Reassembly timeout setting
        self.add_widget(create_section_label('Server Settings:'))
        self._build_timeout_settings()

        # Orange separator line after timeout settings
        self.add_widget(create_separator())

        # Server controls
        self._build_controls_section()

        # Activity log section
        self.add_widget(create_section_label('Activity Log:'))

        # Status log (scrollable)
        self.status_log = StatusLog(size_hint_y=1)
        self.add_widget(self.status_log)

        # Clear log button
        self.clear_btn = create_clear_button(self.on_clear_pressed)
        self.add_widget(self.clear_btn)

        # Initial log message
        self.status_log.add_message("Server GUI initialized. Click 'Start Server' to begin.", COLOR_PRIMARY)

    def _build_status_section(self):
        """Build the connection status section."""
        status_section = BoxLayout(orientation='vertical', size_hint_y=None, height=95, spacing=5)

        # Network badge row (mainnet/testnet/signet)
        network_row, self.network_label = create_status_row(
            'Network:',
            '--',
            initial_color=COLOR_DISCONNECTED,
            bold_value=True
        )
        status_section.add_widget(network_row)

        # Bitcoin RPC status row
        rpc_row, self.rpc_label = create_status_row(
            'Bitcoin RPC:',
            'Not connected',
            initial_color=COLOR_DISCONNECTED
        )
        status_section.add_widget(rpc_row)

        # Meshtastic status row
        meshtastic_row, self.meshtastic_label = create_status_row(
            'Meshtastic:',
            'Not connected',
            initial_color=COLOR_DISCONNECTED
        )
        status_section.add_widget(meshtastic_row)

        self.add_widget(status_section)

    def _build_active_sessions_section(self):
        """Build the active sessions display section with ScrollView.

        Displays up to 3 sessions without scrolling (~85px), scrolls for more.
        Session count is always visible outside the scroll area.
        """
        # Container with left padding for indentation (matches other sections)
        sessions_section = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=115,  # count label (25) + spacing (5) + scroll (85)
            padding=[10, 0, 0, 0],  # left indent
            spacing=5
        )

        # Session count label (always visible, outside ScrollView)
        self.session_count_label = Label(
            text='0 active sessions',
            size_hint_y=None,
            height=25,
            color=COLOR_DISCONNECTED,
            halign='left',
            valign='middle',
        )
        self.session_count_label.bind(size=lambda inst, val: setattr(inst, 'text_size', val))
        sessions_section.add_widget(self.session_count_label)

        # Fixed-height ScrollView to contain sessions
        # Height: 3 sessions * 25px + 2 * spacing(2) + padding = ~85px
        self.sessions_scroll = ScrollView(
            size_hint_y=None,
            height=85,
            do_scroll_x=False,
            bar_width=8,
            bar_color=COLOR_PRIMARY,
            bar_inactive_color=(0.5, 0.5, 0.3, 0.3),
        )

        # Inner container that grows with content
        self.sessions_container = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=2
        )
        # Bind height to minimum height needed for children
        self.sessions_container.bind(minimum_height=self.sessions_container.setter('height'))

        # Initial "no sessions" label (shown when count is 0)
        self.no_sessions_label = Label(
            text='No active sessions',
            size_hint_y=None,
            height=30,
            color=COLOR_DISCONNECTED,
            halign='left',
            valign='middle',
        )
        self.no_sessions_label.bind(size=lambda inst, val: setattr(inst, 'text_size', val))
        self.sessions_container.add_widget(self.no_sessions_label)

        # Dict to track session display widgets by session_id
        self._session_widgets = {}

        self.sessions_scroll.add_widget(self.sessions_container)
        sessions_section.add_widget(self.sessions_scroll)
        self.add_widget(sessions_section)

    def _update_active_sessions(self, sessions_info):
        """Update the active sessions display with new session info.

        Args:
            sessions_info: List of dicts with session_id, sender, chunks_received,
                        total_chunks, elapsed_seconds
        """
        # Update session count label (always visible)
        count = len(sessions_info) if sessions_info else 0
        self.session_count_label.text = f"{count} active session{'s' if count != 1 else ''}"
        self.session_count_label.color = COLOR_WARNING if count > 0 else COLOR_DISCONNECTED

        # Track which sessions are still active
        active_session_ids = set()

        if not sessions_info:
            # No active sessions
            if self._session_widgets:
                # Clear all session widgets
                for widget in self._session_widgets.values():
                    self.sessions_container.remove_widget(widget)
                self._session_widgets.clear()

            # Show "no sessions" label
            if self.no_sessions_label.parent is None:
                self.sessions_container.add_widget(self.no_sessions_label)
            return

        # Hide "no sessions" label
        if self.no_sessions_label.parent is not None:
            self.sessions_container.remove_widget(self.no_sessions_label)

        # Update or create widgets for each session
        for session in sessions_info:
            session_id = session['session_id']
            active_session_ids.add(session_id)

            # Format elapsed time
            elapsed = int(session['elapsed_seconds'])
            elapsed_str = f"{elapsed}s"

            # Format session display text
            session_text = (
                f"[{session_id}] from {session['sender']}: "
                f"{session['chunks_received']}/{session['total_chunks']} chunks, "
                f"{elapsed_str} ago"
            )

            if session_id in self._session_widgets:
                # Update existing widget
                self._session_widgets[session_id].text = session_text
            else:
                # Create new widget
                session_label = Label(
                    text=session_text,
                    size_hint_y=None,
                    height=25,
                    color=COLOR_WARNING,
                    halign='left',
                    valign='middle',
                )
                session_label.bind(size=lambda inst, val: setattr(inst, 'text_size', val))
                self._session_widgets[session_id] = session_label
                self.sessions_container.add_widget(session_label)

        # Remove widgets for sessions that are no longer active
        sessions_to_remove = set(self._session_widgets.keys()) - active_session_ids
        for session_id in sessions_to_remove:
            widget = self._session_widgets.pop(session_id)
            self.sessions_container.remove_widget(widget)

    def _build_rpc_settings(self):
        """Build the Bitcoin RPC settings input section."""
        import os

        # Load defaults from environment
        load_app_config()
        default_host = os.getenv("BITCOIN_RPC_HOST", "127.0.0.1")
        default_port = os.getenv("BITCOIN_RPC_PORT", "8332")
        default_user = os.getenv("BITCOIN_RPC_USER", "")
        default_password = os.getenv("BITCOIN_RPC_PASSWORD", "")

        settings_container = BoxLayout(orientation='vertical', size_hint_y=None, height=225, spacing=5)

        # Row 1: Host input with Show/Hide toggle
        host_row, self.rpc_host_input = create_input_row(
            'Host:', default_host, hint_text='127.0.0.1 or xyz.onion', password=True
        )
        # Show/Hide host toggle button
        self.show_host_btn = create_toggle_button('Show')
        self.show_host_btn.bind(on_press=self._toggle_host_visibility)
        host_row.add_widget(self.show_host_btn)
        settings_container.add_widget(host_row)

        # Row 2: Port input
        port_row, self.rpc_port_input = create_input_row(
            'Port:', default_port, hint_text='8332', input_filter='int'
        )
        # Spacer to align with host row (Show button = 60px)
        port_row.add_widget(Widget(size_hint_x=None, width=60))
        settings_container.add_widget(port_row)

        # Row 3: User input
        user_row, self.rpc_user_input = create_input_row(
            'User:', default_user, hint_text='rpcuser'
        )
        # Spacer to align with host row
        user_row.add_widget(Widget(size_hint_x=None, width=60))
        settings_container.add_widget(user_row)

        # Row 4: Password input with Show/Hide toggle
        pass_row, self.rpc_password_input = create_input_row(
            'Password:', default_password, hint_text='password', password=True
        )
        # Show/Hide password toggle button
        self.show_password_btn = create_toggle_button('Show')
        self.show_password_btn.bind(on_press=self._toggle_password_visibility)
        pass_row.add_widget(self.show_password_btn)
        settings_container.add_widget(pass_row)

        # add spacer
        settings_container.add_widget(Widget(size_hint_y=None, height=5))

        # Row 5: Test Connection button
        test_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=5)
        # Left spacer to center button
        test_row.add_widget(Widget(size_hint_x=0.3))

        self.test_connection_btn = Button(
            text='Test Connection',
            size_hint_x=0.4,
            background_color=COLOR_BG_LIGHT,
            background_normal='',
        )
        self.test_connection_btn.bind(on_press=self._on_test_connection)
        test_row.add_widget(self.test_connection_btn)

        # Right spacer
        test_row.add_widget(Widget(size_hint_x=0.3))

        settings_container.add_widget(test_row)

        self.add_widget(settings_container)

    def _build_meshtastic_settings(self):
        """Build the Meshtastic device settings section."""
        import os

        # Load default from environment
        load_app_config()
        default_device = os.getenv("MESHTASTIC_SERIAL_PORT", "")

        settings_container = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=5)

        # Device label
        device_label = Label(
            text='Device:',
            size_hint_x=None,
            halign='right',
            valign='middle',
            color=COLOR_SECUNDARY,
        )
        device_label.bind(texture_size=lambda inst, val: setattr(inst, 'width', val[0] + 15))
        settings_container.add_widget(device_label)

        # Device dropdown/spinner
        self.device_spinner = Spinner(
            text=default_device if default_device else DEVICE_AUTO_DETECT,
            values=[DEVICE_AUTO_DETECT],
            size_hint_x=0.75,
            background_color=COLOR_BG_LIGHT,
            background_normal='',
            color=COLOR_SECUNDARY,
        )
        settings_container.add_widget(self.device_spinner)

        # Scan button
        self.scan_btn = create_refresh_button('Scan')
        self.scan_btn.bind(on_press=self._on_scan_devices)
        settings_container.add_widget(self.scan_btn)

        self.add_widget(settings_container)

    def _build_timeout_settings(self):
        """Build the reassembly timeout settings section."""
        import os

        # Load default from environment, fallback to 300 seconds
        load_app_config()
        env_timeout = os.getenv("REASSEMBLY_TIMEOUT_SECONDS", "")
        default_timeout = env_timeout if env_timeout else "300"

        # Use create_input_row for consistent styling
        timeout_row, self.timeout_input = create_input_row(
            'Reassembly Timeout:',
            default_timeout,
            hint_text='seconds',
            input_filter='int',
            input_size_hint_x=0.3,
        )
        # Add a spacer to balance the row
        timeout_row.add_widget(Widget(size_hint_x=0.4))
        self.add_widget(timeout_row)

    def _set_timeout_settings_enabled(self, enabled: bool):
        """Enable or disable timeout settings."""
        self.timeout_input.disabled = not enabled

    def _build_controls_section(self):
        """Build the server control buttons section."""
        controls_section = BoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10)

        self.start_btn = create_action_button('Start Server')
        self.start_btn.bind(on_press=self.on_start_pressed)
        controls_section.add_widget(self.start_btn)

        self.stop_btn = create_action_button('Stop Server', color=COLOR_ERROR, disabled=True)
        self.stop_btn.bind(on_press=self.on_stop_pressed)
        controls_section.add_widget(self.stop_btn)

        self.save_btn = create_action_button('Save Settings', color=COLOR_BG_LIGHT)
        self.save_btn.bind(on_press=self._on_save_settings)
        controls_section.add_widget(self.save_btn)

        self.history_btn = create_action_button('History', color=COLOR_BG_LIGHT)
        self.history_btn.bind(on_press=self._on_history_pressed)
        controls_section.add_widget(self.history_btn)

        self.add_widget(controls_section)

    def _on_scan_devices(self, instance):
        """Scan for available Meshtastic devices."""
        self.device_spinner.text = DEVICE_SCANNING
        self.scan_btn.disabled = True

        def scan_thread():
            from core.meshtastic_utils import scan_meshtastic_devices
            devices = scan_meshtastic_devices()
            self.result_queue.put(('devices_found', devices))

        threading.Thread(target=scan_thread, daemon=True).start()

    def _set_meshtastic_settings_enabled(self, enabled: bool):
        """Enable or disable Meshtastic device settings."""
        self.device_spinner.disabled = not enabled
        self.scan_btn.disabled = not enabled

    def _set_rpc_settings_enabled(self, enabled: bool):
        """Enable or disable all RPC settings inputs."""
        self.rpc_host_input.disabled = not enabled
        self.rpc_port_input.disabled = not enabled
        self.rpc_user_input.disabled = not enabled
        self.rpc_password_input.disabled = not enabled
        self.test_connection_btn.disabled = not enabled

    def _toggle_host_visibility(self, instance):
        """Toggle host field visibility."""
        self.rpc_host_input.password = not self.rpc_host_input.password
        self.show_host_btn.text = 'Hide' if not self.rpc_host_input.password else 'Show'

    def _toggle_password_visibility(self, instance):
        """Toggle password field visibility."""
        self.rpc_password_input.password = not self.rpc_password_input.password
        self.show_password_btn.text = 'Hide' if not self.rpc_password_input.password else 'Show'

    def _on_test_connection(self, instance):
        """Test the RPC connection with current settings."""
        host = self.rpc_host_input.text.strip()
        port = self.rpc_port_input.text.strip()
        user = self.rpc_user_input.text.strip()
        password = self.rpc_password_input.text

        # Basic validation
        if not host:
            self.status_log.add_message("Test failed: Host is required", COLOR_ERROR)
            return
        if not port:
            self.status_log.add_message("Test failed: Port is required", COLOR_ERROR)
            return
        if not user:
            self.status_log.add_message("Test failed: User is required", COLOR_ERROR)
            return
        if not password:
            self.status_log.add_message("Test failed: Password is required", COLOR_ERROR)
            return

        self.status_log.add_message("Testing RPC connection...", COLOR_WARNING)
        self.test_connection_btn.disabled = True
        self.start_btn.disabled = True

        def test_thread():
            try:
                # Check for Tor requirement
                is_tor = host.endswith('.onion')
                if is_tor:
                    # Validate Tor is available on port 9050
                    import socket
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(5)
                        result = sock.connect_ex(('127.0.0.1', 9050))
                        sock.close()
                        if result != 0:
                            self.result_queue.put(('test_connection_result', False,
                                                'Tor service not reachable on port 9050'))
                            return
                    except Exception as e:
                        self.result_queue.put(('test_connection_result', False,
                                            f'Failed to check Tor: {e}'))
                        return

                # Test RPC connection
                from core.rpc_client import BitcoinRPCClient
                config = {
                    'host': host,
                    'port': int(port),
                    'user': user,
                    'password': password,
                }
                client = BitcoinRPCClient(config)
                chain = client.chain
                tor_suffix = ' via Tor' if is_tor else ''
                self.result_queue.put(('test_connection_result', True,
                                    f'Connected to {chain} network{tor_suffix}'))
            except Exception as e:
                self.result_queue.put(('test_connection_result', False, str(e)))

        threading.Thread(target=test_thread, daemon=True).start()

    def _on_save_settings(self, instance):
        """Save current settings to .env file.

        Preserves existing comments and unrelated variables.
        Creates a backup (.env.bak) before overwriting.
        """
        # Collect current settings from GUI
        settings = {
            'BITCOIN_RPC_HOST': self.rpc_host_input.text.strip(),
            'BITCOIN_RPC_PORT': self.rpc_port_input.text.strip(),
            'BITCOIN_RPC_USER': self.rpc_user_input.text.strip(),
            'BITCOIN_RPC_PASSWORD': self.rpc_password_input.text,  # Don't strip password
            'REASSEMBLY_TIMEOUT_SECONDS': self.timeout_input.text.strip(),
        }

        # Handle Meshtastic device - only save if not Auto-detect
        selected_device = self.device_spinner.text
        if selected_device and selected_device not in (DEVICE_AUTO_DETECT, DEVICE_SCANNING, DEVICE_NO_DEVICES):
            settings['MESHTASTIC_SERIAL_PORT'] = selected_device
        else:
            # Mark for removal if currently set
            settings['MESHTASTIC_SERIAL_PORT'] = None

        try:
            # Read existing .env content (preserving structure)
            existing_lines = []
            existing_keys = set()
            if os.path.exists(DOTENV_PATH):
                # Create backup before modifying
                backup_path = DOTENV_PATH + '.bak'
                shutil.copy2(DOTENV_PATH, backup_path)

                with open(DOTENV_PATH, 'r') as f:
                    for line in f:
                        stripped = line.strip()
                        # Check if this line sets a variable we want to update
                        if stripped and not stripped.startswith('#') and '=' in stripped:
                            key = stripped.split('=', 1)[0].strip()
                            if key in settings:
                                existing_keys.add(key)
                                value = settings[key]
                                if value is None:
                                    # Skip this line (remove the setting)
                                    continue
                                # Replace the value, preserving the key format
                                existing_lines.append(f'{key}={value}\n')
                                continue
                        # Keep the line as-is (comments, empty lines, other vars)
                        existing_lines.append(line)

            # Add any new settings that weren't in the file
            for key, value in settings.items():
                if key not in existing_keys and value is not None:
                    existing_lines.append(f'{key}={value}\n')

            # Write updated content
            with open(DOTENV_PATH, 'w') as f:
                f.writelines(existing_lines)

            self.status_log.add_message(
                f"Settings saved to {DOTENV_PATH}", COLOR_SUCCESS)

            # Security note for password
            if settings.get('BITCOIN_RPC_PASSWORD'):
                self.status_log.add_message(
                    "Note: Password is stored in plain text in .env file", COLOR_WARNING)

        except PermissionError:
            self.status_log.add_message(
                f"Permission denied: Cannot write to {DOTENV_PATH}", COLOR_ERROR)
        except Exception as e:
            self.status_log.add_message(
                f"Failed to save settings: {e}", COLOR_ERROR)

    def on_start_pressed(self, instance):
        """Handle Start Server button press."""
        # Validate required fields before starting
        host = self.rpc_host_input.text.strip()
        port = self.rpc_port_input.text.strip()
        user = self.rpc_user_input.text.strip()
        password = self.rpc_password_input.text

        if not host or not port or not user or not password:
            self.status_log.add_message(
                "Cannot start: Please fill in all RPC settings fields", COLOR_ERROR)
            return

        # Validate timeout (must be positive integer)
        timeout_text = self.timeout_input.text.strip()
        if not timeout_text:
            self.status_log.add_message(
                "Cannot start: Reassembly timeout is required", COLOR_ERROR)
            return
        try:
            reassembly_timeout = int(timeout_text)
            if reassembly_timeout <= 0:
                raise ValueError()
        except ValueError:
            self.status_log.add_message(
                "Cannot start: Reassembly timeout must be a positive integer", COLOR_ERROR)
            return

        self.status_log.add_message("Starting server...", COLOR_WARNING)
        self.start_btn.disabled = True
        self.save_btn.disabled = True
        self._set_rpc_settings_enabled(False)
        self._set_meshtastic_settings_enabled(False)
        self._set_timeout_settings_enabled(False)

        # Build RPC config from GUI inputs
        rpc_config = {
            'host': host,
            'port': int(port),
            'user': user,
            'password': password,
        }

        # Get selected device (None for auto-detect)
        selected_device = self.device_spinner.text
        serial_port = None if selected_device == DEVICE_AUTO_DETECT else selected_device

        # Reset stop event
        self._stop_event.clear()

        # Set up log handler to capture server logs with timestamps
        self._log_handler = QueueLogHandler(self.result_queue)
        self._log_handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', datefmt='%H:%M:%S'))
        server_logger.addHandler(self._log_handler)

        # Session update callback - puts session info in result queue
        def session_callback(sessions_info):
            self.result_queue.put(('active_sessions', sessions_info))

        # Start server in background thread
        def run_server():
            try:
                btcmesh_server.main(stop_event=self._stop_event, rpc_config=rpc_config,
                                    serial_port=serial_port, reassembly_timeout=reassembly_timeout,
                                    session_update_callback=session_callback)
            except Exception as e:
                self.result_queue.put(('init_error', str(e), logging.ERROR))
            finally:
                # Signal that server has stopped (in case main() exits without stop signal)
                if not self._stop_event.is_set():
                    self.result_queue.put(('server_stopped', None, logging.INFO))

        self._server_thread = threading.Thread(target=run_server, daemon=True)
        self._server_thread.start()

    def on_stop_pressed(self, instance):
        """Handle Stop Server button press."""
        self.status_log.add_message("Stopping server...", COLOR_WARNING)
        self.stop_btn.disabled = True

        # Signal server to stop
        self._stop_event.set()

    def _process_results(self, dt):
        """Process results from background threads (called by Clock)."""
        try:
            while True:
                result = self.result_queue.get_nowait()
                self._handle_result(result)
        except queue.Empty:
            pass

    def _handle_result(self, result):
        """Handle a single result from the queue."""
        result_type = result[0]
        data = result[1] if len(result) > 1 else None
        level = result[2] if len(result) > 2 else logging.INFO

        if result_type == 'log':
            # Parse log message for status updates
            status_update = parse_log_for_status(data, level)
            if status_update:
                self._apply_status_update(status_update)

            # Display log message with appropriate color
            color = get_log_color(level, data)
            self.status_log.add_message(data, color)

        elif result_type in ('rpc_connected', 'rpc_failed', 'meshtastic_connected',
                            'meshtastic_failed', 'server_started', 'server_stopped',
                            'server_stopping', 'pubsub_error', 'init_error'):
            self._apply_status_update((result_type, data))

        elif result_type == 'test_connection_result':
            # data is success (bool), level is message string
            success = data
            message = level  # Third element contains the message
            self.test_connection_btn.disabled = False
            self.start_btn.disabled = False
            if success:
                self.status_log.add_message(f"RPC test successful: {message}", COLOR_SUCCESS)
            else:
                self.status_log.add_message(f"RPC test failed: {message}", COLOR_ERROR)

        elif result_type == 'devices_found':
            devices = data
            self.scan_btn.disabled = False
            if devices:
                # Add Auto-detect as first option, then found devices
                self.device_spinner.values = [DEVICE_AUTO_DETECT] + devices
                if len(devices) == 1:
                    # Auto-select single device
                    self.device_spinner.text = devices[0]
                    self.status_log.add_message(f"Found device: {devices[0]}", COLOR_SUCCESS)
                else:
                    # Multiple devices - keep current selection or show first
                    if self.device_spinner.text == DEVICE_SCANNING:
                        self.device_spinner.text = DEVICE_AUTO_DETECT
                    self.status_log.add_message(
                        f"Found {len(devices)} devices", COLOR_SUCCESS)
            else:
                self.device_spinner.values = [DEVICE_AUTO_DETECT]
                self.device_spinner.text = DEVICE_AUTO_DETECT
                self.status_log.add_message("No Meshtastic devices found", COLOR_WARNING)

        elif result_type == 'active_sessions':
            # Update the active sessions display
            self._update_active_sessions(data)

    def _apply_status_update(self, status_update):
        """Apply a status update to the GUI."""
        status_type, data = status_update

        if status_type == 'rpc_connected':
            # data is dict with 'host', 'is_tor', and 'chain' keys
            host = data.get('host') if isinstance(data, dict) else None
            is_tor = data.get('is_tor', False) if isinstance(data, dict) else False
            chain = data.get('chain') if isinstance(data, dict) else None
            if host:
                tor_badge = " [Tor]" if is_tor else ""
                self.rpc_label.text = f"Connected ({host}){tor_badge}"
            else:
                self.rpc_label.text = STATE_RPC_CONNECTED.text
            self.rpc_label.color = STATE_RPC_CONNECTED.color

            # Update network badge based on chain
            if chain:
                # Map chain values to display names and colors
                chain_display_map = {
                    'main': ('MAINNET', COLOR_MAINNET),
                    'test': ('TESTNET3', COLOR_TESTNET),
                    'testnet4': ('TESTNET4', COLOR_TESTNET),
                    'signet': ('SIGNET', COLOR_SIGNET),
                }
                display_name, color = chain_display_map.get(chain, (chain.upper(), COLOR_TESTNET))
                self.network_label.text = display_name
                self.network_label.color = color

        elif status_type == 'rpc_failed':
            self.rpc_label.text = STATE_RPC_FAILED.text
            self.rpc_label.color = STATE_RPC_FAILED.color

        elif status_type == 'meshtastic_connected':
            # data is dict with 'node_id' and 'device' keys
            node_id = data.get('node_id', 'Unknown') if isinstance(data, dict) else data
            device = data.get('device') if isinstance(data, dict) else None
            if device:
                self.meshtastic_label.text = f"Connected ({node_id}) on {device}"
            else:
                self.meshtastic_label.text = f"Connected ({node_id})"
            self.meshtastic_label.color = STATE_MESHTASTIC_CONNECTED.color

        elif status_type == 'meshtastic_failed':
            self.meshtastic_label.text = STATE_MESHTASTIC_FAILED.text
            self.meshtastic_label.color = STATE_MESHTASTIC_FAILED.color
            # Re-enable start button and settings on failure
            self.start_btn.disabled = False
            self.save_btn.disabled = False
            self._set_rpc_settings_enabled(True)
            self._set_meshtastic_settings_enabled(True)
            self._set_timeout_settings_enabled(True)
            self._cleanup_log_handler()

        elif status_type == 'pubsub_error':
            self.start_btn.disabled = False
            self.save_btn.disabled = False
            self._set_rpc_settings_enabled(True)
            self._set_meshtastic_settings_enabled(True)
            self._set_timeout_settings_enabled(True)
            self._cleanup_log_handler()

        elif status_type == 'server_started':
            self.is_running = True
            self.stop_btn.disabled = False

        elif status_type == 'server_stopping':
            # Server is in the process of stopping
            pass

        elif status_type == 'server_stopped':
            self.is_running = False
            self.meshtastic_label.text = STATE_MESHTASTIC_DISCONNECTED.text
            self.meshtastic_label.color = STATE_MESHTASTIC_DISCONNECTED.color
            self.rpc_label.text = STATE_RPC_DISCONNECTED.text
            self.rpc_label.color = STATE_RPC_DISCONNECTED.color
            self.network_label.text = '--'
            self.network_label.color = COLOR_DISCONNECTED
            # Clear active sessions display
            self._update_active_sessions([])
            # Note: stop_btn is set first because in tests, mocked buttons may be same object
            self.stop_btn.disabled = True
            self.start_btn.disabled = False
            self.save_btn.disabled = False
            self._set_rpc_settings_enabled(True)
            self._set_meshtastic_settings_enabled(True)
            self._set_timeout_settings_enabled(True)
            self._cleanup_log_handler()

        elif status_type == 'init_error':
            self.status_log.add_message(f"Initialization error: {data}", COLOR_ERROR)
            self.start_btn.disabled = False
            self.save_btn.disabled = False
            self._set_rpc_settings_enabled(True)
            self._set_meshtastic_settings_enabled(True)
            self._set_timeout_settings_enabled(True)
            self._cleanup_log_handler()

    def _cleanup_log_handler(self):
        """Remove log handler from server logger."""
        if self._log_handler:
            server_logger.removeHandler(self._log_handler)
            self._log_handler = None

    def _on_history_pressed(self, instance):
        """Handle History button press - show transaction history popup."""
        self._show_history_popup()

    def _show_history_popup(self):
        """Build and show the transaction history popup."""
        # Load transaction history
        history = TransactionHistory()
        entries = history.get_all()

        # Build popup content
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)

        # Header with count
        count = len(entries)
        header = Label(
            text=f"Transaction History ({count} entries)",
            size_hint_y=None,
            height=30,
            color=COLOR_PRIMARY,
            bold=True
        )
        content.add_widget(header)

        # Scrollable list of transactions
        scroll = ScrollView(size_hint_y=1)
        entries_container = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=5,
            padding=[0, 5, 0, 5]
        )
        entries_container.bind(minimum_height=entries_container.setter('height'))

        if entries:
            for entry in entries:
                entry_widget = self._create_history_entry_widget(entry)
                entries_container.add_widget(entry_widget)
        else:
            no_entries = Label(
                text="No transactions yet",
                size_hint_y=None,
                height=40,
                color=COLOR_DISCONNECTED
            )
            entries_container.add_widget(no_entries)

        scroll.add_widget(entries_container)
        content.add_widget(scroll)

        # Close button
        close_btn = create_popup_button('Close', primary=True)
        content.add_widget(close_btn)

        # Create and show popup
        popup = Popup(
            title='Transaction History',
            content=content,
            size_hint=(0.95, 0.8),
            background_color=COLOR_BG,
            title_color=COLOR_PRIMARY,
            separator_color=COLOR_PRIMARY
        )
        close_btn.bind(on_press=popup.dismiss)
        popup.open()

    def _create_history_entry_widget(self, entry):
        """Create a clickable widget to display a single history entry."""
        # Container for the entry - using Button base for touch handling
        container = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=90,
            spacing=5,
            padding=[5, 5, 5, 5]
        )

        # Store entry data for click handler
        container._entry_data = entry

        # Add background color based on status
        with container.canvas.before:
            if entry.get('status') == 'success':
                Color(0.1, 0.3, 0.1, 1)  # Dark green
            else:
                Color(0.3, 0.1, 0.1, 1)  # Dark red
            container._bg_rect = Rectangle(pos=container.pos, size=container.size)
        container.bind(pos=self._update_rect, size=self._update_rect)

        # Make container clickable
        container.bind(on_touch_down=self._on_history_entry_touch)

        # First row: timestamp and status
        row1 = BoxLayout(orientation='horizontal', size_hint_y=None, height=25)

        # Parse timestamp for display
        timestamp = entry.get('timestamp', '')
        if timestamp:
            try:
                # Format: 2025-12-26T14:30:00 -> Dec 26 14:30
                from datetime import datetime
                dt = datetime.fromisoformat(timestamp)
                timestamp_display = dt.strftime('%b %d %H:%M')
            except (ValueError, TypeError):
                timestamp_display = timestamp[:16]
        else:
            timestamp_display = 'Unknown'

        status = entry.get('status', 'unknown')
        status_color = COLOR_SUCCESS if status == 'success' else COLOR_ERROR

        time_label = Label(
            text=timestamp_display,
            size_hint_x=0.4,
            halign='left',
            valign='middle',
            color=COLOR_SECUNDARY
        )
        time_label.bind(size=lambda inst, val: setattr(inst, 'text_size', val))

        status_label = Label(
            text=status.upper(),
            size_hint_x=0.6,
            halign='right',
            valign='middle',
            color=status_color,
            bold=True
        )
        status_label.bind(size=lambda inst, val: setattr(inst, 'text_size', val))

        row1.add_widget(time_label)
        row1.add_widget(status_label)
        container.add_widget(row1)

        # Second row: sender and session
        row2 = BoxLayout(orientation='horizontal', size_hint_y=None, height=20)

        sender = entry.get('sender', 'Unknown')
        session_id = entry.get('session_id', '')

        sender_label = Label(
            text=f"From: {sender}",
            size_hint_x=0.5,
            halign='left',
            valign='middle',
            color=COLOR_SECUNDARY,
            font_size='12sp'
        )
        sender_label.bind(size=lambda inst, val: setattr(inst, 'text_size', val))

        session_label = Label(
            text=f"Session: {session_id}",
            size_hint_x=0.5,
            halign='right',
            valign='middle',
            color=COLOR_SECUNDARY,
            font_size='12sp'
        )
        session_label.bind(size=lambda inst, val: setattr(inst, 'text_size', val))

        row2.add_widget(sender_label)
        row2.add_widget(session_label)
        container.add_widget(row2)

        # Third row: TXID or error
        row3 = BoxLayout(orientation='horizontal', size_hint_y=None, height=20)

        if status == 'success':
            txid = entry.get('txid', '')
            # Truncate TXID for display
            txid_display = f"{txid[:16]}...{txid[-8:]}" if len(txid) > 24 else txid
            result_label = Label(
                text=f"TXID: {txid_display}",
                size_hint_x=1,
                halign='left',
                valign='middle',
                color=COLOR_SUCCESS,
                font_size='11sp'
            )
        else:
            error = entry.get('error', 'Unknown error')
            # Truncate error for display
            error_display = error[:50] + '...' if len(error) > 50 else error
            result_label = Label(
                text=f"Error: {error_display}",
                size_hint_x=1,
                halign='left',
                valign='middle',
                color=COLOR_ERROR,
                font_size='11sp'
            )
        result_label.bind(size=lambda inst, val: setattr(inst, 'text_size', val))

        row3.add_widget(result_label)
        container.add_widget(row3)

        return container

    def _update_rect(self, instance, value):
        """Update rectangle position/size for background."""
        if hasattr(instance, '_bg_rect'):
            instance._bg_rect.pos = instance.pos
            instance._bg_rect.size = instance.size

    def _on_history_entry_touch(self, instance, touch):
        """Handle touch on a history entry widget."""
        if instance.collide_point(*touch.pos):
            if hasattr(instance, '_entry_data'):
                self._show_transaction_detail(instance._entry_data)
                return True
        return False

    def _show_transaction_detail(self, entry):
        """Show detailed view of a transaction history entry."""
        from datetime import datetime

        # Build popup content
        content = BoxLayout(orientation='vertical', spacing=5, padding=10)

        # Status header with color
        status = entry.get('status', 'unknown')
        status_color = COLOR_SUCCESS if status == 'success' else COLOR_ERROR
        header = Label(
            text=f"Transaction {status.upper()}",
            size_hint_y=None,
            height=40,
            color=status_color,
            bold=True,
            font_size='18sp'
        )
        content.add_widget(header)

        # Timestamp
        timestamp = entry.get('timestamp', '')
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp)
                timestamp_display = dt.strftime('%B %d, %Y at %H:%M:%S')
            except (ValueError, TypeError):
                timestamp_display = timestamp
        else:
            timestamp_display = 'Unknown'

        time_row, _ = create_status_row('Time:', timestamp_display, COLOR_SECUNDARY)
        content.add_widget(time_row)

        # Sender
        sender = entry.get('sender', 'Unknown')
        sender_row, _ = create_status_row('Sender:', sender, COLOR_SECUNDARY)
        content.add_widget(sender_row)

        # Session ID
        session_id = entry.get('session_id', '')
        session_row, _ = create_status_row('Session:', session_id, COLOR_SECUNDARY)
        content.add_widget(session_row)

        # TXID (for success) with copy button
        if status == 'success':
            txid = entry.get('txid', '')
            txid_display = f"{txid[:24]}...{txid[-8:]}" if len(txid) > 32 else txid
            txid_row, _ = create_status_row('TXID:', txid_display, COLOR_SUCCESS, height=35)

            copy_txid_btn = create_popup_inline_button('Copy TXID')
            copy_txid_btn.bind(on_press=lambda x: self._copy_to_clipboard(txid, "TXID"))
            txid_row.add_widget(copy_txid_btn)
            content.add_widget(txid_row)

        # Error (for failure)
        if status == 'failed':
            error = entry.get('error', 'Unknown error')
            error_row, error_label = create_status_row('Error:', error, COLOR_ERROR, height=35)
            content.add_widget(error_row)

        # Raw TX section
        raw_tx = entry.get('raw_tx')
        if raw_tx:
            raw_tx_row, _ = create_status_row('Raw TX:', '', COLOR_SECUNDARY)
            content.add_widget(raw_tx_row)

            # Scrollable raw TX display - fills remaining space
            raw_tx_scroll = ScrollView(size_hint_y=1)
            raw_tx_label = Label(
                text=raw_tx,
                size_hint_y=None,
                color=COLOR_PRIMARY,
                halign='left',
                valign='top',
                font_size='11sp'
            )
            raw_tx_label.bind(texture_size=lambda inst, val: setattr(inst, 'height', val[1]))
            raw_tx_label.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0], None)))
            raw_tx_scroll.add_widget(raw_tx_label)
            content.add_widget(raw_tx_scroll)

            # Copy Raw TX button
            copy_raw_btn = create_popup_button('Copy Raw TX', primary=False)
            copy_raw_btn.bind(on_press=lambda x: self._copy_to_clipboard(raw_tx, "Raw TX"))
            content.add_widget(copy_raw_btn)

            # Spacer between buttons
            content.add_widget(Widget(size_hint_y=None, height=10))
        else:
            # No raw TX - add spacer to push close button to bottom
            no_raw_row, _ = create_status_row('Raw TX:', 'Not available (timeout or incomplete)',
                                            COLOR_DISCONNECTED)
            no_raw_row.size_hint_y = 1  # Fill remaining space
            content.add_widget(no_raw_row)

        # Close button
        close_btn = create_popup_button('Close', primary=True)
        content.add_widget(close_btn)

        # Create and show popup
        popup = Popup(
            title='Transaction Details',
            content=content,
            size_hint=(0.95, 0.85),
            background_color=COLOR_BG,
            title_color=COLOR_PRIMARY,
            separator_color=COLOR_PRIMARY
        )
        close_btn.bind(on_press=popup.dismiss)
        popup.open()

    def _copy_to_clipboard(self, text, label):
        """Copy text to clipboard and show confirmation."""
        Clipboard.copy(text)
        self.status_log.add_message(f"{label} copied to clipboard", COLOR_SUCCESS)

    def on_clear_pressed(self, instance):
        """Handle Clear Log button press."""
        self.status_log.clear()
        self.status_log.add_message("Log cleared", COLOR_PRIMARY)


class BTCMeshServerApp(App):
    """Main Kivy application for the server GUI."""

    def build(self):
        self.title = 'BTCMesh Relay Server'
        Window.clearcolor = COLOR_BG
        return BTCMeshServerGUI()


def main():
    """Entry point for the server GUI."""
    BTCMeshServerApp().run()


if __name__ == '__main__':
    main()
