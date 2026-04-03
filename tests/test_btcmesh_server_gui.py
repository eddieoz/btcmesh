#!/usr/bin/env python3
"""
Tests for BTCMesh Server GUI (btcmesh_server_gui.py).

Story 15.1: Create Server GUI Application Structure
"""
import sys
import unittest
import unittest.mock

# Mock Kivy modules before importing btcmesh_server_gui
# This is necessary because Python loads the entire module (including Kivy imports)
# before extracting the specific functions we want to test.
# These mocks allow tests to run in environments without Kivy installed.


# Create proper base classes for Kivy widgets to allow class inheritance
class MockCanvas:
    """Mock canvas for Kivy widgets - acts as context manager."""
    def __init__(self):
        self.before = self  # self-referential for canvas.before

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class MockBoxLayout:
    """Mock base class for BoxLayout to allow proper class inheritance."""
    def __init__(self, **kwargs):
        self.canvas = MockCanvas()
        self.size = (100, 100)
        self.pos = (0, 0)
        self.width = 100
        self.height = kwargs.get('height', 100)
        self.children = []

    def add_widget(self, widget):
        widget.parent = self
        self.children.append(widget)

    def remove_widget(self, widget):
        widget.parent = None
        if widget in self.children:
            self.children.remove(widget)

    def bind(self, **kwargs):
        pass

    def setter(self, prop):
        """Mock setter method for property binding."""
        return lambda *args: None


class MockScrollView:
    """Mock base class for ScrollView."""
    def __init__(self, **kwargs):
        self.size = (100, 100)
        self.pos = (0, 0)
        self.width = 100
        self.height = kwargs.get('height', 100)
        self.children = []

    def add_widget(self, widget):
        widget.parent = self
        self.children.append(widget)

    def bind(self, **kwargs):
        pass

    def setter(self, prop):
        """Mock setter method for property binding."""
        return lambda *args: None


class MockWidget:
    """Mock base class for Widget."""
    def __init__(self, **kwargs):
        self.size = (100, 100)
        self.pos = (0, 0)
        self.width = kwargs.get('width', 100)
        self.height = kwargs.get('height', 100)
        self.size_hint_x = kwargs.get('size_hint_x', 1)
        self.size_hint_y = kwargs.get('size_hint_y', 1)
        self.canvas = MockCanvas()

    def bind(self, **kwargs):
        pass


class MockApp:
    """Mock base class for App."""
    def __init__(self, **kwargs):
        pass

    def run(self):
        pass


class MockTextInput:
    """Mock base class for TextInput that properly stores password attribute."""
    def __init__(self, **kwargs):
        self.text = kwargs.get('text', '')
        self.hint_text = kwargs.get('hint_text', '')
        self.password = kwargs.get('password', False)
        self.disabled = kwargs.get('disabled', False)
        self.multiline = kwargs.get('multiline', True)
        self.size_hint_x = kwargs.get('size_hint_x', 1)
        self.background_color = kwargs.get('background_color', (1, 1, 1, 1))
        self.foreground_color = kwargs.get('foreground_color', (0, 0, 0, 1))
        self.cursor_color = kwargs.get('cursor_color', (0, 0, 0, 1))
        self.input_filter = kwargs.get('input_filter', None)

    def bind(self, **kwargs):
        pass


class MockSpinner:
    """Mock base class for Spinner that properly stores text and values."""
    def __init__(self, **kwargs):
        self.text = kwargs.get('text', '')
        self.values = kwargs.get('values', [])
        self.disabled = kwargs.get('disabled', False)
        self.size_hint_x = kwargs.get('size_hint_x', 1)
        self.background_color = kwargs.get('background_color', (1, 1, 1, 1))
        self.background_normal = kwargs.get('background_normal', '')
        self.color = kwargs.get('color', (0, 0, 0, 1))

    def bind(self, **kwargs):
        pass


class MockLabel:
    """Mock base class for Label that properly stores text and parent."""
    def __init__(self, **kwargs):
        self.text = kwargs.get('text', '')
        self.color = kwargs.get('color', (1, 1, 1, 1))
        self.size_hint_y = kwargs.get('size_hint_y', 1)
        self.size_hint_x = kwargs.get('size_hint_x', 1)
        self.height = kwargs.get('height', 20)
        self.width = kwargs.get('width', 100)
        self.halign = kwargs.get('halign', 'left')
        self.valign = kwargs.get('valign', 'middle')
        self.parent = None
        self.texture_size = (100, 20)
        self.text_size = (None, None)
        self.size = (100, 20)
        self.bold = kwargs.get('bold', False)

    def bind(self, **kwargs):
        pass

    def setter(self, prop):
        """Mock setter method for property binding."""
        return lambda *args: None


kivy_mock = unittest.mock.MagicMock()
# get_color_from_hex should return a tuple like (r, g, b, a)
kivy_mock.get_color_from_hex = lambda _: (1, 1, 1, 1)

# Set up modules with proper base classes for inheritance
boxlayout_mock = unittest.mock.MagicMock()
boxlayout_mock.BoxLayout = MockBoxLayout

scrollview_mock = unittest.mock.MagicMock()
scrollview_mock.ScrollView = MockScrollView

app_mock = unittest.mock.MagicMock()
app_mock.App = MockApp

widget_mock = unittest.mock.MagicMock()
widget_mock.Widget = MockWidget

textinput_mock = unittest.mock.MagicMock()
textinput_mock.TextInput = MockTextInput

spinner_mock = unittest.mock.MagicMock()
spinner_mock.Spinner = MockSpinner

label_mock = unittest.mock.MagicMock()
label_mock.Label = MockLabel

# Properties need to return actual values, not MagicMocks
properties_mock = unittest.mock.MagicMock()
properties_mock.StringProperty = lambda default='': default
properties_mock.BooleanProperty = lambda default=False: default

sys.modules['kivy'] = kivy_mock
sys.modules['kivy.app'] = app_mock
sys.modules['kivy.uix'] = kivy_mock
sys.modules['kivy.uix.boxlayout'] = boxlayout_mock
sys.modules['kivy.uix.label'] = label_mock
sys.modules['kivy.uix.textinput'] = textinput_mock
sys.modules['kivy.uix.button'] = kivy_mock
sys.modules['kivy.uix.scrollview'] = scrollview_mock
sys.modules['kivy.uix.popup'] = kivy_mock
sys.modules['kivy.uix.widget'] = widget_mock
sys.modules['kivy.uix.togglebutton'] = kivy_mock
sys.modules['kivy.uix.spinner'] = spinner_mock
sys.modules['kivy.clock'] = kivy_mock
sys.modules['kivy.graphics'] = kivy_mock
sys.modules['kivy.core'] = kivy_mock
sys.modules['kivy.core.window'] = kivy_mock
sys.modules['kivy.core.clipboard'] = kivy_mock
sys.modules['kivy.properties'] = properties_mock
sys.modules['kivy.utils'] = kivy_mock

# Mock pubsub (used by btcmesh_server)
pubsub_mock = unittest.mock.MagicMock()
sys.modules['pubsub'] = pubsub_mock

# Clear cached gui_common to ensure it uses our mocks
if 'core.gui_common' in sys.modules:
    del sys.modules['core.gui_common']

# =============================================================================
# Story 15.1: Create Server GUI Application Structure
# Tests for basic GUI structure and theming
# =============================================================================


class TestServerGUIStructureStory151(unittest.TestCase):
    """Tests for Story 15.1: Create Server GUI Application Structure.

    Verifies:
    - GUI uses correct color scheme (Bitcoin orange theme)
    - Window title is "BTCMesh Relay Server"
    - Dark background color is used
    """

    def test_color_primary_is_bitcoin_orange(self):
        """Given server GUI module, Then COLOR_PRIMARY should be Bitcoin orange (#FF6B00)."""
        import btcmesh_server_gui

        # The color should be set via get_color_from_hex('#FF6B00')
        # Since we mock get_color_from_hex, we verify the constant exists
        self.assertTrue(hasattr(btcmesh_server_gui, 'COLOR_PRIMARY'))

    def test_color_bg_is_dark(self):
        """Given server GUI module, Then COLOR_BG should be dark (#1E1E1E)."""
        import btcmesh_server_gui

        self.assertTrue(hasattr(btcmesh_server_gui, 'COLOR_BG'))

    def test_color_success_exists(self):
        """Given server GUI module, Then COLOR_SUCCESS should exist for green indicators."""
        import btcmesh_server_gui

        self.assertTrue(hasattr(btcmesh_server_gui, 'COLOR_SUCCESS'))

    def test_color_error_exists(self):
        """Given server GUI module, Then COLOR_ERROR should exist for red indicators."""
        import btcmesh_server_gui

        self.assertTrue(hasattr(btcmesh_server_gui, 'COLOR_ERROR'))

    def test_color_warning_exists(self):
        """Given server GUI module, Then COLOR_WARNING should exist for orange warnings."""
        import btcmesh_server_gui

        self.assertTrue(hasattr(btcmesh_server_gui, 'COLOR_WARNING'))

    def test_color_mainnet_exists(self):
        """Given server GUI module, Then COLOR_MAINNET should exist for mainnet badge."""
        import btcmesh_server_gui

        self.assertTrue(hasattr(btcmesh_server_gui, 'COLOR_MAINNET'))

    def test_color_testnet_exists(self):
        """Given server GUI module, Then COLOR_TESTNET should exist for testnet badge."""
        import btcmesh_server_gui

        self.assertTrue(hasattr(btcmesh_server_gui, 'COLOR_TESTNET'))

    def test_color_signet_exists(self):
        """Given server GUI module, Then COLOR_SIGNET should exist for signet badge."""
        import btcmesh_server_gui

        self.assertTrue(hasattr(btcmesh_server_gui, 'COLOR_SIGNET'))

    def test_btcmesh_server_app_class_exists(self):
        """Given server GUI module, Then BTCMeshServerApp class should exist."""
        import btcmesh_server_gui

        self.assertTrue(hasattr(btcmesh_server_gui, 'BTCMeshServerApp'))

    def test_btcmesh_server_gui_class_exists(self):
        """Given server GUI module, Then BTCMeshServerGUI class should exist."""
        import btcmesh_server_gui

        self.assertTrue(hasattr(btcmesh_server_gui, 'BTCMeshServerGUI'))

    def test_app_title_is_correct(self):
        """Given BTCMeshServerApp, Then title should be 'BTCMesh Relay Server'."""
        import btcmesh_server_gui

        app = btcmesh_server_gui.BTCMeshServerApp()
        # Mock the GUI class to avoid canvas issues
        with unittest.mock.patch.object(btcmesh_server_gui, 'BTCMeshServerGUI'):
            with unittest.mock.patch.object(btcmesh_server_gui, 'Window'):
                app.build()
        self.assertEqual(app.title, 'BTCMesh Relay Server')

    def test_status_log_class_exists(self):
        """Given server GUI module, Then StatusLog class should exist for activity display."""
        import btcmesh_server_gui

        self.assertTrue(hasattr(btcmesh_server_gui, 'StatusLog'))

    def test_main_function_exists(self):
        """Given server GUI module, Then main() function should exist as entry point."""
        import btcmesh_server_gui

        self.assertTrue(hasattr(btcmesh_server_gui, 'main'))
        self.assertTrue(callable(btcmesh_server_gui.main))


class TestServerGUIConnectionStatesStory151(unittest.TestCase):
    """Tests for connection state constants in Story 15.1.

    Verifies server-specific connection states for both
    Meshtastic and Bitcoin RPC.
    """

    def test_meshtastic_disconnected_state_exists(self):
        """Given server GUI, Then Meshtastic disconnected state should be defined."""
        import btcmesh_server_gui

        self.assertTrue(hasattr(btcmesh_server_gui, 'STATE_MESHTASTIC_DISCONNECTED'))

    def test_rpc_disconnected_state_exists(self):
        """Given server GUI, Then Bitcoin RPC disconnected state should be defined."""
        import btcmesh_server_gui

        self.assertTrue(hasattr(btcmesh_server_gui, 'STATE_RPC_DISCONNECTED'))


class TestServerGUIHelperFunctionsStory151(unittest.TestCase):
    """Tests for helper functions in the server GUI."""

    def test_get_log_color_exists(self):
        """Given server GUI module, Then get_log_color function should exist."""
        import btcmesh_server_gui

        self.assertTrue(hasattr(btcmesh_server_gui, 'get_log_color'))
        self.assertTrue(callable(btcmesh_server_gui.get_log_color))

    def test_get_log_color_returns_error_for_error_level(self):
        """Given ERROR log level, Then get_log_color should return COLOR_ERROR."""
        import btcmesh_server_gui
        import logging

        color = btcmesh_server_gui.get_log_color(logging.ERROR, "Some error")
        self.assertEqual(color, btcmesh_server_gui.COLOR_ERROR)

    def test_get_log_color_returns_warning_for_warning_level(self):
        """Given WARNING log level, Then get_log_color should return COLOR_WARNING."""
        import btcmesh_server_gui
        import logging

        color = btcmesh_server_gui.get_log_color(logging.WARNING, "Some warning")
        self.assertEqual(color, btcmesh_server_gui.COLOR_WARNING)

    def test_get_log_color_returns_success_for_success_message(self):
        """Given INFO level with 'success' in message, Then get_log_color should return COLOR_SUCCESS."""
        import btcmesh_server_gui
        import logging

        color = btcmesh_server_gui.get_log_color(logging.INFO, "Broadcast success")
        self.assertEqual(color, btcmesh_server_gui.COLOR_SUCCESS)

    def test_get_log_color_returns_none_for_normal_info(self):
        """Given INFO level with normal message, Then get_log_color should return None."""
        import btcmesh_server_gui
        import logging

        color = btcmesh_server_gui.get_log_color(logging.INFO, "Normal info message")
        self.assertIsNone(color)


# =============================================================================
# Story 15.2: Implement Start/Stop Server Controls
# Tests for server start and stop functionality
# =============================================================================


class TestServerStartStopStory152(unittest.TestCase):
    """Tests for Story 15.2: Implement Start/Stop Server Controls.

    Verifies:
    - Start button initializes Meshtastic and Bitcoin RPC
    - Stop button gracefully shuts down connections
    - Button states update correctly
    - Log messages appear for start/stop events
    """

    def setUp(self):
        """Set up test fixtures."""
        # Reload modules to get fresh state with correct mocks
        if 'core.gui_common' in sys.modules:
            del sys.modules['core.gui_common']
        if 'btcmesh_server_gui' in sys.modules:
            del sys.modules['btcmesh_server_gui']

    def test_server_gui_has_start_button(self):
        """Given server GUI, Then it should have a start_btn attribute."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertTrue(hasattr(gui, 'start_btn'))

    def test_server_gui_has_stop_button(self):
        """Given server GUI, Then it should have a stop_btn attribute."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertTrue(hasattr(gui, 'stop_btn'))

    def test_stop_button_initially_disabled(self):
        """Given server GUI just started, Then stop button should be disabled."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertTrue(gui.stop_btn.disabled)

    def test_is_running_initially_false(self):
        """Given server GUI just started, Then is_running should be False."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertFalse(gui.is_running)

    def test_server_gui_has_result_queue(self):
        """Given server GUI, Then it should have a result_queue for thread communication."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertTrue(hasattr(gui, 'result_queue'))

    def test_server_gui_has_stop_event(self):
        """Given server GUI, Then it should have _stop_event for thread control."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertTrue(hasattr(gui, '_stop_event'))

    def test_server_gui_has_log_handler_attribute(self):
        """Given server GUI, Then it should have _log_handler attribute."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertTrue(hasattr(gui, '_log_handler'))
        self.assertIsNone(gui._log_handler)

    def test_on_start_pressed_disables_start_button(self):
        """Given operator clicks Start Server with valid settings, Then start button should be disabled."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            with unittest.mock.patch.object(btcmesh_server_gui, 'threading'):
                gui = btcmesh_server_gui.BTCMeshServerGUI()
                # Create separate mock objects for each input to avoid shared state
                gui.rpc_host_input = unittest.mock.MagicMock()
                gui.rpc_host_input.text = 'localhost'
                gui.rpc_port_input = unittest.mock.MagicMock()
                gui.rpc_port_input.text = '8332'
                gui.rpc_user_input = unittest.mock.MagicMock()
                gui.rpc_user_input.text = 'user'
                gui.rpc_password_input = unittest.mock.MagicMock()
                gui.rpc_password_input.text = 'password'
                mock_instance = unittest.mock.MagicMock()
                gui.on_start_pressed(mock_instance)
        self.assertTrue(gui.start_btn.disabled)

    def test_on_stop_pressed_disables_stop_button(self):
        """Given operator clicks Stop Server, Then stop button should be disabled."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            with unittest.mock.patch.object(btcmesh_server_gui, 'threading'):
                gui = btcmesh_server_gui.BTCMeshServerGUI()
                gui.is_running = True
                mock_instance = unittest.mock.MagicMock()
                gui.on_stop_pressed(mock_instance)
        self.assertTrue(gui.stop_btn.disabled)


class TestServerResultHandlingStory152(unittest.TestCase):
    """Tests for result queue handling in Story 15.2."""

    def setUp(self):
        """Set up test fixtures."""
        if 'core.gui_common' in sys.modules:
            del sys.modules['core.gui_common']
        if 'btcmesh_server_gui' in sys.modules:
            del sys.modules['btcmesh_server_gui']

    def test_handle_result_server_started_sets_is_running(self):
        """Given 'server_started' result, Then is_running should be True."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui._handle_result(('server_started', None))
        self.assertTrue(gui.is_running)

    def test_handle_result_server_started_enables_stop_button(self):
        """Given 'server_started' result, Then stop button should be enabled."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui._handle_result(('server_started', None))
        self.assertFalse(gui.stop_btn.disabled)

    def test_handle_result_server_stopped_sets_is_running_false(self):
        """Given 'server_stopped' result, Then is_running should be False."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui.is_running = True
            gui._handle_result(('server_stopped', None))
        self.assertFalse(gui.is_running)

    def test_handle_result_server_stopped_enables_start_button(self):
        """Given 'server_stopped' result, Then start button should be enabled."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui.start_btn.disabled = True
            gui._handle_result(('server_stopped', None))
        self.assertFalse(gui.start_btn.disabled)

    def test_handle_result_rpc_connected_updates_label(self):
        """Given 'rpc_connected' result with host, Then RPC label should show connected with host."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui._handle_result(('rpc_connected', {'host': 'localhost:8332', 'is_tor': False}))
        self.assertIn('Connected', gui.rpc_label.text)
        self.assertIn('localhost:8332', gui.rpc_label.text)
        self.assertNotIn('[Tor]', gui.rpc_label.text)

    def test_handle_result_rpc_connected_with_tor(self):
        """Given 'rpc_connected' result with Tor, Then RPC label should show Tor badge."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui._handle_result(('rpc_connected', {'host': '*.onion', 'is_tor': True}))
        self.assertIn('Connected', gui.rpc_label.text)
        self.assertIn('*.onion', gui.rpc_label.text)
        self.assertIn('[Tor]', gui.rpc_label.text)

    def test_handle_result_rpc_connected_without_host(self):
        """Given 'rpc_connected' result without host, Then RPC label shows default text."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui._handle_result(('rpc_connected', {'host': None, 'is_tor': False}))
        self.assertEqual(gui.rpc_label.text, btcmesh_server_gui.STATE_RPC_CONNECTED.text)

    def test_handle_result_rpc_failed_updates_label(self):
        """Given 'rpc_failed' result, Then RPC label should show failed state."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui._handle_result(('rpc_failed', 'Connection refused'))
        self.assertEqual(gui.rpc_label.text, btcmesh_server_gui.STATE_RPC_FAILED.text)

    def test_handle_result_meshtastic_connected_updates_label(self):
        """Given 'meshtastic_connected' result with device, Then Meshtastic label should show connected with device."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui._handle_result(('meshtastic_connected', {'node_id': '!abcdef12', 'device': '/dev/ttyUSB0'}))
        self.assertIn('Connected', gui.meshtastic_label.text)
        self.assertIn('!abcdef12', gui.meshtastic_label.text)
        self.assertIn('/dev/ttyUSB0', gui.meshtastic_label.text)

    def test_handle_result_meshtastic_connected_without_device(self):
        """Given 'meshtastic_connected' result without device, Then label shows connected without device path."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui._handle_result(('meshtastic_connected', {'node_id': '!abcdef12', 'device': None}))
        self.assertIn('Connected', gui.meshtastic_label.text)
        self.assertIn('!abcdef12', gui.meshtastic_label.text)
        self.assertNotIn(') on ', gui.meshtastic_label.text)  # No device path syntax

    def test_handle_result_meshtastic_failed_updates_label(self):
        """Given 'meshtastic_failed' result, Then Meshtastic label should show failed."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui._handle_result(('meshtastic_failed', 'No device found'))
        self.assertEqual(gui.meshtastic_label.text, btcmesh_server_gui.STATE_MESHTASTIC_FAILED.text)

    def test_handle_result_meshtastic_failed_re_enables_start(self):
        """Given 'meshtastic_failed' result, Then start button should be re-enabled."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui.start_btn.disabled = True
            gui._handle_result(('meshtastic_failed', 'No device found'))
        self.assertFalse(gui.start_btn.disabled)

    def test_handle_result_rpc_connected_shows_mainnet_badge(self):
        """Given 'rpc_connected' result with chain='main', Then network label shows MAINNET."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui._handle_result(('rpc_connected', {'host': 'localhost:8332', 'is_tor': False, 'chain': 'main'}))
        self.assertIn('MAINNET', gui.network_label.text)
        self.assertEqual(gui.network_label.color, btcmesh_server_gui.COLOR_MAINNET)

    def test_handle_result_rpc_connected_shows_testnet3_badge(self):
        """Given 'rpc_connected' result with chain='test', Then network label shows TESTNET3."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui._handle_result(('rpc_connected', {'host': 'localhost:18332', 'is_tor': False, 'chain': 'test'}))
        self.assertIn('TESTNET3', gui.network_label.text)
        self.assertEqual(gui.network_label.color, btcmesh_server_gui.COLOR_TESTNET)

    def test_handle_result_rpc_connected_shows_testnet4_badge(self):
        """Given 'rpc_connected' result with chain='testnet4', Then network label shows TESTNET4."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui._handle_result(('rpc_connected', {'host': 'localhost:48332', 'is_tor': False, 'chain': 'testnet4'}))
        self.assertIn('TESTNET4', gui.network_label.text)
        self.assertEqual(gui.network_label.color, btcmesh_server_gui.COLOR_TESTNET)

    def test_handle_result_rpc_connected_shows_signet_badge(self):
        """Given 'rpc_connected' result with chain='signet', Then network label shows SIGNET."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui._handle_result(('rpc_connected', {'host': 'localhost:38332', 'is_tor': False, 'chain': 'signet'}))
        self.assertIn('SIGNET', gui.network_label.text)
        self.assertEqual(gui.network_label.color, btcmesh_server_gui.COLOR_SIGNET)

    def test_handle_result_server_stopped_clears_network_badge(self):
        """Given 'server_stopped' result, Then network label should be cleared."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            # First set a network badge
            gui.network_label.text = 'Network: MAINNET'
            gui.network_label.color = btcmesh_server_gui.COLOR_MAINNET
            # Then simulate server stopped
            gui._handle_result(('server_stopped', None))
        self.assertEqual(gui.network_label.text, '--')
        self.assertEqual(gui.network_label.color, btcmesh_server_gui.COLOR_DISCONNECTED)

    def test_server_gui_has_network_label(self):
        """Given server GUI, Then it should have a network_label attribute."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertTrue(hasattr(gui, 'network_label'))


class TestServerLogParsingStory152(unittest.TestCase):
    """Tests for log parsing in Story 15.2."""

    def setUp(self):
        """Set up test fixtures."""
        if 'core.gui_common' in sys.modules:
            del sys.modules['core.gui_common']
        if 'btcmesh_server_gui' in sys.modules:
            del sys.modules['btcmesh_server_gui']

    def test_parse_log_for_status_function_exists(self):
        """Given server GUI module, Then parse_log_for_status function should exist."""
        import btcmesh_server_gui

        self.assertTrue(hasattr(btcmesh_server_gui, 'parse_log_for_status'))
        self.assertTrue(callable(btcmesh_server_gui.parse_log_for_status))

    def test_parse_log_detects_rpc_connected(self):
        """Given RPC connected log message with host and chain, Then parse_log_for_status returns rpc_connected with dict."""
        import btcmesh_server_gui

        result = btcmesh_server_gui.parse_log_for_status(
            "Connected to Bitcoin Core RPC node successfully. Host: localhost:8332, Tor: False, Chain: main"
        )
        self.assertEqual(result[0], 'rpc_connected')
        self.assertEqual(result[1], {'host': 'localhost:8332', 'is_tor': False, 'chain': 'main'})

    def test_parse_log_detects_rpc_connected_with_tor(self):
        """Given RPC connected log message with Tor, Then parse_log_for_status returns is_tor=True."""
        import btcmesh_server_gui

        result = btcmesh_server_gui.parse_log_for_status(
            "Connected to Bitcoin Core RPC node successfully. Host: *.onion, Tor: True, Chain: signet"
        )
        self.assertEqual(result[0], 'rpc_connected')
        self.assertEqual(result[1], {'host': '*.onion', 'is_tor': True, 'chain': 'signet'})

    def test_parse_log_detects_rpc_connected_testnet4(self):
        """Given RPC connected log message with testnet4, Then parse_log_for_status extracts chain correctly."""
        import btcmesh_server_gui

        result = btcmesh_server_gui.parse_log_for_status(
            "Connected to Bitcoin Core RPC node successfully. Host: localhost:48332, Tor: False, Chain: testnet4"
        )
        self.assertEqual(result[0], 'rpc_connected')
        self.assertEqual(result[1]['chain'], 'testnet4')

    def test_parse_log_detects_rpc_failed(self):
        """Given RPC failed log message, Then parse_log_for_status returns rpc_failed."""
        import btcmesh_server_gui

        result = btcmesh_server_gui.parse_log_for_status(
            "Failed to connect to Bitcoin Core RPC node: Connection refused. Continuing without RPC."
        )
        self.assertEqual(result[0], 'rpc_failed')
        self.assertIn('Connection refused', result[1])

    def test_parse_log_detects_meshtastic_connected(self):
        """Given Meshtastic connected log message, Then parse_log_for_status returns meshtastic_connected with dict."""
        import btcmesh_server_gui

        result = btcmesh_server_gui.parse_log_for_status(
            "Meshtastic interface initialized successfully. Device: /dev/ttyUSB0, My Node Num: !abcdef12"
        )
        self.assertEqual(result[0], 'meshtastic_connected')
        self.assertEqual(result[1], {'node_id': '!abcdef12', 'device': '/dev/ttyUSB0'})

    def test_parse_log_detects_meshtastic_failed(self):
        """Given Meshtastic failed log message, Then parse_log_for_status returns meshtastic_failed."""
        import btcmesh_server_gui

        result = btcmesh_server_gui.parse_log_for_status(
            "Failed to initialize Meshtastic interface. Exiting."
        )
        self.assertEqual(result[0], 'meshtastic_failed')

    def test_parse_log_meshtastic_invalid_device_none_string(self):
        """Given Meshtastic log with Device='None', Then parse_log_for_status returns meshtastic_failed."""
        import btcmesh_server_gui

        result = btcmesh_server_gui.parse_log_for_status(
            "Meshtastic interface initialized successfully. Device: None, My Node Num: Unknown Node Num"
        )
        self.assertEqual(result[0], 'meshtastic_failed')
        self.assertEqual(result[1], "Invalid device info")

    def test_parse_log_meshtastic_invalid_device_question_mark(self):
        """Given Meshtastic log with Device='?', Then parse_log_for_status returns meshtastic_failed."""
        import btcmesh_server_gui

        result = btcmesh_server_gui.parse_log_for_status(
            "Meshtastic interface initialized successfully. Device: ?, My Node Num: !abcdef12"
        )
        # Still connected because node_id is valid, just device is None
        self.assertEqual(result[0], 'meshtastic_connected')
        self.assertEqual(result[1], {'node_id': '!abcdef12', 'device': None})

    def test_parse_log_meshtastic_invalid_node_id(self):
        """Given Meshtastic log with invalid node ID, Then parse_log_for_status returns meshtastic_failed."""
        import btcmesh_server_gui

        result = btcmesh_server_gui.parse_log_for_status(
            "Meshtastic interface initialized successfully. Device: /dev/ttyUSB0, My Node Num: Unknown Node Num"
        )
        self.assertEqual(result[0], 'meshtastic_failed')
        self.assertEqual(result[1], "Invalid device info")

    def test_parse_log_meshtastic_no_device_connected_error(self):
        """Given server error about no device connected, Then parse_log_for_status returns meshtastic_failed."""
        import btcmesh_server_gui

        result = btcmesh_server_gui.parse_log_for_status(
            "Meshtastic interface created but could not retrieve device info. "
            "This usually means no Meshtastic device is connected."
        )
        self.assertEqual(result[0], 'meshtastic_failed')
        self.assertEqual(result[1], "No device connected")

    def test_parse_log_detects_server_started(self):
        """Given server started log message, Then parse_log_for_status returns server_started."""
        import btcmesh_server_gui

        result = btcmesh_server_gui.parse_log_for_status(
            "Registered Meshtastic message handler. Waiting for messages..."
        )
        self.assertEqual(result, ('server_started', None))

    def test_parse_log_detects_server_stopped(self):
        """Given server stopped log message, Then parse_log_for_status returns server_stopped."""
        import btcmesh_server_gui

        result = btcmesh_server_gui.parse_log_for_status(
            "Closing Meshtastic interface..."
        )
        self.assertEqual(result, ('server_stopped', None))

    def test_parse_log_returns_none_for_normal_message(self):
        """Given normal log message, Then parse_log_for_status returns None."""
        import btcmesh_server_gui

        result = btcmesh_server_gui.parse_log_for_status(
            "Some normal log message"
        )
        self.assertIsNone(result)

    def test_process_results_method_exists(self):
        """Given server GUI, Then _process_results method should exist."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertTrue(hasattr(gui, '_process_results'))
        self.assertTrue(callable(gui._process_results))


class TestQueueLogHandlerStory152(unittest.TestCase):
    """Tests for QueueLogHandler class in Story 15.2."""

    def setUp(self):
        """Set up test fixtures."""
        if 'core.gui_common' in sys.modules:
            del sys.modules['core.gui_common']
        if 'btcmesh_server_gui' in sys.modules:
            del sys.modules['btcmesh_server_gui']

    def test_queue_log_handler_class_exists(self):
        """Given server GUI module, Then QueueLogHandler class should exist."""
        import btcmesh_server_gui

        self.assertTrue(hasattr(btcmesh_server_gui, 'QueueLogHandler'))

    def test_queue_log_handler_puts_log_to_queue(self):
        """Given QueueLogHandler with a queue, When emit is called, Then message goes to queue."""
        import btcmesh_server_gui
        import logging
        import queue

        q = queue.Queue()
        handler = btcmesh_server_gui.QueueLogHandler(q)
        handler.setFormatter(logging.Formatter('%(message)s'))

        record = logging.LogRecord(
            name='test', level=logging.INFO, pathname='', lineno=0,
            msg='Test message', args=(), exc_info=None
        )
        handler.emit(record)

        result = q.get_nowait()
        self.assertEqual(result[0], 'log')
        self.assertEqual(result[1], 'Test message')
        self.assertEqual(result[2], logging.INFO)


class TestRPCSettingsStory181(unittest.TestCase):
    """Tests for Bitcoin RPC Settings in Story 18.1."""

    def setUp(self):
        """Set up test fixtures."""
        if 'core.gui_common' in sys.modules:
            del sys.modules['core.gui_common']
        if 'btcmesh_server_gui' in sys.modules:
            del sys.modules['btcmesh_server_gui']

    def test_gui_has_rpc_host_input(self):
        """Given server GUI, Then it should have rpc_host_input attribute."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertTrue(hasattr(gui, 'rpc_host_input'))

    def test_gui_has_rpc_port_input(self):
        """Given server GUI, Then it should have rpc_port_input attribute."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertTrue(hasattr(gui, 'rpc_port_input'))

    def test_gui_has_rpc_user_input(self):
        """Given server GUI, Then it should have rpc_user_input attribute."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertTrue(hasattr(gui, 'rpc_user_input'))

    def test_gui_has_rpc_password_input(self):
        """Given server GUI, Then it should have rpc_password_input attribute."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertTrue(hasattr(gui, 'rpc_password_input'))

    def test_password_input_is_masked_by_default(self):
        """Given server GUI, Then password input should be masked (password=True)."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertTrue(gui.rpc_password_input.password)

    def test_gui_has_show_password_button(self):
        """Given server GUI, Then it should have show_password_btn attribute."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertTrue(hasattr(gui, 'show_password_btn'))

    def test_toggle_password_visibility_shows_password(self):
        """Given password is masked, When toggle is clicked, Then password is visible."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            # Initially masked
            self.assertTrue(gui.rpc_password_input.password)
            # Toggle
            gui._toggle_password_visibility(None)
        # Now visible
        self.assertFalse(gui.rpc_password_input.password)
        self.assertEqual(gui.show_password_btn.text, 'Hide')

    def test_toggle_password_visibility_hides_password(self):
        """Given password is visible, When toggle is clicked, Then password is masked."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            # First toggle to show
            gui._toggle_password_visibility(None)
            self.assertFalse(gui.rpc_password_input.password)
            # Toggle again to hide
            gui._toggle_password_visibility(None)
        self.assertTrue(gui.rpc_password_input.password)
        self.assertEqual(gui.show_password_btn.text, 'Show')

    def test_gui_has_test_connection_button(self):
        """Given server GUI, Then it should have test_connection_btn attribute."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertTrue(hasattr(gui, 'test_connection_btn'))

    def test_test_connection_validates_empty_host(self):
        """Given empty host, When Test Connection clicked, Then error is logged."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            # Create separate mock objects for each input to avoid shared state
            gui.rpc_host_input = unittest.mock.MagicMock()
            gui.rpc_host_input.text = ''
            gui.rpc_port_input = unittest.mock.MagicMock()
            gui.rpc_port_input.text = '8332'
            gui.rpc_user_input = unittest.mock.MagicMock()
            gui.rpc_user_input.text = 'user'
            gui.rpc_password_input = unittest.mock.MagicMock()
            gui.rpc_password_input.text = 'pass'
            # Mock the add_message method
            gui.status_log.add_message = unittest.mock.MagicMock()
            gui._on_test_connection(None)
        # Verify error message was logged
        gui.status_log.add_message.assert_called()
        call_args = gui.status_log.add_message.call_args[0]
        self.assertIn('Host is required', call_args[0])

    def test_test_connection_validates_empty_password(self):
        """Given empty password, When Test Connection clicked, Then error is logged."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            # Create separate mock objects for each input to avoid shared state
            gui.rpc_host_input = unittest.mock.MagicMock()
            gui.rpc_host_input.text = 'localhost'
            gui.rpc_port_input = unittest.mock.MagicMock()
            gui.rpc_port_input.text = '8332'
            gui.rpc_user_input = unittest.mock.MagicMock()
            gui.rpc_user_input.text = 'user'
            gui.rpc_password_input = unittest.mock.MagicMock()
            gui.rpc_password_input.text = ''
            # Mock the add_message method
            gui.status_log.add_message = unittest.mock.MagicMock()
            gui._on_test_connection(None)
        # Verify error message was logged
        gui.status_log.add_message.assert_called()
        call_args = gui.status_log.add_message.call_args[0]
        self.assertIn('Password is required', call_args[0])

    def test_handle_result_test_connection_success(self):
        """Given test_connection_result with success, Then success message logged."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui.test_connection_btn.disabled = True
            gui._handle_result(('test_connection_result', True, 'Connected to main network'))
        self.assertFalse(gui.test_connection_btn.disabled)

    def test_handle_result_test_connection_failure(self):
        """Given test_connection_result with failure, Then error message logged."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui.test_connection_btn.disabled = True
            gui._handle_result(('test_connection_result', False, 'Connection refused'))
        self.assertFalse(gui.test_connection_btn.disabled)

    def test_on_start_validates_empty_fields(self):
        """Given empty RPC fields, When Start Server clicked, Then error is logged."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            # Create separate mock objects for each input to avoid shared state
            gui.rpc_host_input = unittest.mock.MagicMock()
            gui.rpc_host_input.text = ''
            gui.rpc_port_input = unittest.mock.MagicMock()
            gui.rpc_port_input.text = ''
            gui.rpc_user_input = unittest.mock.MagicMock()
            gui.rpc_user_input.text = ''
            gui.rpc_password_input = unittest.mock.MagicMock()
            gui.rpc_password_input.text = ''
            # Mock the add_message method
            gui.status_log.add_message = unittest.mock.MagicMock()
            gui.on_start_pressed(None)
        # Verify error message was logged
        gui.status_log.add_message.assert_called()
        call_args = gui.status_log.add_message.call_args[0]
        self.assertIn('Cannot start', call_args[0])

    def test_host_input_is_masked_by_default(self):
        """Given server GUI, Then host input should be masked (password=True) for privacy."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertTrue(gui.rpc_host_input.password)

    def test_gui_has_show_host_button(self):
        """Given server GUI, Then it should have show_host_btn attribute."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertTrue(hasattr(gui, 'show_host_btn'))

    def test_toggle_host_visibility_shows_host(self):
        """Given host is masked, When toggle is clicked, Then host is visible."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            # Initially masked
            self.assertTrue(gui.rpc_host_input.password)
            # Toggle
            gui._toggle_host_visibility(None)
        # Now visible
        self.assertFalse(gui.rpc_host_input.password)
        self.assertEqual(gui.show_host_btn.text, 'Hide')

    def test_toggle_host_visibility_hides_host(self):
        """Given host is visible, When toggle is clicked, Then host is masked."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            # First toggle to show
            gui._toggle_host_visibility(None)
            self.assertFalse(gui.rpc_host_input.password)
            # Toggle again to hide
            gui._toggle_host_visibility(None)
        self.assertTrue(gui.rpc_host_input.password)
        self.assertEqual(gui.show_host_btn.text, 'Show')

    def test_rpc_settings_disabled_when_server_starts(self):
        """Given server starts, Then RPC settings inputs should be disabled."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            with unittest.mock.patch.object(btcmesh_server_gui, 'threading'):
                gui = btcmesh_server_gui.BTCMeshServerGUI()
                # Create separate mock objects for each input to avoid shared state
                gui.rpc_host_input = unittest.mock.MagicMock()
                gui.rpc_host_input.text = 'localhost'
                gui.rpc_port_input = unittest.mock.MagicMock()
                gui.rpc_port_input.text = '8332'
                gui.rpc_user_input = unittest.mock.MagicMock()
                gui.rpc_user_input.text = 'user'
                gui.rpc_password_input = unittest.mock.MagicMock()
                gui.rpc_password_input.text = 'password'
                gui.test_connection_btn = unittest.mock.MagicMock()
                gui.on_start_pressed(None)
        # Verify all inputs are disabled
        self.assertTrue(gui.rpc_host_input.disabled)
        self.assertTrue(gui.rpc_port_input.disabled)
        self.assertTrue(gui.rpc_user_input.disabled)
        self.assertTrue(gui.rpc_password_input.disabled)
        self.assertTrue(gui.test_connection_btn.disabled)

    def test_rpc_settings_enabled_when_server_stops(self):
        """Given server stops, Then RPC settings inputs should be re-enabled."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            # Disable settings (simulating running server)
            gui._set_rpc_settings_enabled(False)
            self.assertTrue(gui.rpc_host_input.disabled)
            # Simulate server stopped
            gui._handle_result(('server_stopped', None))
        # Verify all inputs are re-enabled
        self.assertFalse(gui.rpc_host_input.disabled)
        self.assertFalse(gui.rpc_port_input.disabled)
        self.assertFalse(gui.rpc_user_input.disabled)
        self.assertFalse(gui.rpc_password_input.disabled)
        self.assertFalse(gui.test_connection_btn.disabled)

    def test_rpc_settings_enabled_on_meshtastic_failure(self):
        """Given meshtastic fails, Then RPC settings inputs should be re-enabled."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            # Disable settings (simulating server start attempt)
            gui._set_rpc_settings_enabled(False)
            self.assertTrue(gui.rpc_host_input.disabled)
            # Simulate meshtastic failure
            gui._handle_result(('meshtastic_failed', 'No device found'))
        # Verify inputs are re-enabled
        self.assertFalse(gui.rpc_host_input.disabled)
        self.assertFalse(gui.test_connection_btn.disabled)

    def test_rpc_settings_enabled_on_init_error(self):
        """Given init error occurs, Then RPC settings inputs should be re-enabled."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            # Disable settings (simulating server start attempt)
            gui._set_rpc_settings_enabled(False)
            self.assertTrue(gui.rpc_host_input.disabled)
            # Simulate init error
            gui._handle_result(('init_error', 'Some error'))
        # Verify inputs are re-enabled
        self.assertFalse(gui.rpc_host_input.disabled)
        self.assertFalse(gui.test_connection_btn.disabled)

    def test_start_button_disabled_during_test_connection(self):
        """Given Test Connection clicked, Then Start button should be disabled."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            with unittest.mock.patch.object(btcmesh_server_gui, 'threading'):
                gui = btcmesh_server_gui.BTCMeshServerGUI()
                # Set valid inputs
                gui.rpc_host_input = unittest.mock.MagicMock()
                gui.rpc_host_input.text = 'localhost'
                gui.rpc_port_input = unittest.mock.MagicMock()
                gui.rpc_port_input.text = '8332'
                gui.rpc_user_input = unittest.mock.MagicMock()
                gui.rpc_user_input.text = 'user'
                gui.rpc_password_input = unittest.mock.MagicMock()
                gui.rpc_password_input.text = 'password'
                gui._on_test_connection(None)
        # Verify start button is disabled during test
        self.assertTrue(gui.start_btn.disabled)

    def test_start_button_enabled_after_test_connection_success(self):
        """Given Test Connection succeeds, Then Start button should be re-enabled."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui.start_btn.disabled = True
            gui._handle_result(('test_connection_result', True, 'Connected to main network'))
        self.assertFalse(gui.start_btn.disabled)

    def test_start_button_enabled_after_test_connection_failure(self):
        """Given Test Connection fails, Then Start button should be re-enabled."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui.start_btn.disabled = True
            gui._handle_result(('test_connection_result', False, 'Connection refused'))
        self.assertFalse(gui.start_btn.disabled)


class TestMeshtasticDeviceSettingsStory182(unittest.TestCase):
    """Tests for Story 18.2: Meshtastic Device Settings."""

    def test_gui_has_device_spinner(self):
        """Given server GUI, Then it should have device_spinner attribute."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertTrue(hasattr(gui, 'device_spinner'))

    def test_gui_has_scan_button(self):
        """Given server GUI, Then it should have scan_btn attribute."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertTrue(hasattr(gui, 'scan_btn'))

    def test_device_spinner_default_is_auto_detect(self):
        """Given server GUI with no env config, Then device spinner should show Auto-detect."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            with unittest.mock.patch.dict('os.environ', {}, clear=True):
                gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertEqual(gui.device_spinner.text, btcmesh_server_gui.DEVICE_AUTO_DETECT)

    def test_device_spinner_uses_env_default(self):
        """Given MESHTASTIC_SERIAL_PORT env var, Then device spinner should use it."""
        import btcmesh_server_gui
        import os

        # Set the env var before creating GUI (will be used by os.getenv)
        original_value = os.environ.get('MESHTASTIC_SERIAL_PORT')
        os.environ['MESHTASTIC_SERIAL_PORT'] = '/dev/ttyUSB0'
        try:
            with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
                gui = btcmesh_server_gui.BTCMeshServerGUI()
            self.assertEqual(gui.device_spinner.text, '/dev/ttyUSB0')
        finally:
            # Restore original value
            if original_value is None:
                os.environ.pop('MESHTASTIC_SERIAL_PORT', None)
            else:
                os.environ['MESHTASTIC_SERIAL_PORT'] = original_value

    def test_devices_found_updates_spinner_values(self):
        """Given devices_found result, Then spinner values should include Auto-detect and devices."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui._handle_result(('devices_found', ['/dev/ttyUSB0', '/dev/ttyACM0']))
        self.assertIn(btcmesh_server_gui.DEVICE_AUTO_DETECT, gui.device_spinner.values)
        self.assertIn('/dev/ttyUSB0', gui.device_spinner.values)
        self.assertIn('/dev/ttyACM0', gui.device_spinner.values)

    def test_devices_found_single_device_auto_selects(self):
        """Given single device found, Then spinner should auto-select it."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui._handle_result(('devices_found', ['/dev/ttyUSB0']))
        self.assertEqual(gui.device_spinner.text, '/dev/ttyUSB0')

    def test_devices_found_no_devices_shows_auto_detect(self):
        """Given no devices found, Then spinner should show Auto-detect."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui.device_spinner.text = btcmesh_server_gui.DEVICE_SCANNING
            gui._handle_result(('devices_found', []))
        self.assertEqual(gui.device_spinner.text, btcmesh_server_gui.DEVICE_AUTO_DETECT)

    def test_meshtastic_settings_disabled_when_server_starts(self):
        """Given server starts, Then meshtastic settings should be disabled."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            with unittest.mock.patch.object(btcmesh_server_gui, 'threading'):
                gui = btcmesh_server_gui.BTCMeshServerGUI()
                # Set valid RPC inputs
                gui.rpc_host_input.text = 'localhost'
                gui.rpc_port_input.text = '8332'
                gui.rpc_user_input.text = 'user'
                gui.rpc_password_input.text = 'password'
                gui.on_start_pressed(None)
        self.assertTrue(gui.device_spinner.disabled)
        self.assertTrue(gui.scan_btn.disabled)

    def test_meshtastic_settings_enabled_when_server_stops(self):
        """Given server stops, Then meshtastic settings should be re-enabled."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui._set_meshtastic_settings_enabled(False)
            self.assertTrue(gui.device_spinner.disabled)
            gui._handle_result(('server_stopped', None))
        self.assertFalse(gui.device_spinner.disabled)
        self.assertFalse(gui.scan_btn.disabled)

    def test_meshtastic_settings_enabled_on_meshtastic_failure(self):
        """Given meshtastic fails, Then meshtastic settings should be re-enabled."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui._set_meshtastic_settings_enabled(False)
            gui._handle_result(('meshtastic_failed', 'No device found'))
        self.assertFalse(gui.device_spinner.disabled)
        self.assertFalse(gui.scan_btn.disabled)

    def test_scan_button_disabled_during_scan(self):
        """Given Scan button clicked, Then scan button should be disabled during scan."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            with unittest.mock.patch.object(btcmesh_server_gui, 'threading'):
                gui = btcmesh_server_gui.BTCMeshServerGUI()
                gui._on_scan_devices(None)
        self.assertTrue(gui.scan_btn.disabled)
        self.assertEqual(gui.device_spinner.text, btcmesh_server_gui.DEVICE_SCANNING)

    def test_scan_button_enabled_after_devices_found(self):
        """Given devices_found result, Then scan button should be re-enabled."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui.scan_btn.disabled = True
            gui._handle_result(('devices_found', ['/dev/ttyUSB0']))
        self.assertFalse(gui.scan_btn.disabled)

    def test_auto_detect_passes_none_to_server(self):
        """Given Auto-detect selected, Then serial_port should be None when starting server."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            with unittest.mock.patch.object(btcmesh_server_gui, 'threading') as mock_threading:
                with unittest.mock.patch.object(btcmesh_server_gui.btcmesh_server, 'main') as mock_main:
                    gui = btcmesh_server_gui.BTCMeshServerGUI()
                    gui.rpc_host_input.text = 'localhost'
                    gui.rpc_port_input.text = '8332'
                    gui.rpc_user_input.text = 'user'
                    gui.rpc_password_input.text = 'password'
                    gui.device_spinner.text = btcmesh_server_gui.DEVICE_AUTO_DETECT

                    # Capture the thread target function
                    gui.on_start_pressed(None)
                    thread_call = mock_threading.Thread.call_args
                    target_fn = thread_call.kwargs.get('target') or thread_call[1].get('target')

                    # Call the target function to trigger btcmesh_server.main
                    if target_fn:
                        target_fn()
                        mock_main.assert_called_once()
                        call_kwargs = mock_main.call_args.kwargs
                        self.assertIsNone(call_kwargs.get('serial_port'))

    def test_selected_device_passes_to_server(self):
        """Given device selected, Then serial_port should be passed to server."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            with unittest.mock.patch.object(btcmesh_server_gui, 'threading') as mock_threading:
                with unittest.mock.patch.object(btcmesh_server_gui.btcmesh_server, 'main') as mock_main:
                    gui = btcmesh_server_gui.BTCMeshServerGUI()
                    gui.rpc_host_input.text = 'localhost'
                    gui.rpc_port_input.text = '8332'
                    gui.rpc_user_input.text = 'user'
                    gui.rpc_password_input.text = 'password'
                    gui.device_spinner.text = '/dev/ttyUSB0'

                    # Capture the thread target function
                    gui.on_start_pressed(None)
                    thread_call = mock_threading.Thread.call_args
                    target_fn = thread_call.kwargs.get('target') or thread_call[1].get('target')

                    # Call the target function to trigger btcmesh_server.main
                    if target_fn:
                        target_fn()
                        mock_main.assert_called_once()
                        call_kwargs = mock_main.call_args.kwargs
                        self.assertEqual(call_kwargs.get('serial_port'), '/dev/ttyUSB0')


class TestReassemblyTimeoutSettingsStory183(unittest.TestCase):
    """Tests for Story 18.3: Reassembly Timeout Settings."""

    def test_gui_has_timeout_input(self):
        """Given server GUI, Then it should have timeout_input attribute."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertTrue(hasattr(gui, 'timeout_input'))

    def test_timeout_input_default_is_300(self):
        """Given server GUI with no env config, Then timeout should default to 300."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            with unittest.mock.patch.dict('os.environ', {}, clear=True):
                gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertEqual(gui.timeout_input.text, '300')

    def test_timeout_input_uses_env_default(self):
        """Given REASSEMBLY_TIMEOUT_SECONDS env var, Then timeout input should use it."""
        import btcmesh_server_gui
        import os

        original_value = os.environ.get('REASSEMBLY_TIMEOUT_SECONDS')
        os.environ['REASSEMBLY_TIMEOUT_SECONDS'] = '600'
        try:
            with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
                gui = btcmesh_server_gui.BTCMeshServerGUI()
            self.assertEqual(gui.timeout_input.text, '600')
        finally:
            if original_value is None:
                os.environ.pop('REASSEMBLY_TIMEOUT_SECONDS', None)
            else:
                os.environ['REASSEMBLY_TIMEOUT_SECONDS'] = original_value

    def test_timeout_settings_disabled_when_server_starts(self):
        """Given server starts, Then timeout settings should be disabled."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            with unittest.mock.patch.object(btcmesh_server_gui, 'threading'):
                gui = btcmesh_server_gui.BTCMeshServerGUI()
                gui.rpc_host_input.text = 'localhost'
                gui.rpc_port_input.text = '8332'
                gui.rpc_user_input.text = 'user'
                gui.rpc_password_input.text = 'password'
                gui.on_start_pressed(None)
        self.assertTrue(gui.timeout_input.disabled)

    def test_timeout_settings_enabled_when_server_stops(self):
        """Given server stops, Then timeout settings should be re-enabled."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui._set_timeout_settings_enabled(False)
            self.assertTrue(gui.timeout_input.disabled)
            gui._handle_result(('server_stopped', None))
        self.assertFalse(gui.timeout_input.disabled)

    def test_timeout_settings_enabled_on_meshtastic_failure(self):
        """Given meshtastic fails, Then timeout settings should be re-enabled."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui._set_timeout_settings_enabled(False)
            gui._handle_result(('meshtastic_failed', 'No device found'))
        self.assertFalse(gui.timeout_input.disabled)

    def test_timeout_settings_enabled_on_init_error(self):
        """Given init error, Then timeout settings should be re-enabled."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui._set_timeout_settings_enabled(False)
            gui._handle_result(('init_error', 'Some error'))
        self.assertFalse(gui.timeout_input.disabled)

    def test_start_rejected_with_empty_timeout(self):
        """Given empty timeout, Then start should be rejected with error message."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui.rpc_host_input.text = 'localhost'
            gui.rpc_port_input.text = '8332'
            gui.rpc_user_input.text = 'user'
            gui.rpc_password_input.text = 'password'
            gui.timeout_input.text = ''
            gui.on_start_pressed(None)
        # Start button should not be disabled (rejected early)
        self.assertFalse(gui.start_btn.disabled)

    def test_start_rejected_with_invalid_timeout(self):
        """Given non-integer timeout, Then start should be rejected with error message."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui.rpc_host_input.text = 'localhost'
            gui.rpc_port_input.text = '8332'
            gui.rpc_user_input.text = 'user'
            gui.rpc_password_input.text = 'password'
            gui.timeout_input.text = 'abc'
            gui.on_start_pressed(None)
        self.assertFalse(gui.start_btn.disabled)

    def test_start_rejected_with_zero_timeout(self):
        """Given zero timeout, Then start should be rejected with error message."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui.rpc_host_input.text = 'localhost'
            gui.rpc_port_input.text = '8332'
            gui.rpc_user_input.text = 'user'
            gui.rpc_password_input.text = 'password'
            gui.timeout_input.text = '0'
            gui.on_start_pressed(None)
        self.assertFalse(gui.start_btn.disabled)

    def test_start_rejected_with_negative_timeout(self):
        """Given negative timeout, Then start should be rejected with error message."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui.rpc_host_input.text = 'localhost'
            gui.rpc_port_input.text = '8332'
            gui.rpc_user_input.text = 'user'
            gui.rpc_password_input.text = 'password'
            gui.timeout_input.text = '-10'
            gui.on_start_pressed(None)
        self.assertFalse(gui.start_btn.disabled)

    def test_timeout_passed_to_server(self):
        """Given valid timeout, Then reassembly_timeout should be passed to server."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            with unittest.mock.patch.object(btcmesh_server_gui, 'threading') as mock_threading:
                with unittest.mock.patch.object(btcmesh_server_gui.btcmesh_server, 'main') as mock_main:
                    gui = btcmesh_server_gui.BTCMeshServerGUI()
                    gui.rpc_host_input.text = 'localhost'
                    gui.rpc_port_input.text = '8332'
                    gui.rpc_user_input.text = 'user'
                    gui.rpc_password_input.text = 'password'
                    gui.timeout_input.text = '120'

                    gui.on_start_pressed(None)
                    thread_call = mock_threading.Thread.call_args
                    target_fn = thread_call.kwargs.get('target') or thread_call[1].get('target')

                    if target_fn:
                        target_fn()
                        mock_main.assert_called_once()
                        call_kwargs = mock_main.call_args.kwargs
                        self.assertEqual(call_kwargs.get('reassembly_timeout'), 120)


class TestActivityLogDisplayStory171(unittest.TestCase):
    """Tests for Story 17.1: Implement Activity Log Display.

    Verifies:
    - Scrollable activity log shows server events
    - Log messages have timestamps
    - Color coding per log_color_spec.md
    - Auto-scroll to newest entry
    """

    def setUp(self):
        """Set up test fixtures."""
        if 'core.gui_common' in sys.modules:
            del sys.modules['core.gui_common']
        if 'btcmesh_server_gui' in sys.modules:
            del sys.modules['btcmesh_server_gui']

    def test_gui_has_status_log(self):
        """Given server GUI, Then it should have status_log attribute."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertTrue(hasattr(gui, 'status_log'))

    def test_gui_has_clear_button(self):
        """Given server GUI, Then it should have clear_btn attribute for clearing log."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertTrue(hasattr(gui, 'clear_btn'))

    def test_log_handler_uses_timestamp_format(self):
        """Given server starts, Then log handler should format messages with [HH:MM:SS] timestamps."""
        import btcmesh_server_gui
        import logging

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            with unittest.mock.patch.object(btcmesh_server_gui, 'threading'):
                gui = btcmesh_server_gui.BTCMeshServerGUI()
                gui.rpc_host_input.text = 'localhost'
                gui.rpc_port_input.text = '8332'
                gui.rpc_user_input.text = 'user'
                gui.rpc_password_input.text = 'password'
                gui.on_start_pressed(None)

        # Verify log handler was created and has correct format
        self.assertIsNotNone(gui._log_handler)
        formatter = gui._log_handler.formatter
        self.assertIsNotNone(formatter)
        # Check format string includes asctime
        self.assertIn('asctime', formatter._fmt)
        # Check datefmt is HH:MM:SS
        self.assertEqual(formatter.datefmt, '%H:%M:%S')

    def test_log_handler_formats_message_with_timestamp(self):
        """Given log handler, When formatting a log record, Then output should contain [HH:MM:SS] timestamp."""
        import btcmesh_server_gui
        import logging

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            with unittest.mock.patch.object(btcmesh_server_gui, 'threading'):
                gui = btcmesh_server_gui.BTCMeshServerGUI()
                gui.rpc_host_input.text = 'localhost'
                gui.rpc_port_input.text = '8332'
                gui.rpc_user_input.text = 'user'
                gui.rpc_password_input.text = 'password'
                gui.on_start_pressed(None)

        # Create a log record and format it
        record = logging.LogRecord(
            name='test', level=logging.INFO, pathname='', lineno=0,
            msg='Test message', args=(), exc_info=None
        )
        formatted = gui._log_handler.formatter.format(record)

        # Verify formatted message contains timestamp in [HH:MM:SS] format
        # Pattern: [00:00:00] to [23:59:59]
        timestamp_pattern = r'\[\d{2}:\d{2}:\d{2}\]'
        self.assertRegex(formatted, timestamp_pattern)
        # Verify the message is also present
        self.assertIn('Test message', formatted)

    def test_log_message_result_adds_to_status_log(self):
        """Given 'log' result type, Then message should be added to status_log."""
        import btcmesh_server_gui
        import logging

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui.status_log.add_message = unittest.mock.MagicMock()
            gui._handle_result(('log', 'Test log message', logging.INFO))
        gui.status_log.add_message.assert_called()

    def test_get_log_color_returns_error_for_failed_keyword(self):
        """Given INFO level with 'failed' keyword, Then get_log_color should return COLOR_ERROR."""
        import btcmesh_server_gui
        import logging

        color = btcmesh_server_gui.get_log_color(logging.INFO, "Connection failed")
        self.assertEqual(color, btcmesh_server_gui.COLOR_ERROR)

    def test_get_log_color_returns_error_for_nack_keyword(self):
        """Given INFO level with 'nack' keyword, Then get_log_color should return COLOR_ERROR."""
        import btcmesh_server_gui
        import logging

        color = btcmesh_server_gui.get_log_color(logging.INFO, "Sending NACK to client")
        self.assertEqual(color, btcmesh_server_gui.COLOR_ERROR)

    def test_get_log_color_returns_error_for_timed_out_keyword(self):
        """Given INFO level with 'timed out' keyword, Then get_log_color should return COLOR_ERROR."""
        import btcmesh_server_gui
        import logging

        color = btcmesh_server_gui.get_log_color(logging.INFO, "Session timed out")
        self.assertEqual(color, btcmesh_server_gui.COLOR_ERROR)

    def test_get_log_color_returns_error_for_abort_keyword(self):
        """Given INFO level with 'abort' keyword, Then get_log_color should return COLOR_ERROR."""
        import btcmesh_server_gui
        import logging

        color = btcmesh_server_gui.get_log_color(logging.INFO, "Session aborted by user")
        self.assertEqual(color, btcmesh_server_gui.COLOR_ERROR)

    def test_get_log_color_returns_error_for_closing_keyword(self):
        """Given INFO level with 'closing' keyword, Then get_log_color should return COLOR_ERROR."""
        import btcmesh_server_gui
        import logging

        color = btcmesh_server_gui.get_log_color(logging.INFO, "Closing Meshtastic interface")
        self.assertEqual(color, btcmesh_server_gui.COLOR_ERROR)

    def test_get_log_color_returns_success_for_successfully_keyword(self):
        """Given INFO level with 'successfully' keyword, Then get_log_color should return COLOR_SUCCESS."""
        import btcmesh_server_gui
        import logging

        color = btcmesh_server_gui.get_log_color(logging.INFO, "Meshtastic initialized successfully")
        self.assertEqual(color, btcmesh_server_gui.COLOR_SUCCESS)

    def test_get_log_color_returns_success_for_txid_keyword(self):
        """Given INFO level with 'txid:' keyword, Then get_log_color should return COLOR_SUCCESS."""
        import btcmesh_server_gui
        import logging

        color = btcmesh_server_gui.get_log_color(logging.INFO, "Broadcast success. TXID: abc123")
        self.assertEqual(color, btcmesh_server_gui.COLOR_SUCCESS)

    def test_on_clear_pressed_clears_log(self):
        """Given log has messages, When clear button pressed, Then log should be cleared."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui.status_log.clear = unittest.mock.MagicMock()
            gui.status_log.add_message = unittest.mock.MagicMock()
            gui.on_clear_pressed(None)
        gui.status_log.clear.assert_called_once()

    def test_btc_tx_chunk_message_color(self):
        """Given INFO level message about BTC_TX chunk, Then it should be normal color (not highlighted as error)."""
        import btcmesh_server_gui
        import logging

        # BTC_TX chunk messages are normal info messages per log_color_spec.md
        color = btcmesh_server_gui.get_log_color(logging.INFO, "Potential BTC transaction chunk from !abcdef12. Processing...")
        # Should be None (default white) since it's not a success or error keyword
        self.assertIsNone(color)

    def test_log_parses_and_displays_connection_events(self):
        """Given log result with connection message, Then status should be updated and message displayed."""
        import btcmesh_server_gui
        import logging

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui.status_log.add_message = unittest.mock.MagicMock()
            # Simulate log message that triggers status update
            gui._handle_result(('log', 'Connected to Bitcoin Core RPC node successfully. Host: localhost:8332, Tor: False, Chain: main', logging.INFO))
        # Verify message was added to log with success color (message contains 'successfully')
        gui.status_log.add_message.assert_called()
        call_args = gui.status_log.add_message.call_args
        message = call_args[0][0]
        color = call_args[0][1]
        self.assertIn('Connected to Bitcoin Core', message)
        self.assertEqual(color, btcmesh_server_gui.COLOR_SUCCESS)


class TestSaveLoadSettingsStory184(unittest.TestCase):
    """Tests for Story 18.4: Save and Load Settings.

    Verifies:
    - GUI has Save Settings button
    - Settings are saved to .env file
    - Existing content is preserved
    - Auto-detect device is handled properly
    - Backup is created before saving
    - Button is disabled when server is running
    """

    def setUp(self):
        """Set up test fixtures."""
        if 'core.gui_common' in sys.modules:
            del sys.modules['core.gui_common']
        if 'btcmesh_server_gui' in sys.modules:
            del sys.modules['btcmesh_server_gui']

    def test_gui_has_save_button(self):
        """Given server GUI, Then it should have save_btn attribute."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertTrue(hasattr(gui, 'save_btn'))

    def test_save_button_initially_enabled(self):
        """Given server GUI just started, Then save button should be enabled."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertFalse(gui.save_btn.disabled)

    def test_save_button_disabled_when_server_starts(self):
        """Given server starts, Then save button should be disabled."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            with unittest.mock.patch.object(btcmesh_server_gui, 'threading'):
                gui = btcmesh_server_gui.BTCMeshServerGUI()
                gui.rpc_host_input.text = 'localhost'
                gui.rpc_port_input.text = '8332'
                gui.rpc_user_input.text = 'user'
                gui.rpc_password_input.text = 'password'
                gui.on_start_pressed(None)
        self.assertTrue(gui.save_btn.disabled)

    def test_save_button_enabled_when_server_stops(self):
        """Given server stops, Then save button should be re-enabled."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui.save_btn.disabled = True
            gui._handle_result(('server_stopped', None))
        self.assertFalse(gui.save_btn.disabled)

    def test_save_button_enabled_on_meshtastic_failure(self):
        """Given meshtastic fails, Then save button should be re-enabled."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui.save_btn.disabled = True
            gui._handle_result(('meshtastic_failed', 'No device found'))
        self.assertFalse(gui.save_btn.disabled)

    def test_save_button_enabled_on_init_error(self):
        """Given init error occurs, Then save button should be re-enabled."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui.save_btn.disabled = True
            gui._handle_result(('init_error', 'Some error'))
        self.assertFalse(gui.save_btn.disabled)

    def test_save_settings_writes_to_env_file(self):
        """Given settings are filled, When save is clicked, Then .env file is written."""
        import btcmesh_server_gui
        import tempfile
        import os

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui.rpc_host_input.text = 'testhost.local'
            gui.rpc_port_input.text = '18332'
            gui.rpc_user_input.text = 'testuser'
            gui.rpc_password_input.text = 'testpass'
            gui.timeout_input.text = '120'
            gui.device_spinner.text = '/dev/ttyUSB0'

            # Mock the .env path to a temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
                temp_path = f.name

            try:
                with unittest.mock.patch.object(btcmesh_server_gui, 'DOTENV_PATH', temp_path):
                    gui.status_log.add_message = unittest.mock.MagicMock()
                    gui._on_save_settings(None)

                # Read and verify content
                with open(temp_path, 'r') as f:
                    content = f.read()

                self.assertIn('BITCOIN_RPC_HOST=testhost.local', content)
                self.assertIn('BITCOIN_RPC_PORT=18332', content)
                self.assertIn('BITCOIN_RPC_USER=testuser', content)
                self.assertIn('BITCOIN_RPC_PASSWORD=testpass', content)
                self.assertIn('REASSEMBLY_TIMEOUT_SECONDS=120', content)
                self.assertIn('MESHTASTIC_SERIAL_PORT=/dev/ttyUSB0', content)

                # Verify success message was shown
                gui.status_log.add_message.assert_called()
            finally:
                os.unlink(temp_path)

    def test_save_settings_shows_confirmation_message(self):
        """Given save succeeds, Then confirmation message should be displayed."""
        import btcmesh_server_gui
        import tempfile
        import os

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui.rpc_host_input.text = 'localhost'
            gui.rpc_port_input.text = '8332'
            gui.rpc_user_input.text = 'user'
            gui.rpc_password_input.text = 'pass'
            gui.timeout_input.text = '300'

            with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
                temp_path = f.name

            try:
                with unittest.mock.patch.object(btcmesh_server_gui, 'DOTENV_PATH', temp_path):
                    gui.status_log.add_message = unittest.mock.MagicMock()
                    gui._on_save_settings(None)

                # Check that success message was shown
                calls = gui.status_log.add_message.call_args_list
                messages = [call[0][0] for call in calls]
                self.assertTrue(any('saved' in msg.lower() for msg in messages))
            finally:
                os.unlink(temp_path)

    def test_save_settings_preserves_comments(self):
        """Given .env has comments, When save is clicked, Then comments are preserved."""
        import btcmesh_server_gui
        import tempfile
        import os

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui.rpc_host_input.text = 'localhost'
            gui.rpc_port_input.text = '8332'
            gui.rpc_user_input.text = 'user'
            gui.rpc_password_input.text = 'pass'
            gui.timeout_input.text = '300'

            with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
                # Write initial content with comments
                f.write("# This is a comment\n")
                f.write("BITCOIN_RPC_HOST=oldhost\n")
                f.write("# Another comment\n")
                f.write("SOME_OTHER_VAR=keepme\n")
                temp_path = f.name

            try:
                with unittest.mock.patch.object(btcmesh_server_gui, 'DOTENV_PATH', temp_path):
                    gui.status_log.add_message = unittest.mock.MagicMock()
                    gui._on_save_settings(None)

                with open(temp_path, 'r') as f:
                    content = f.read()

                # Comments should be preserved
                self.assertIn('# This is a comment', content)
                self.assertIn('# Another comment', content)
                # Other variables should be preserved
                self.assertIn('SOME_OTHER_VAR=keepme', content)
                # Value should be updated
                self.assertIn('BITCOIN_RPC_HOST=localhost', content)
                self.assertNotIn('BITCOIN_RPC_HOST=oldhost', content)
            finally:
                os.unlink(temp_path)
                # Clean up backup if created
                if os.path.exists(temp_path + '.bak'):
                    os.unlink(temp_path + '.bak')

    def test_save_settings_creates_backup(self):
        """Given .env exists, When save is clicked, Then .env.bak backup is created."""
        import btcmesh_server_gui
        import tempfile
        import os

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui.rpc_host_input.text = 'localhost'
            gui.rpc_port_input.text = '8332'
            gui.rpc_user_input.text = 'user'
            gui.rpc_password_input.text = 'pass'
            gui.timeout_input.text = '300'

            with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
                f.write("BITCOIN_RPC_HOST=original\n")
                temp_path = f.name

            try:
                with unittest.mock.patch.object(btcmesh_server_gui, 'DOTENV_PATH', temp_path):
                    gui.status_log.add_message = unittest.mock.MagicMock()
                    gui._on_save_settings(None)

                # Backup should exist
                backup_path = temp_path + '.bak'
                self.assertTrue(os.path.exists(backup_path))

                # Backup should contain original content
                with open(backup_path, 'r') as f:
                    backup_content = f.read()
                self.assertIn('BITCOIN_RPC_HOST=original', backup_content)
            finally:
                os.unlink(temp_path)
                if os.path.exists(temp_path + '.bak'):
                    os.unlink(temp_path + '.bak')

    def test_save_settings_auto_detect_removes_device_setting(self):
        """Given Auto-detect is selected, Then MESHTASTIC_SERIAL_PORT should be removed."""
        import btcmesh_server_gui
        import tempfile
        import os

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui.rpc_host_input.text = 'localhost'
            gui.rpc_port_input.text = '8332'
            gui.rpc_user_input.text = 'user'
            gui.rpc_password_input.text = 'pass'
            gui.timeout_input.text = '300'
            gui.device_spinner.text = btcmesh_server_gui.DEVICE_AUTO_DETECT

            with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
                # File has an existing device setting
                f.write("MESHTASTIC_SERIAL_PORT=/dev/ttyOLD\n")
                f.write("BITCOIN_RPC_HOST=oldhost\n")
                temp_path = f.name

            try:
                with unittest.mock.patch.object(btcmesh_server_gui, 'DOTENV_PATH', temp_path):
                    gui.status_log.add_message = unittest.mock.MagicMock()
                    gui._on_save_settings(None)

                with open(temp_path, 'r') as f:
                    content = f.read()

                # Device setting should be removed
                self.assertNotIn('MESHTASTIC_SERIAL_PORT', content)
                # Other settings should be present
                self.assertIn('BITCOIN_RPC_HOST=localhost', content)
            finally:
                os.unlink(temp_path)
                if os.path.exists(temp_path + '.bak'):
                    os.unlink(temp_path + '.bak')

    def test_save_settings_shows_password_warning(self):
        """Given password is set, When save succeeds, Then warning about plain text is shown."""
        import btcmesh_server_gui
        import tempfile
        import os

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui.rpc_host_input.text = 'localhost'
            gui.rpc_port_input.text = '8332'
            gui.rpc_user_input.text = 'user'
            gui.rpc_password_input.text = 'secretpassword'
            gui.timeout_input.text = '300'

            with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
                temp_path = f.name

            try:
                with unittest.mock.patch.object(btcmesh_server_gui, 'DOTENV_PATH', temp_path):
                    gui.status_log.add_message = unittest.mock.MagicMock()
                    gui._on_save_settings(None)

                # Check that warning about plain text password was shown
                calls = gui.status_log.add_message.call_args_list
                messages = [call[0][0] for call in calls]
                self.assertTrue(any('plain text' in msg.lower() for msg in messages))
            finally:
                os.unlink(temp_path)

    def test_save_settings_handles_permission_error(self):
        """Given .env is not writable, When save is clicked, Then error message is shown."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
            gui.rpc_host_input.text = 'localhost'
            gui.rpc_port_input.text = '8332'
            gui.rpc_user_input.text = 'user'
            gui.rpc_password_input.text = 'pass'
            gui.timeout_input.text = '300'

            # Mock open to raise PermissionError
            with unittest.mock.patch.object(btcmesh_server_gui, 'DOTENV_PATH', '/nonexistent/path/.env'):
                with unittest.mock.patch('builtins.open', side_effect=PermissionError("Permission denied")):
                    gui.status_log.add_message = unittest.mock.MagicMock()
                    gui._on_save_settings(None)

            # Check that error message was shown
            calls = gui.status_log.add_message.call_args_list
            messages = [call[0][0] for call in calls]
            colors = [call[0][1] for call in calls]
            self.assertTrue(any('permission' in msg.lower() for msg in messages))
            self.assertIn(btcmesh_server_gui.COLOR_ERROR, colors)

    def test_settings_loaded_on_startup(self):
        """Given .env has settings, When GUI starts, Then settings are loaded."""
        import btcmesh_server_gui
        import os

        # This test verifies the existing behavior - settings are loaded from env vars
        # which are populated by load_app_config() from .env file
        original_host = os.environ.get('BITCOIN_RPC_HOST')
        os.environ['BITCOIN_RPC_HOST'] = 'loaded-from-env.local'

        try:
            with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
                gui = btcmesh_server_gui.BTCMeshServerGUI()
            # Verify the value was loaded
            self.assertEqual(gui.rpc_host_input.text, 'loaded-from-env.local')
        finally:
            if original_host is None:
                os.environ.pop('BITCOIN_RPC_HOST', None)
            else:
                os.environ['BITCOIN_RPC_HOST'] = original_host


class TestActiveSessionsDisplayStory172(unittest.TestCase):
    """Tests for Active Sessions Display in Story 17.2."""

    def setUp(self):
        """Set up test fixtures."""
        if 'core.gui_common' in sys.modules:
            del sys.modules['core.gui_common']
        if 'btcmesh_server_gui' in sys.modules:
            del sys.modules['btcmesh_server_gui']

    def test_gui_has_sessions_container(self):
        """Given server GUI, Then it should have sessions_container attribute."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertTrue(hasattr(gui, 'sessions_container'))

    def test_gui_has_sessions_scroll(self):
        """Given server GUI, Then it should have sessions_scroll ScrollView attribute."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertTrue(hasattr(gui, 'sessions_scroll'))
        # ScrollView should have fixed height of 85 (fits ~3 sessions)
        self.assertEqual(gui.sessions_scroll.height, 85)

    def test_gui_has_session_count_label(self):
        """Given server GUI, Then it should have session_count_label always visible."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertTrue(hasattr(gui, 'session_count_label'))
        self.assertEqual(gui.session_count_label.text, '0 active sessions')

    def test_session_count_updates_with_sessions(self):
        """Given sessions, When _update_active_sessions called, Then count label updates."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()

        # Update with 1 session
        sessions = [{'session_id': 'abc12', 'sender': '!12345678',
                    'chunks_received': 2, 'total_chunks': 5, 'elapsed_seconds': 10}]
        gui._update_active_sessions(sessions)
        self.assertEqual(gui.session_count_label.text, '1 active session')

        # Update with 3 sessions
        sessions = [
            {'session_id': 'abc12', 'sender': '!12345678', 'chunks_received': 2, 'total_chunks': 5, 'elapsed_seconds': 10},
            {'session_id': 'def34', 'sender': '!87654321', 'chunks_received': 1, 'total_chunks': 3, 'elapsed_seconds': 5},
            {'session_id': 'ghi56', 'sender': '!abcdef00', 'chunks_received': 4, 'total_chunks': 8, 'elapsed_seconds': 20},
        ]
        gui._update_active_sessions(sessions)
        self.assertEqual(gui.session_count_label.text, '3 active sessions')

        # Update with 0 sessions
        gui._update_active_sessions([])
        self.assertEqual(gui.session_count_label.text, '0 active sessions')

    def test_gui_has_no_sessions_label(self):
        """Given server GUI, Then it should have no_sessions_label attribute."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertTrue(hasattr(gui, 'no_sessions_label'))
        self.assertEqual(gui.no_sessions_label.text, 'No active sessions')

    def test_gui_has_session_widgets_dict(self):
        """Given server GUI, Then it should have _session_widgets dict."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertTrue(hasattr(gui, '_session_widgets'))
        self.assertIsInstance(gui._session_widgets, dict)
        self.assertEqual(len(gui._session_widgets), 0)

    def test_gui_has_update_active_sessions_method(self):
        """Given server GUI, Then it should have _update_active_sessions method."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()
        self.assertTrue(hasattr(gui, '_update_active_sessions'))
        self.assertTrue(callable(gui._update_active_sessions))

    def test_update_active_sessions_with_empty_list_shows_no_sessions(self):
        """Given empty sessions list, When _update_active_sessions called, Then no_sessions_label is shown."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()

        # Update with empty list
        gui._update_active_sessions([])

        # Verify no_sessions_label is shown
        self.assertIsNotNone(gui.no_sessions_label.parent)
        self.assertEqual(len(gui._session_widgets), 0)

    def test_update_active_sessions_with_sessions_creates_widgets(self):
        """Given sessions list, When _update_active_sessions called, Then session widgets are created."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()

        sessions = [
            {
                'session_id': 'abc12',
                'sender': '!deadbeef',
                'chunks_received': 2,
                'total_chunks': 5,
                'elapsed_seconds': 10.5
            }
        ]
        gui._update_active_sessions(sessions)

        # Verify session widget was created
        self.assertIn('abc12', gui._session_widgets)
        self.assertIsNone(gui.no_sessions_label.parent)

    def test_update_active_sessions_updates_existing_widget(self):
        """Given existing session, When _update_active_sessions called again, Then widget is updated."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()

        # First update
        sessions1 = [
            {
                'session_id': 'abc12',
                'sender': '!deadbeef',
                'chunks_received': 2,
                'total_chunks': 5,
                'elapsed_seconds': 10.0
            }
        ]
        gui._update_active_sessions(sessions1)
        widget1 = gui._session_widgets['abc12']

        # Second update with progress
        sessions2 = [
            {
                'session_id': 'abc12',
                'sender': '!deadbeef',
                'chunks_received': 3,
                'total_chunks': 5,
                'elapsed_seconds': 15.0
            }
        ]
        gui._update_active_sessions(sessions2)

        # Same widget should be updated
        self.assertIs(gui._session_widgets['abc12'], widget1)
        self.assertIn('3/5', widget1.text)

    def test_update_active_sessions_removes_completed_sessions(self):
        """Given session no longer in list, When _update_active_sessions called, Then widget is removed."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()

        # First update with two sessions
        sessions1 = [
            {'session_id': 'abc12', 'sender': '!deadbeef', 'chunks_received': 2, 'total_chunks': 5, 'elapsed_seconds': 10.0},
            {'session_id': 'xyz99', 'sender': '!cafebabe', 'chunks_received': 1, 'total_chunks': 3, 'elapsed_seconds': 5.0}
        ]
        gui._update_active_sessions(sessions1)
        self.assertEqual(len(gui._session_widgets), 2)

        # Second update with only one session (abc12 completed)
        sessions2 = [
            {'session_id': 'xyz99', 'sender': '!cafebabe', 'chunks_received': 2, 'total_chunks': 3, 'elapsed_seconds': 8.0}
        ]
        gui._update_active_sessions(sessions2)

        # Only xyz99 should remain
        self.assertEqual(len(gui._session_widgets), 1)
        self.assertNotIn('abc12', gui._session_widgets)
        self.assertIn('xyz99', gui._session_widgets)

    def test_handle_result_active_sessions_calls_update(self):
        """Given 'active_sessions' result type, When _handle_result called, Then _update_active_sessions is called."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()

        sessions = [
            {'session_id': 'test1', 'sender': '!12345678', 'chunks_received': 1, 'total_chunks': 2, 'elapsed_seconds': 3.0}
        ]

        # Call _handle_result directly
        gui._handle_result(('active_sessions', sessions))

        # Verify session widget was created
        self.assertIn('test1', gui._session_widgets)

    def test_server_stopped_clears_active_sessions(self):
        """Given active sessions, When server_stopped status received, Then sessions are cleared."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()

        # Set up some sessions
        sessions = [
            {'session_id': 'abc12', 'sender': '!deadbeef', 'chunks_received': 2, 'total_chunks': 5, 'elapsed_seconds': 10.0}
        ]
        gui._update_active_sessions(sessions)
        self.assertEqual(len(gui._session_widgets), 1)

        # Apply server_stopped status
        gui._apply_status_update(('server_stopped', None))

        # Sessions should be cleared
        self.assertEqual(len(gui._session_widgets), 0)
        self.assertIsNotNone(gui.no_sessions_label.parent)

    def test_session_display_format(self):
        """Given session info, When widget created, Then text format is correct."""
        import btcmesh_server_gui

        with unittest.mock.patch.object(btcmesh_server_gui, 'Clock'):
            gui = btcmesh_server_gui.BTCMeshServerGUI()

        sessions = [
            {
                'session_id': 'test1',
                'sender': '!abcdef12',
                'chunks_received': 3,
                'total_chunks': 7,
                'elapsed_seconds': 45.0
            }
        ]
        gui._update_active_sessions(sessions)

        widget = gui._session_widgets['test1']
        # Check key parts are in the text
        self.assertIn('test1', widget.text)
        self.assertIn('3/7', widget.text)
        self.assertIn('45s', widget.text)


class TestReassemblerGetActiveSessionsInfo(unittest.TestCase):
    """Tests for TransactionReassembler.get_active_sessions_info method."""

    def test_get_active_sessions_info_empty(self):
        """Given no active sessions, When get_active_sessions_info called, Then empty list returned."""
        from core.reassembler import TransactionReassembler

        reassembler = TransactionReassembler(timeout_seconds=60)
        result = reassembler.get_active_sessions_info()

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_get_active_sessions_info_with_session(self):
        """Given active session, When get_active_sessions_info called, Then session info returned."""
        from core.reassembler import TransactionReassembler

        reassembler = TransactionReassembler(timeout_seconds=60)

        # Add a chunk to create a session
        reassembler.add_chunk('!sender123', 'BTC_TX|sess1|1/3|aabbccdd')

        result = reassembler.get_active_sessions_info()

        self.assertEqual(len(result), 1)
        session_info = result[0]
        self.assertEqual(session_info['session_id'], 'sess1')
        self.assertEqual(session_info['sender'], '!sender123')
        self.assertEqual(session_info['chunks_received'], 1)
        self.assertEqual(session_info['total_chunks'], 3)
        self.assertIsInstance(session_info['elapsed_seconds'], float)

    def test_get_active_sessions_info_multiple_sessions(self):
        """Given multiple active sessions, When get_active_sessions_info called, Then all sessions returned."""
        from core.reassembler import TransactionReassembler

        reassembler = TransactionReassembler(timeout_seconds=60)

        # Add chunks to create multiple sessions
        reassembler.add_chunk('!sender1', 'BTC_TX|sessA|1/2|aabb')
        reassembler.add_chunk('!sender2', 'BTC_TX|sessB|1/3|ccdd')

        result = reassembler.get_active_sessions_info()

        self.assertEqual(len(result), 2)
        session_ids = {s['session_id'] for s in result}
        self.assertIn('sessA', session_ids)
        self.assertIn('sessB', session_ids)


if __name__ == '__main__':
    unittest.main()
