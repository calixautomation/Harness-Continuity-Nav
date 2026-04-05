"""8x8 LED Grid Widget for visualizing test patterns."""

from typing import Optional, Dict
from PyQt5.QtWidgets import QWidget, QGridLayout, QPushButton, QSizePolicy, QFrame
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QFont

from ...core.patterns.models import Pattern, LEDStatus


class LEDButton(QPushButton):
    """Individual LED cell button."""

    def __init__(self, led_num: int, parent=None):
        super().__init__(parent)
        self.led_num = led_num
        self.status = LEDStatus.OFF
        self._blink_state = True  # For blinking animation

        # Fixed square size
        self.setFixedSize(60, 60)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # Font for LED number
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.setFont(font)

        self.setText(str(led_num))
        self.set_status(LEDStatus.OFF)

    def set_status(self, status: LEDStatus, blink_on: bool = True) -> None:
        """Set LED status and update appearance."""
        self.status = status
        self._blink_state = blink_on

        colors = {
            LEDStatus.OFF: ("#333333", "#888888"),       # Dark gray, light text
            LEDStatus.PENDING: ("#FFFF00", "#000000"),   # Yellow, black text
            LEDStatus.ACTIVE: ("#00AAFF", "#FFFFFF"),    # Cyan, white text (blinks)
            LEDStatus.LOCKED: ("#FF8800", "#FFFFFF"),    # Orange, white text (wire locked)
            LEDStatus.VERIFIED: ("#00FF00", "#000000"),  # Green, black text
            LEDStatus.ERROR: ("#FF0000", "#FFFFFF"),     # Red, white text
        }

        bg_color, text_color = colors.get(status, colors[LEDStatus.OFF])

        # For ACTIVE status, alternate between bright cyan and dim cyan
        if status == LEDStatus.ACTIVE:
            if blink_on:
                bg_color = "#00AAFF"  # Bright cyan
                border_color = "#00FFFF"
            else:
                bg_color = "#005577"  # Dim cyan
                border_color = "#007799"
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg_color};
                    color: {text_color};
                    border: 3px solid {border_color};
                    border-radius: 8px;
                    font-weight: bold;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg_color};
                    color: {text_color};
                    border: 2px solid #555555;
                    border-radius: 8px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    border: 2px solid #FFFFFF;
                }}
                QPushButton:pressed {{
                    background-color: #AAAAAA;
                }}
            """)


class GridWidget(QWidget):
    """
    8x8 LED Grid Widget with large clickable cells.

    LED numbering:
        1  2  3  4  5  6  7  8
        9  10 11 12 13 14 15 16
        17 18 19 20 21 22 23 24
        25 26 27 28 29 30 31 32
        33 34 35 36 37 38 39 40
        41 42 43 44 45 46 47 48
        49 50 51 52 53 54 55 56
        57 58 59 60 61 62 63 64
    """

    # Signal emitted when an LED is clicked (led_num 1-64)
    led_clicked = pyqtSignal(int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._pattern: Optional[Pattern] = None
        self._led_buttons: Dict[int, LEDButton] = {}
        self._blink_state = True
        self._blinking_enabled = False

        # Blink timer for active LED
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._on_blink_timer)
        self._blink_timer.setInterval(500)  # 500ms blink interval

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the grid layout."""
        layout = QGridLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(10, 10, 10, 10)

        # Create 8x8 grid of LED buttons
        for row in range(8):
            for col in range(8):
                led_num = row * 8 + col + 1  # 1-64

                btn = LEDButton(led_num)
                btn.clicked.connect(lambda checked, n=led_num: self._on_led_clicked(n))

                layout.addWidget(btn, row, col)
                self._led_buttons[led_num] = btn

        # Set background
        self.setStyleSheet("background-color: #1A1A1A;")

    def _on_led_clicked(self, led_num: int) -> None:
        """Handle LED button click."""
        self.led_clicked.emit(led_num)

    def _on_blink_timer(self) -> None:
        """Handle blink timer tick."""
        self._blink_state = not self._blink_state

        # Update active LED's blink state
        if self._pattern and self._pattern.active_led:
            active_led = self._pattern.active_led
            if active_led in self._led_buttons:
                btn = self._led_buttons[active_led]
                if btn.status == LEDStatus.ACTIVE:
                    btn.set_status(LEDStatus.ACTIVE, self._blink_state)

    def start_blinking(self) -> None:
        """Start the blinking animation for active LED."""
        self._blinking_enabled = True
        self._blink_state = True
        self._blink_timer.start()

    def stop_blinking(self) -> None:
        """Stop the blinking animation."""
        self._blinking_enabled = False
        self._blink_timer.stop()
        # Ensure active LED is shown in bright state
        if self._pattern and self._pattern.active_led:
            active_led = self._pattern.active_led
            if active_led in self._led_buttons:
                self._led_buttons[active_led].set_status(LEDStatus.ACTIVE, True)

    def set_pattern(self, pattern: Optional[Pattern]) -> None:
        """
        Set the pattern to display.

        Args:
            pattern: Pattern to display, or None to clear
        """
        self._pattern = pattern

        # Reset all LEDs to OFF
        for btn in self._led_buttons.values():
            btn.set_status(LEDStatus.OFF)

        # Set pattern LEDs to PENDING
        if pattern:
            for led_num in pattern.leds:
                if led_num in self._led_buttons:
                    status = pattern.get_led_status(led_num)
                    self._led_buttons[led_num].set_status(status)

    def update_led_status(self, led_num: int, status: LEDStatus) -> None:
        """Update the status of a specific LED."""
        if led_num in self._led_buttons:
            self._led_buttons[led_num].set_status(status)

    def refresh_display(self) -> None:
        """Refresh the entire display from current pattern data."""
        if self._pattern:
            # First reset all to OFF
            for btn in self._led_buttons.values():
                btn.set_status(LEDStatus.OFF)

            # Then update pattern LEDs
            for led_num in self._pattern.leds:
                status = self._pattern.get_led_status(led_num)
                if led_num in self._led_buttons:
                    self._led_buttons[led_num].set_status(status)

    def clear_display(self) -> None:
        """Clear all LEDs to off state."""
        for btn in self._led_buttons.values():
            btn.set_status(LEDStatus.OFF)
        self._pattern = None

    def highlight_led(self, led_num: int, status: LEDStatus) -> None:
        """Highlight a specific LED."""
        if led_num in self._led_buttons:
            self._led_buttons[led_num].set_status(status)

    @property
    def current_pattern(self) -> Optional[Pattern]:
        """Get the currently displayed pattern."""
        return self._pattern
