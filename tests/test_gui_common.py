#!/usr/bin/env python3
"""
Tests for BTCMesh GUI Common Components (gui_common.py).

Tests shared UI components, color constants, and helper functions
used by both client and server GUIs.
"""
import sys
import unittest
import unittest.mock
import logging


# Mock Kivy modules before importing gui_common
# This allows tests to run in environments without Kivy installed.

class MockCanvas:
    """Mock canvas for Kivy widgets - acts as context manager."""
    def __init__(self):
        self.before = self  # self-referential for canvas.before

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class MockBoxLayout:
    """Mock base class for BoxLayout."""
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


kivy_mock = unittest.mock.MagicMock()
# get_color_from_hex should return a tuple like (r, g, b, a)
kivy_mock.get_color_from_hex = lambda hex_str: (1.0, 0.42, 0.0, 1.0)  # Return consistent tuple

boxlayout_mock = unittest.mock.MagicMock()
boxlayout_mock.BoxLayout = MockBoxLayout

scrollview_mock = unittest.mock.MagicMock()
scrollview_mock.ScrollView = MockScrollView

widget_mock = unittest.mock.MagicMock()
widget_mock.Widget = MockWidget


class MockTextInput:
    """Mock base class for TextInput that properly stores password attribute."""
    def __init__(self, **kwargs):
        self.text = kwargs.get('text', '')
        self.hint_text = kwargs.get('hint_text', '')
        self.password = kwargs.get('password', False)
        self.multiline = kwargs.get('multiline', True)
        self.size_hint_x = kwargs.get('size_hint_x', 1)
        self.background_color = kwargs.get('background_color', (1, 1, 1, 1))
        self.foreground_color = kwargs.get('foreground_color', (0, 0, 0, 1))
        self.cursor_color = kwargs.get('cursor_color', (0, 0, 0, 1))
        self.input_filter = kwargs.get('input_filter', None)

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


class MockButton:
    """Mock base class for Button that properly stores text attribute."""
    def __init__(self, **kwargs):
        self.text = kwargs.get('text', '')
        self.size_hint_x = kwargs.get('size_hint_x', 1)
        self.size_hint_y = kwargs.get('size_hint_y', 1)
        self.width = kwargs.get('width', 100)
        self.height = kwargs.get('height', 100)
        self.background_color = kwargs.get('background_color', (1, 1, 1, 1))
        self.background_normal = kwargs.get('background_normal', '')
        self.font_size = kwargs.get('font_size', '14sp')
        self.bold = kwargs.get('bold', False)
        self.disabled = kwargs.get('disabled', False)

    def bind(self, **kwargs):
        pass


textinput_mock = unittest.mock.MagicMock()
textinput_mock.TextInput = MockTextInput

button_mock = unittest.mock.MagicMock()
button_mock.Button = MockButton

label_mock = unittest.mock.MagicMock()
label_mock.Label = MockLabel

sys.modules['kivy'] = kivy_mock
sys.modules['kivy.uix'] = kivy_mock
sys.modules['kivy.uix.boxlayout'] = boxlayout_mock
sys.modules['kivy.uix.widget'] = widget_mock
sys.modules['kivy.uix.label'] = label_mock
sys.modules['kivy.uix.button'] = button_mock
sys.modules['kivy.uix.textinput'] = textinput_mock
sys.modules['kivy.uix.scrollview'] = scrollview_mock
sys.modules['kivy.graphics'] = kivy_mock
sys.modules['kivy.clock'] = kivy_mock
sys.modules['kivy.core'] = kivy_mock
sys.modules['kivy.core.window'] = kivy_mock
sys.modules['kivy.utils'] = kivy_mock


# =============================================================================
# Tests for Color Constants
# =============================================================================

class TestColorConstants(unittest.TestCase):
    """Tests for color constants defined in gui_common."""

    def test_color_primary_exists(self):
        """Given gui_common module, Then COLOR_PRIMARY should be defined."""
        from core import gui_common
        self.assertTrue(hasattr(gui_common, 'COLOR_PRIMARY'))

    def test_color_success_exists(self):
        """Given gui_common module, Then COLOR_SUCCESS should be defined."""
        from core import gui_common
        self.assertTrue(hasattr(gui_common, 'COLOR_SUCCESS'))

    def test_color_error_exists(self):
        """Given gui_common module, Then COLOR_ERROR should be defined."""
        from core import gui_common
        self.assertTrue(hasattr(gui_common, 'COLOR_ERROR'))

    def test_color_warning_exists(self):
        """Given gui_common module, Then COLOR_WARNING should be defined."""
        from core import gui_common
        self.assertTrue(hasattr(gui_common, 'COLOR_WARNING'))

    def test_color_bg_exists(self):
        """Given gui_common module, Then COLOR_BG should be defined."""
        from core import gui_common
        self.assertTrue(hasattr(gui_common, 'COLOR_BG'))

    def test_color_bg_light_exists(self):
        """Given gui_common module, Then COLOR_BG_LIGHT should be defined."""
        from core import gui_common
        self.assertTrue(hasattr(gui_common, 'COLOR_BG_LIGHT'))

    def test_color_secundary_exists(self):
        """Given gui_common module, Then COLOR_SECUNDARY should be defined."""
        from core import gui_common
        self.assertTrue(hasattr(gui_common, 'COLOR_SECUNDARY'))

    def test_color_disconnected_exists(self):
        """Given gui_common module, Then COLOR_DISCONNECTED should be defined."""
        from core import gui_common
        self.assertTrue(hasattr(gui_common, 'COLOR_DISCONNECTED'))

    def test_color_disconnected_is_gray(self):
        """Given COLOR_DISCONNECTED, Then it should be a gray color tuple."""
        from core import gui_common
        self.assertEqual(gui_common.COLOR_DISCONNECTED, (0.7, 0.7, 0.7, 1))


# =============================================================================
# Tests for ConnectionState Dataclass
# =============================================================================

class TestConnectionState(unittest.TestCase):
    """Tests for ConnectionState dataclass."""

    def test_connection_state_exists(self):
        """Given gui_common module, Then ConnectionState should be defined."""
        from core import gui_common
        self.assertTrue(hasattr(gui_common, 'ConnectionState'))

    def test_connection_state_has_text_attribute(self):
        """Given ConnectionState, Then it should have a text attribute."""
        from core import gui_common
        state = gui_common.ConnectionState(text='Test', color=(1, 1, 1, 1))
        self.assertEqual(state.text, 'Test')

    def test_connection_state_has_color_attribute(self):
        """Given ConnectionState, Then it should have a color attribute."""
        from core import gui_common
        state = gui_common.ConnectionState(text='Test', color=(0.5, 0.5, 0.5, 1))
        self.assertEqual(state.color, (0.5, 0.5, 0.5, 1))

    def test_connection_state_is_frozen(self):
        """Given ConnectionState, Then it should be immutable (frozen)."""
        from core import gui_common
        state = gui_common.ConnectionState(text='Test', color=(1, 1, 1, 1))
        with self.assertRaises(AttributeError):
            state.text = 'New Text'


# =============================================================================
# Tests for get_log_color Function
# =============================================================================

class TestGetLogColor(unittest.TestCase):
    """Tests for get_log_color helper function."""

    def test_get_log_color_exists(self):
        """Given gui_common module, Then get_log_color should be defined."""
        from core import gui_common
        self.assertTrue(hasattr(gui_common, 'get_log_color'))
        self.assertTrue(callable(gui_common.get_log_color))

    def test_get_log_color_returns_error_for_error_level(self):
        """Given ERROR log level, Then get_log_color should return COLOR_ERROR."""
        from core import gui_common
        color = gui_common.get_log_color(logging.ERROR, "Some error")
        self.assertEqual(color, gui_common.COLOR_ERROR)

    def test_get_log_color_returns_error_for_critical_level(self):
        """Given CRITICAL log level, Then get_log_color should return COLOR_ERROR."""
        from core import gui_common
        color = gui_common.get_log_color(logging.CRITICAL, "Critical error")
        self.assertEqual(color, gui_common.COLOR_ERROR)

    def test_get_log_color_returns_warning_for_warning_level(self):
        """Given WARNING log level, Then get_log_color should return COLOR_WARNING."""
        from core import gui_common
        color = gui_common.get_log_color(logging.WARNING, "Some warning")
        self.assertEqual(color, gui_common.COLOR_WARNING)

    def test_get_log_color_returns_success_for_success_keyword(self):
        """Given INFO level with 'success' in message, Then return COLOR_SUCCESS."""
        from core import gui_common
        color = gui_common.get_log_color(logging.INFO, "Operation success")
        self.assertEqual(color, gui_common.COLOR_SUCCESS)

    def test_get_log_color_returns_success_for_txid_keyword(self):
        """Given INFO level with 'txid:' in message, Then return COLOR_SUCCESS."""
        from core import gui_common
        color = gui_common.get_log_color(logging.INFO, "Broadcast success. TXID: abc123")
        self.assertEqual(color, gui_common.COLOR_SUCCESS)

    def test_get_log_color_returns_success_for_successfully_keyword(self):
        """Given INFO level with 'successfully' in message, Then return COLOR_SUCCESS."""
        from core import gui_common
        color = gui_common.get_log_color(logging.INFO, "Connected successfully")
        self.assertEqual(color, gui_common.COLOR_SUCCESS)

    def test_get_log_color_returns_error_for_failed_keyword_at_info(self):
        """Given INFO level with 'failed' in message, Then return COLOR_ERROR."""
        from core import gui_common
        color = gui_common.get_log_color(logging.INFO, "Broadcast failed: some error")
        self.assertEqual(color, gui_common.COLOR_ERROR)

    def test_get_log_color_returns_error_for_nack_keyword_at_info(self):
        """Given INFO level with 'nack' in message, Then return COLOR_ERROR."""
        from core import gui_common
        color = gui_common.get_log_color(logging.INFO, "Sending NACK to client")
        self.assertEqual(color, gui_common.COLOR_ERROR)

    def test_get_log_color_returns_error_for_timeout_keyword_at_info(self):
        """Given INFO level with 'timed out' in message, Then return COLOR_ERROR."""
        from core import gui_common
        color = gui_common.get_log_color(logging.INFO, "Session timed out. Sending NACK")
        self.assertEqual(color, gui_common.COLOR_ERROR)

    def test_get_log_color_returns_error_for_closing_keyword_at_info(self):
        """Given INFO level with 'closing' in message, Then return COLOR_ERROR."""
        from core import gui_common
        color = gui_common.get_log_color(logging.INFO, "Closing Meshtastic interface...")
        self.assertEqual(color, gui_common.COLOR_ERROR)

    def test_get_log_color_returns_error_for_cannot_keyword_at_info(self):
        """Given INFO level with 'cannot' in message, Then return COLOR_ERROR."""
        from core import gui_common
        color = gui_common.get_log_color(logging.INFO, "Cannot send reply: no interface")
        self.assertEqual(color, gui_common.COLOR_ERROR)

    def test_get_log_color_returns_error_for_abort_keyword_at_info(self):
        """Given INFO level with 'abort' in message, Then return COLOR_ERROR."""
        from core import gui_common
        color = gui_common.get_log_color(logging.INFO, "Session aborted by sender")
        self.assertEqual(color, gui_common.COLOR_ERROR)

    def test_get_log_color_error_keywords_take_priority_over_success(self):
        """Given message with both error and success keywords, Then error takes priority."""
        from core import gui_common
        # 'failed' is error keyword, 'success' would be success keyword
        color = gui_common.get_log_color(logging.INFO, "Success check failed")
        self.assertEqual(color, gui_common.COLOR_ERROR)

    def test_get_log_color_with_custom_error_keywords(self):
        """Given custom error keywords, Then use those for matching."""
        from core import gui_common
        color = gui_common.get_log_color(
            logging.INFO, "Connection dropped",
            error_keywords=['dropped']
        )
        self.assertEqual(color, gui_common.COLOR_ERROR)

    def test_get_log_color_returns_none_for_normal_info(self):
        """Given INFO level with normal message, Then return None."""
        from core import gui_common
        color = gui_common.get_log_color(logging.INFO, "Normal info message")
        self.assertIsNone(color)

    def test_get_log_color_with_custom_success_keywords(self):
        """Given custom success keywords, Then use those for matching."""
        from core import gui_common
        # Default keywords don't include 'complete'
        color = gui_common.get_log_color(logging.INFO, "Task complete", success_keywords=['complete'])
        self.assertEqual(color, gui_common.COLOR_SUCCESS)

    def test_get_log_color_case_insensitive(self):
        """Given message with mixed case, Then matching should be case-insensitive."""
        from core import gui_common
        color = gui_common.get_log_color(logging.INFO, "SUCCESS message")
        self.assertEqual(color, gui_common.COLOR_SUCCESS)


# =============================================================================
# Tests for get_print_color Function
# =============================================================================

class TestGetPrintColor(unittest.TestCase):
    """Tests for get_print_color helper function."""

    def test_get_print_color_exists(self):
        """Given gui_common module, Then get_print_color should be defined."""
        from core import gui_common
        self.assertTrue(hasattr(gui_common, 'get_print_color'))
        self.assertTrue(callable(gui_common.get_print_color))

    def test_get_print_color_returns_error_for_error_keyword(self):
        """Given message with 'error', Then return COLOR_ERROR."""
        from core import gui_common
        color = gui_common.get_print_color("Error occurred")
        self.assertEqual(color, gui_common.COLOR_ERROR)

    def test_get_print_color_returns_error_for_failed_keyword(self):
        """Given message with 'failed', Then return COLOR_ERROR."""
        from core import gui_common
        color = gui_common.get_print_color("Connection failed")
        self.assertEqual(color, gui_common.COLOR_ERROR)

    def test_get_print_color_returns_error_for_abort_keyword(self):
        """Given message with 'abort', Then return COLOR_ERROR."""
        from core import gui_common
        color = gui_common.get_print_color("User abort")
        self.assertEqual(color, gui_common.COLOR_ERROR)

    def test_get_print_color_returns_success_for_success_keyword(self):
        """Given message with 'success', Then return COLOR_SUCCESS."""
        from core import gui_common
        color = gui_common.get_print_color("Operation success")
        self.assertEqual(color, gui_common.COLOR_SUCCESS)

    def test_get_print_color_returns_success_for_txid_keyword(self):
        """Given message with 'txid', Then return COLOR_SUCCESS."""
        from core import gui_common
        color = gui_common.get_print_color("TXID: abc123def456")
        self.assertEqual(color, gui_common.COLOR_SUCCESS)

    def test_get_print_color_returns_none_for_normal_message(self):
        """Given normal message, Then return None."""
        from core import gui_common
        color = gui_common.get_print_color("Normal message")
        self.assertIsNone(color)


# =============================================================================
# Tests for StatusLog Class
# =============================================================================

class TestStatusLog(unittest.TestCase):
    """Tests for StatusLog widget class."""

    def test_status_log_class_exists(self):
        """Given gui_common module, Then StatusLog class should be defined."""
        from core import gui_common
        self.assertTrue(hasattr(gui_common, 'StatusLog'))


# =============================================================================
# Tests for Widget Factory Functions
# =============================================================================

class TestWidgetFactories(unittest.TestCase):
    """Tests for widget factory functions."""

    def test_create_separator_exists(self):
        """Given gui_common module, Then create_separator should be defined."""
        from core import gui_common
        self.assertTrue(hasattr(gui_common, 'create_separator'))
        self.assertTrue(callable(gui_common.create_separator))

    def test_create_title_exists(self):
        """Given gui_common module, Then create_title should be defined."""
        from core import gui_common
        self.assertTrue(hasattr(gui_common, 'create_title'))
        self.assertTrue(callable(gui_common.create_title))

    def test_create_section_label_exists(self):
        """Given gui_common module, Then create_section_label should be defined."""
        from core import gui_common
        self.assertTrue(hasattr(gui_common, 'create_section_label'))
        self.assertTrue(callable(gui_common.create_section_label))

    def test_create_clear_button_exists(self):
        """Given gui_common module, Then create_clear_button should be defined."""
        from core import gui_common
        self.assertTrue(hasattr(gui_common, 'create_clear_button'))
        self.assertTrue(callable(gui_common.create_clear_button))

    def test_create_action_button_exists(self):
        """Given gui_common module, Then create_action_button should be defined."""
        from core import gui_common
        self.assertTrue(hasattr(gui_common, 'create_action_button'))
        self.assertTrue(callable(gui_common.create_action_button))

    def test_create_status_row_exists(self):
        """Given gui_common module, Then create_status_row should be defined."""
        from core import gui_common
        self.assertTrue(hasattr(gui_common, 'create_status_row'))
        self.assertTrue(callable(gui_common.create_status_row))

    def test_create_status_row_returns_tuple(self):
        """Given create_status_row call, Then returns tuple of (BoxLayout, Label)."""
        from core import gui_common
        result = gui_common.create_status_row('Test:', 'Value')
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_create_status_row_returns_label_as_second_element(self):
        """Given create_status_row call, Then second element is a Label-like object."""
        from core import gui_common
        _, value_label = gui_common.create_status_row('Label:', 'Initial Value')
        # The value_label should be a Label (mocked in tests)
        # We can verify it has expected Label attributes
        self.assertTrue(hasattr(value_label, 'text'))
        self.assertTrue(hasattr(value_label, 'color'))

    def test_create_toggle_button_exists(self):
        """Given gui_common module, Then create_toggle_button should be defined."""
        from core import gui_common
        self.assertTrue(hasattr(gui_common, 'create_toggle_button'))
        self.assertTrue(callable(gui_common.create_toggle_button))

    def test_create_toggle_button_returns_button(self):
        """Given create_toggle_button call, Then returns a Button-like object."""
        from core import gui_common
        btn = gui_common.create_toggle_button('Show')
        self.assertTrue(hasattr(btn, 'text'))

    def test_create_toggle_button_uses_provided_text(self):
        """Given create_toggle_button call with text, Then button text is set correctly."""
        from core import gui_common
        btn = gui_common.create_toggle_button('Toggle')
        self.assertEqual(btn.text, 'Toggle')


if __name__ == '__main__':
    unittest.main()
