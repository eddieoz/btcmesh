#!/usr/bin/env python3
"""
BTCMesh GUI Common Components - Shared UI elements and utilities for
both client and server GUIs.

This module provides reusable Kivy widgets, color constants, and helper
functions to maintain visual consistency across BTCMesh applications.
"""
import logging
from dataclasses import dataclass
from typing import Optional, Tuple

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import get_color_from_hex


# =============================================================================
# Color Constants - Bitcoin-orange themed color scheme
# =============================================================================

COLOR_PRIMARY = get_color_from_hex('#FF6B00')    # Bitcoin orange
COLOR_SUCCESS = get_color_from_hex('#4CAF50')    # Green
COLOR_ERROR = get_color_from_hex('#F44336')      # Red
COLOR_WARNING = get_color_from_hex('#FF9800')    # Orange
COLOR_BG = get_color_from_hex('#1E1E1E')         # Dark background
COLOR_BG_LIGHT = get_color_from_hex('#2D2D2D')   # Lighter background
COLOR_SECUNDARY = get_color_from_hex("#FFFFFF")  # White text
COLOR_DISCONNECTED = (0.7, 0.7, 0.7, 1)          # Gray for disconnected

# Network badge colors
COLOR_MAINNET = get_color_from_hex('#FF6B00')    # Bitcoin orange for mainnet
COLOR_TESTNET = get_color_from_hex('#2196F3')    # Blue for testnet
COLOR_SIGNET = get_color_from_hex('#9C27B0')     # Purple for signet


# =============================================================================
# Connection State Dataclass
# =============================================================================

@dataclass(frozen=True)
class ConnectionState:
    """Represents a connection state with display text and color.

    Attributes:
        text: The display text for the connection status
        color: The color tuple (r, g, b, a) for the status display
    """
    text: str
    color: tuple


# =============================================================================
# Helper Functions
# =============================================================================

def get_log_color(level: int, msg: str,
                  success_keywords: Optional[list] = None,
                  error_keywords: Optional[list] = None) -> Optional[Tuple]:
    """Determine the color for a log message based on level and content.

    Args:
        level: The logging level (e.g., logging.ERROR, logging.WARNING, logging.INFO)
        msg: The log message text
        success_keywords: Optional list of keywords that indicate success messages.
                         Defaults to ['successfully', 'success', 'txid:']
        error_keywords: Optional list of keywords that indicate error messages at INFO level.
                       Defaults to ['failed', 'nack', 'timed out', 'abort',
                                   'cannot', 'closing']

    Returns:
        A color tuple (r, g, b, a) or None for default color

    See project/log_color_spec.md for full categorization requirements.
    """
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


def get_print_color(msg: str) -> Optional[Tuple]:
    """Determine the color for a print message based on content.

    Args:
        msg: The message text

    Returns:
        A color tuple (r, g, b, a) or None for default color
    """
    msg_lower = msg.lower()
    if 'error' in msg_lower or 'failed' in msg_lower or 'abort' in msg_lower:
        return COLOR_ERROR
    elif 'success' in msg_lower or 'txid' in msg_lower:
        return COLOR_SUCCESS
    return None


# =============================================================================
# Reusable Widget Components
# =============================================================================

class StatusLog(ScrollView):
    """Scrollable status/log area for displaying messages.

    A ScrollView-based widget that displays log messages with optional
    color coding. Messages auto-scroll to show the newest entry.

    Attributes:
        layout: The internal BoxLayout containing log message labels
    """

    def __init__(self, label_height: int = 25, **kwargs):
        """Initialize the StatusLog widget.

        Args:
            label_height: Height of each log message label (default 25)
            **kwargs: Additional keyword arguments passed to ScrollView
        """
        super().__init__(**kwargs)
        self._label_height = label_height
        self.layout = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            padding=5,
            spacing=2
        )
        self.layout.bind(minimum_height=self.layout.setter('height'))
        self.add_widget(self.layout)

    def add_message(self, text: str, color: Optional[Tuple] = None):
        """Add a log message with optional color.

        Args:
            text: The message text to display
            color: Optional color tuple (r, g, b, a). If None, uses white.
        """
        if color is None:
            color = COLOR_SECUNDARY

        label = Label(
            text=text,
            size_hint_y=None,
            height=self._label_height,
            halign='left',
            valign='middle',
            color=color,
        )
        # Bind text_size to ScrollView width so it updates on resize
        def update_text_size(_instance, value):
            label.text_size = (value - 20, None)
        self.bind(width=update_text_size)
        # Set initial text_size (in case width is already known)
        label.text_size = (self.width - 20 if self.width > 20 else 100, None)

        # Adjust height based on text content
        label.bind(
            texture_size=lambda instance, value: setattr(
                instance, 'height', max(self._label_height, value[1] + 10)
            )
        )
        self.layout.add_widget(label)

        # Auto-scroll to bottom
        Clock.schedule_once(lambda dt: setattr(self, 'scroll_y', 0), 0.1)

    def clear(self):
        """Clear all log messages."""
        self.layout.clear_widgets()


# =============================================================================
# Widget Factory Functions
# =============================================================================

def create_separator(color: Tuple = None, height: int = 2) -> Widget:
    """Create a horizontal separator line widget.

    Args:
        color: Color tuple for the separator. Defaults to COLOR_PRIMARY.
        height: Height of the separator in pixels. Defaults to 2.

    Returns:
        A Widget configured as a colored horizontal line.
    """
    if color is None:
        color = COLOR_PRIMARY

    separator = Widget(size_hint_y=None, height=height)
    with separator.canvas:
        Color(*color)
        rect = Rectangle(pos=separator.pos, size=separator.size)
    separator.bind(pos=lambda inst, val: setattr(rect, 'pos', val))
    separator.bind(size=lambda inst, val: setattr(rect, 'size', val))
    return separator


def create_title(text: str, font_size: int = 42) -> BoxLayout:
    """Create a styled title widget.

    Args:
        text: The title text to display
        font_size: Font size for the title. Defaults to 42.

    Returns:
        A BoxLayout containing the styled title label.
    """
    title_box = BoxLayout(size_hint_y=None, height=50, padding=15)
    title_label = Label(
        text=text,
        font_size=font_size,
        bold=True,
        color=COLOR_PRIMARY,
    )
    title_box.add_widget(title_label)
    return title_box


def create_section_label(text: str, height: int = 25) -> Label:
    """Create a section label (e.g., 'Activity Log:').

    Args:
        text: The label text
        height: Height of the label. Defaults to 25.

    Returns:
        A Label widget with left-aligned text.
    """
    label = Label(
        text=text,
        size_hint_y=None,
        height=height,
        halign='left',
    )
    label.bind(width=lambda instance, value: setattr(instance, 'text_size', (value, None)))
    return label


def create_clear_button(on_press_callback, text: str = 'Clear Log') -> Button:
    """Create a styled Clear Log button.

    Args:
        on_press_callback: Function to call when button is pressed
        text: Button text. Defaults to 'Clear Log'.

    Returns:
        A styled Button widget.
    """
    btn = Button(
        text=text,
        size_hint_y=None,
        height=40,
        background_color=COLOR_BG_LIGHT,
        background_normal='',
    )
    btn.bind(on_press=on_press_callback)
    return btn


def create_action_button(text: str, color: Tuple = None, bold: bool = True,
                            disabled: bool = False) -> Button:
    """Create a styled action button.

    Args:
        text: Button text
        color: Background color tuple. Defaults to COLOR_PRIMARY.
        bold: Whether to use bold text. Defaults to True.
        disabled: Whether button is initially disabled. Defaults to False.

    Returns:
        A styled Button widget.
    """
    if color is None:
        color = COLOR_PRIMARY

    return Button(
        text=text,
        background_color=color,
        background_normal='',
        bold=bold,
        disabled=disabled,
    )


def create_refresh_button(text: str, width: int = 90) -> Button:
    """Create a styled refresh/scan button with fixed width.

    Args:
        text: Button text.
        width: Button width in pixels. Defaults to 90.

    Returns:
        A styled Button widget with fixed width.
    """
    return Button(
        text=text,
        size_hint_x=None,
        width=width,
        background_color=COLOR_BG_LIGHT,
        background_normal='',
        font_size='14sp',
    )


def create_toggle_button(text: str, width: int = 60) -> Button:
    """Create a styled toggle button (e.g., Show/Hide for password fields).

    Args:
        text: Initial button text.
        width: Button width in pixels. Defaults to 60.

    Returns:
        A styled Button widget with fixed width.
    """
    return Button(
        text=text,
        size_hint_x=None,
        width=width,
        background_color=COLOR_BG_LIGHT,
        background_normal='',
        font_size='12sp',
    )


def create_popup_button(text: str, primary: bool = True) -> Button:
    """Create a styled button for use in popups.

    Creates a full-width button with larger font size, suitable for
    popup dialogs (e.g., Close, OK, Copy buttons).

    Args:
        text: Button text.
        primary: If True, uses COLOR_PRIMARY (orange). If False, uses COLOR_BG_LIGHT.

    Returns:
        A styled Button widget with fixed height.
    """
    return Button(
        text=text,
        size_hint_y=None,
        height=50,
        background_color=COLOR_PRIMARY if primary else COLOR_BG_LIGHT,
        background_normal='',
        bold=True,
        font_size='18sp',
    )


def create_popup_inline_button(text: str, width: int = 120) -> Button:
    """Create a styled inline button for use in popup rows.

    Creates a fixed-width button matching the style of main screen
    inline buttons (Scan, Show/Hide), suitable for inline placement
    within popup content rows (e.g., Copy TXID button).

    Args:
        text: Button text.
        width: Button width in pixels. Defaults to 120.

    Returns:
        A styled Button widget with fixed width.
    """
    return Button(
        text=text,
        size_hint_x=None,
        width=width,
        background_color=COLOR_BG_LIGHT,
        background_normal='',
        font_size='14sp',
    )


def create_status_row(label_text: str, initial_value: str = '',
                      initial_color: Tuple = None,
                      height: int = 30, bold_value: bool = False) -> Tuple[BoxLayout, Label]:
    """Create a status row with a description label and value label.

    Creates a horizontal layout with an auto-sized description label on the left
    and a flexible-width value label on the right. The description label
    automatically sizes to fit its text content. The value label can be updated
    independently to show status changes.

    Args:
        label_text: Text for the description label (e.g., 'Meshtastic:')
        initial_value: Initial text for the value label. Defaults to empty.
        initial_color: Initial color for the value label. Defaults to COLOR_SECUNDARY.
        height: Height of the row in pixels. Defaults to 30.
        bold_value: Whether the value label should be bold. Defaults to False.

    Returns:
        Tuple of (container BoxLayout, value Label). The value Label can be used
        to update the status text and color.

    Example:
        row, value_label = create_status_row('Meshtastic:', 'Not connected')
        status_section.add_widget(row)
        # Later, update the status:
        value_label.text = 'Connected (!abcdef12)'
        value_label.color = COLOR_SUCCESS
    """
    if initial_color is None:
        initial_color = COLOR_SECUNDARY

    row = BoxLayout(orientation='horizontal', size_hint_y=None, height=height)

    # Description label (auto-sized to fit text)
    desc_label = Label(
        text=label_text,
        size_hint_x=None,
        halign='left',
        valign='middle',
        color=COLOR_SECUNDARY,
    )
    # Bind width to texture size so label auto-fits its text content (+ padding for spacing)
    desc_label.bind(texture_size=lambda inst, val: setattr(inst, 'width', val[0] + 25))
    row.add_widget(desc_label)

    # Value label (flexible width)
    value_label = Label(
        text=initial_value,
        halign='left',
        valign='middle',
        color=initial_color,
        bold=bold_value,
    )
    value_label.bind(size=value_label.setter('text_size'))
    row.add_widget(value_label)

    return row, value_label


def create_input_row(label_text: str, initial_value: str = '',
                    hint_text: str = '', height: int = 40,
                    password: bool = False, input_filter: str = None,
                    input_size_hint_x: float = 0.7) -> Tuple[BoxLayout, TextInput]:
    """Create an input row with a description label and text input field.

    Creates a horizontal layout with an auto-sized description label on the left
    and a styled TextInput on the right. The description label automatically
    sizes to fit its text content using texture_size binding.

    Args:
        label_text: Text for the description label (e.g., 'Host:', 'Password:')
        initial_value: Initial text value for the input. Defaults to empty.
        hint_text: Placeholder hint text for the input. Defaults to empty.
        height: Height of the row in pixels. Defaults to 40.
        password: Whether to mask input as password. Defaults to False.
        input_filter: Optional input filter (e.g., 'int' for numbers only).
        input_size_hint_x: Proportional width for the input field. Defaults to 0.7.

    Returns:
        Tuple of (container BoxLayout, TextInput). The TextInput can be used
        to access or modify the input value.

    Example:
        row, host_input = create_input_row('Host:', '127.0.0.1', hint_text='IP address')
        settings_section.add_widget(row)
        # Later, get the value:
        host = host_input.text.strip()
    """
    row = BoxLayout(orientation='horizontal', size_hint_y=None, height=height, spacing=5)

    # Description label (auto-sized to fit text)
    desc_label = Label(
        text=label_text,
        size_hint_x=None,
        halign='right',
        valign='middle',
        color=COLOR_SECUNDARY,
    )
    # Bind width to texture size so label auto-fits its text content (+ padding for spacing)
    desc_label.bind(texture_size=lambda inst, val: setattr(inst, 'width', val[0] + 15))
    row.add_widget(desc_label)

    # Text input with consistent styling
    text_input = TextInput(
        text=initial_value,
        hint_text=hint_text,
        multiline=False,
        password=password,
        size_hint_x=input_size_hint_x,
        background_color=COLOR_BG_LIGHT,
        foreground_color=COLOR_SECUNDARY,
        cursor_color=COLOR_PRIMARY,
    )
    if input_filter:
        text_input.input_filter = input_filter
    row.add_widget(text_input)

    return row, text_input
