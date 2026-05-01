"""Main application window for LED Pattern Test System."""

from typing import Optional, List
from pathlib import Path
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStatusBar, QMessageBox, QGroupBox, QComboBox,
    QPushButton, QLabel, QProgressBar, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QCloseEvent, QFont, QKeySequence
from PyQt5.QtWidgets import QShortcut

from .widgets.grid_widget import GridWidget
from .pattern_editor import PatternEditorDialog
from ..core.patterns.models import Pattern, TestState, LEDStatus
from ..core.patterns.pattern_loader import PatternLoader


class MainWindow(QMainWindow):
    """
    Main application window for LED Pattern Testing.

    Layout:
    ┌──────────────────────────────────────────────────────┐
    │                  LED Pattern Tester                   │
    ├────────────────┬─────────────────────────────────────┤
    │                │                                     │
    │   Pattern      │         8x8 LED Grid                │
    │   Selection    │         (Large Buttons)             │
    │                │                                     │
    │   Controls     │         1  2  3  4  5  6  7  8      │
    │                │         9  10 11 ...                │
    │   Progress     │         ...                         │
    │                │         57 58 59 60 61 62 63 64     │
    │                │                                     │
    └────────────────┴─────────────────────────────────────┘
    │                      Status Bar                       │
    └──────────────────────────────────────────────────────┘
    """

    # Signals
    test_started = pyqtSignal()
    test_stopped = pyqtSignal()
    pattern_selected = pyqtSignal(str)  # pattern_id

    def __init__(
        self,
        patterns_file: str = "./data/patterns.json",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        self._patterns_file = patterns_file
        self._pattern_loader = PatternLoader(patterns_file)
        self._patterns: List[Pattern] = []
        self._current_pattern: Optional[Pattern] = None
        self._state = TestState.IDLE

        # Hardware mode: hide test buttons, use GPIO triggers
        self._hardware_mode = False
        # Live matrix mode: auto-start test when a pattern is selected.
        self._live_matrix_mode = False

        # Callbacks
        self._on_start_test = None
        self._on_stop_test = None
        self._on_reset = None
        self._on_led_selected = None
        self._on_lock_wire = None
        self._on_verify_connection = None

        self._setup_ui()
        self._setup_shortcuts()
        self._connect_signals()
        self._load_patterns()

    def _setup_ui(self) -> None:
        """Setup the main window UI."""
        self.setWindowTitle("LED Pattern Tester")
        self.setMinimumSize(900, 650)

        # Create central widget
        central = QWidget()
        self.setCentralWidget(central)

        # Main horizontal layout
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # Left panel - Controls
        left_panel = self._create_left_panel()
        main_layout.addWidget(left_panel)

        # Right panel - LED Grid
        self._grid_widget = GridWidget()
        main_layout.addWidget(self._grid_widget, 1)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Ready - Select a pattern to begin")

        # Apply styling
        self._apply_styles()

    def _setup_shortcuts(self) -> None:
        """Setup keyboard shortcuts for emergency exit."""
        # Escape key to exit application
        self._escape_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self._escape_shortcut.activated.connect(self._on_emergency_exit)

        # Ctrl+Q to exit application
        self._quit_shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        self._quit_shortcut.activated.connect(self._on_emergency_exit)

        # F10 for emergency exit (alternative)
        self._f10_shortcut = QShortcut(QKeySequence(Qt.Key_F10), self)
        self._f10_shortcut.activated.connect(self._on_emergency_exit)

    def _on_emergency_exit(self) -> None:
        """Handle emergency exit request."""
        from PyQt5.QtWidgets import QApplication
        self.close()
        QApplication.instance().quit()

    def _create_left_panel(self) -> QWidget:
        """Create the left control panel."""
        panel = QWidget()
        panel.setFixedWidth(250)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Pattern Selection Group
        pattern_group = QGroupBox("Pattern Selection")
        pattern_layout = QVBoxLayout(pattern_group)

        self._pattern_combo = QComboBox()
        self._pattern_combo.setMinimumHeight(35)
        self._pattern_combo.currentIndexChanged.connect(self._on_pattern_selected)
        pattern_layout.addWidget(self._pattern_combo)

        # Pattern info label
        self._pattern_info = QLabel("Select a pattern")
        self._pattern_info.setWordWrap(True)
        self._pattern_info.setStyleSheet("color: #AAAAAA; font-style: italic;")
        pattern_layout.addWidget(self._pattern_info)

        # Pattern management buttons
        pattern_btn_layout = QHBoxLayout()

        self._new_pattern_btn = QPushButton("New Pattern")
        self._new_pattern_btn.setMinimumHeight(30)
        self._new_pattern_btn.clicked.connect(self._on_new_pattern)
        self._new_pattern_btn.setStyleSheet("""
            QPushButton {
                background-color: #1565C0;
                color: white;
            }
            QPushButton:hover { background-color: #1976D2; }
        """)
        pattern_btn_layout.addWidget(self._new_pattern_btn)

        self._edit_pattern_btn = QPushButton("Edit")
        self._edit_pattern_btn.setMinimumHeight(30)
        self._edit_pattern_btn.setEnabled(False)
        self._edit_pattern_btn.clicked.connect(self._on_edit_pattern)
        pattern_btn_layout.addWidget(self._edit_pattern_btn)

        self._delete_pattern_btn = QPushButton("Delete")
        self._delete_pattern_btn.setMinimumHeight(30)
        self._delete_pattern_btn.setEnabled(False)
        self._delete_pattern_btn.clicked.connect(self._on_delete_pattern)
        self._delete_pattern_btn.setStyleSheet("""
            QPushButton {
                background-color: #C62828;
                color: white;
            }
            QPushButton:hover { background-color: #D32F2F; }
            QPushButton:disabled { background-color: #555555; color: #888888; }
        """)
        pattern_btn_layout.addWidget(self._delete_pattern_btn)

        pattern_layout.addLayout(pattern_btn_layout)

        layout.addWidget(pattern_group)

        # Test Controls Group
        controls_group = QGroupBox("Test Controls")
        controls_layout = QVBoxLayout(controls_group)

        # Start/Stop button
        self._start_btn = QPushButton("Start Test")
        self._start_btn.setMinimumHeight(50)
        self._start_btn.setEnabled(False)
        self._start_btn.clicked.connect(self._on_start_clicked)
        self._update_start_button_style(False)
        controls_layout.addWidget(self._start_btn)

        # Reset button
        self._reset_btn = QPushButton("Reset")
        self._reset_btn.setMinimumHeight(35)
        self._reset_btn.clicked.connect(self._on_reset_clicked)
        controls_layout.addWidget(self._reset_btn)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        controls_layout.addWidget(line)

        # Two-stage verification buttons
        # Step 1: Lock Wire button (simulates limit switch press)
        self._lock_btn = QPushButton("1. Lock Wire")
        self._lock_btn.setMinimumHeight(40)
        self._lock_btn.setEnabled(False)
        self._lock_btn.setToolTip("Click when wire is inserted and locked in slot")
        self._lock_btn.clicked.connect(self._on_lock_clicked)
        self._lock_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF8800;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #FF9922; }
            QPushButton:disabled { background-color: #555555; color: #888888; }
        """)
        controls_layout.addWidget(self._lock_btn)

        # Step 2: Verify Connection button (simulates metal plate touch)
        self._verify_btn = QPushButton("2. Verify Connection")
        self._verify_btn.setMinimumHeight(40)
        self._verify_btn.setEnabled(False)
        self._verify_btn.setToolTip("Click when wire touches metal plate to verify connectivity")
        self._verify_btn.clicked.connect(self._on_verify_clicked)
        self._verify_btn.setStyleSheet("""
            QPushButton {
                background-color: #1565C0;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1976D2; }
            QPushButton:disabled { background-color: #555555; color: #888888; }
        """)
        controls_layout.addWidget(self._verify_btn)

        # Status indicator for current step
        self._step_label = QLabel("Step: Select pattern and start test")
        self._step_label.setWordWrap(True)
        self._step_label.setAlignment(Qt.AlignCenter)
        self._step_label.setStyleSheet("color: #AAAAAA; font-style: italic;")
        controls_layout.addWidget(self._step_label)

        layout.addWidget(controls_group)

        # Progress Group
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)

        self._progress_bar = QProgressBar()
        self._progress_bar.setMinimumHeight(25)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        progress_layout.addWidget(self._progress_bar)

        self._progress_label = QLabel("0 / 0 LEDs verified")
        self._progress_label.setAlignment(Qt.AlignCenter)
        progress_layout.addWidget(self._progress_label)

        layout.addWidget(progress_group)

        # Current LED Group
        led_group = QGroupBox("Current LED")
        led_layout = QVBoxLayout(led_group)

        self._current_led_label = QLabel("None selected")
        self._current_led_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        self._current_led_label.setFont(font)
        self._current_led_label.setStyleSheet("color: #00AAFF;")
        led_layout.addWidget(self._current_led_label)

        layout.addWidget(led_group)

        # Spacer
        layout.addStretch()

        return panel

    def _apply_styles(self) -> None:
        """Apply application-wide styles."""
        self.setStyleSheet("""
            QMainWindow { background-color: #2D2D2D; }
            QGroupBox {
                color: #FFFFFF;
                font-weight: bold;
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLabel { color: #CCCCCC; }
            QComboBox {
                background-color: #404040;
                color: #FFFFFF;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 8px;
                font-size: 13px;
            }
            QComboBox:hover { border: 1px solid #777777; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #404040;
                color: #FFFFFF;
                selection-background-color: #0078D7;
            }
            QPushButton {
                background-color: #404040;
                color: #FFFFFF;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 8px 15px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #505050; }
            QPushButton:pressed { background-color: #353535; }
            QPushButton:disabled { background-color: #333333; color: #666666; }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 5px;
                text-align: center;
                color: #FFFFFF;
                background-color: #404040;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 4px;
            }
            QStatusBar {
                background-color: #1A1A1A;
                color: #AAAAAA;
            }
        """)

    def _update_start_button_style(self, is_testing: bool) -> None:
        """Update start button appearance based on state."""
        if is_testing:
            self._start_btn.setText("Stop Test")
            self._start_btn.setStyleSheet("""
                QPushButton {
                    background-color: #C62828;
                    color: white;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover { background-color: #D32F2F; }
            """)
        else:
            self._start_btn.setText("Start Test")
            self._start_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2E7D32;
                    color: white;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover { background-color: #388E3C; }
                QPushButton:disabled { background-color: #555555; color: #888888; }
            """)

    def _connect_signals(self) -> None:
        """Connect widget signals."""
        self._grid_widget.led_clicked.connect(self._on_led_clicked)

    def _load_patterns(self) -> None:
        """Load patterns from JSON file."""
        try:
            self._patterns = self._pattern_loader.load()
            self._pattern_combo.clear()
            self._pattern_combo.addItem("-- Select Pattern --")

            for pattern in self._patterns:
                self._pattern_combo.addItem(
                    f"{pattern.name}: {pattern.description}",
                    pattern.id
                )

            self._status_bar.showMessage(f"Loaded {len(self._patterns)} patterns")

        except FileNotFoundError:
            self._status_bar.showMessage("No patterns file found")
        except Exception as e:
            self._status_bar.showMessage(f"Error loading patterns: {e}")

    def _on_pattern_selected(self, index: int) -> None:
        """Handle pattern selection from combo box."""
        if index <= 0:
            self._current_pattern = None
            self._grid_widget.clear_display()
            self._start_btn.setEnabled(False)
            self._edit_pattern_btn.setEnabled(False)
            self._delete_pattern_btn.setEnabled(False)
            self._pattern_info.setText("Select a pattern")
            self._update_progress(0, 0)
            self._state = TestState.IDLE
            return

        pattern_id = self._pattern_combo.itemData(index)
        self._current_pattern = self._pattern_loader.get_pattern_by_id(pattern_id)

        if self._current_pattern:
            self._current_pattern.reset()
            self._grid_widget.set_pattern(self._current_pattern)
            self._start_btn.setEnabled(True)
            self._edit_pattern_btn.setEnabled(True)
            self._delete_pattern_btn.setEnabled(True)
            self._state = TestState.PATTERN_LOADED

            leds_str = ", ".join(str(led) for led in self._current_pattern.leds)
            self._pattern_info.setText(f"LEDs to test: {leds_str}")
            self._update_progress(0, len(self._current_pattern.leds))
            self._status_bar.showMessage(
                f"Pattern loaded: {len(self._current_pattern.leds)} LEDs to test"
            )
            self.pattern_selected.emit(pattern_id)

            if self._live_matrix_mode and self._state == TestState.PATTERN_LOADED:
                self._start_test()

    def _on_led_clicked(self, led_num: int) -> None:
        """Handle LED button click."""
        if self._state != TestState.TESTING:
            return

        if not self._current_pattern:
            return

        # Check if LED is part of pattern and not already verified
        if led_num not in self._current_pattern.leds:
            self._status_bar.showMessage(f"LED {led_num} is not part of this pattern!")
            return

        if led_num in self._current_pattern.verified_leds:
            self._status_bar.showMessage(f"LED {led_num} already verified")
            return

        # Select this LED
        if self._current_pattern.select_led(led_num):
            self._grid_widget.refresh_display()
            self._current_led_label.setText(f"LED {led_num}")
            self._verify_btn.setEnabled(True)
            self._status_bar.showMessage(f"LED {led_num} selected - Click 'Verify Connection'")

            if self._on_led_selected:
                self._on_led_selected(led_num)

    def _on_start_clicked(self) -> None:
        """Handle start/stop button click."""
        if self._state == TestState.TESTING:
            self._stop_test()
        else:
            self._start_test()

    def _start_test(self) -> None:
        """Start the test."""
        if not self._current_pattern:
            return

        self._state = TestState.TESTING
        self._update_start_button_style(True)
        self._pattern_combo.setEnabled(False)
        self._current_pattern.reset()
        self._grid_widget.refresh_display()

        # Auto-select first LED
        first_led = self._current_pattern.auto_select_next()
        if first_led:
            self._grid_widget.refresh_display()
            self._current_led_label.setText(f"LED {first_led}")
            self._current_led_label.setStyleSheet("color: #00AAFF;")
            self._lock_btn.setEnabled(not self._hardware_mode)
            self._verify_btn.setEnabled(False)
            if self._hardware_mode:
                self._step_label.setText("Insert wire and lock it")
            else:
                self._step_label.setText("Step 1: Insert wire in slot and lock it")
            self._step_label.setStyleSheet("color: #FF8800; font-weight: bold;")

        # Start blinking animation
        self._grid_widget.start_blinking()

        self._status_bar.showMessage("Test started - Insert wire and lock it in the slot")
        self.test_started.emit()

        if self._on_start_test:
            self._on_start_test()

    def _stop_test(self) -> None:
        """Stop the test."""
        self._state = TestState.PATTERN_LOADED
        self._update_start_button_style(False)
        self._pattern_combo.setEnabled(True)
        self._lock_btn.setEnabled(False)
        self._verify_btn.setEnabled(False)
        self._current_led_label.setText("None selected")
        self._current_led_label.setStyleSheet("color: #00AAFF;")
        self._step_label.setText("Step: Select pattern and start test")
        self._step_label.setStyleSheet("color: #AAAAAA; font-style: italic;")

        # Stop blinking animation
        self._grid_widget.stop_blinking()

        self._status_bar.showMessage("Test stopped")
        self.test_stopped.emit()

        if self._on_stop_test:
            self._on_stop_test()

    def _on_reset_clicked(self) -> None:
        """Handle reset button click."""
        if self._current_pattern:
            self._current_pattern.reset()
            self._grid_widget.refresh_display()
            self._update_progress(0, len(self._current_pattern.leds))
            self._current_led_label.setText("None selected")
            self._current_led_label.setStyleSheet("color: #00AAFF;")
            self._lock_btn.setEnabled(False)
            self._verify_btn.setEnabled(False)

            if self._state == TestState.TESTING:
                first_led = self._current_pattern.auto_select_next()
                if first_led:
                    self._grid_widget.refresh_display()
                    self._current_led_label.setText(f"LED {first_led}")
                    self._lock_btn.setEnabled(True)
                    self._step_label.setText("Step 1: Insert wire in slot and lock it")
                    self._step_label.setStyleSheet("color: #FF8800; font-weight: bold;")

            self._status_bar.showMessage("Pattern reset")

            if self._on_reset:
                self._on_reset()

    def _on_lock_clicked(self) -> None:
        """Handle lock button click (simulates limit switch press when wire locked)."""
        if not self._current_pattern or self._state != TestState.TESTING:
            return

        active_led = self._current_pattern.active_led
        if active_led == 0:
            return

        # Lock the wire in slot
        if self._current_pattern.lock_active_led():
            self._grid_widget.refresh_display()
            self._lock_btn.setEnabled(False)
            self._verify_btn.setEnabled(True)
            self._step_label.setText("Step 2: Touch wire on metal plate")
            self._step_label.setStyleSheet("color: #00AAFF; font-weight: bold;")
            self._status_bar.showMessage(f"LED {active_led} wire locked - Now verify connectivity")

            # Callback for buzzer beep (lock tone)
            if hasattr(self, '_on_lock_wire') and self._on_lock_wire:
                self._on_lock_wire(active_led)

    def _on_verify_clicked(self) -> None:
        """Handle verify button click (simulates metal plate touch - circuit complete)."""
        if not self._current_pattern or self._state != TestState.TESTING:
            return

        active_led = self._current_pattern.active_led
        if active_led == 0:
            return

        # Check if wire is locked first
        if not self._current_pattern.is_active_led_locked():
            self._status_bar.showMessage("Wire must be locked first! Click 'Lock Wire'")
            return

        # Verify the LED (circuit complete)
        self._current_pattern.verify_active_led()
        self._grid_widget.refresh_display()

        verified, total = self._current_pattern.progress
        self._update_progress(verified, total)

        self._status_bar.showMessage(f"LED {active_led} verified! ({verified}/{total})")

        # Check if complete
        if self._current_pattern.is_complete:
            self._state = TestState.COMPLETE
            self._update_start_button_style(False)
            self._start_btn.setEnabled(False)
            self._pattern_combo.setEnabled(True)
            self._lock_btn.setEnabled(False)
            self._verify_btn.setEnabled(False)
            self._current_led_label.setText("COMPLETE!")
            self._current_led_label.setStyleSheet("color: #00FF00;")
            self._step_label.setText("All wires verified successfully!")
            self._step_label.setStyleSheet("color: #00FF00; font-weight: bold;")

            # Stop blinking
            self._grid_widget.stop_blinking()

            self._status_bar.showMessage("Test COMPLETE! All LEDs verified.")
            QMessageBox.information(self, "Complete", "All LEDs verified successfully!")
        else:
            # Auto-select next LED
            next_led = self._current_pattern.auto_select_next()
            if next_led:
                self._grid_widget.refresh_display()
                self._current_led_label.setText(f"LED {next_led}")
                self._current_led_label.setStyleSheet("color: #00AAFF;")
                self._lock_btn.setEnabled(True)
                self._verify_btn.setEnabled(False)
                self._step_label.setText("Step 1: Insert wire in slot and lock it")
                self._step_label.setStyleSheet("color: #FF8800; font-weight: bold;")

        if self._on_verify_connection:
            self._on_verify_connection(active_led)

    def _update_progress(self, verified: int, total: int) -> None:
        """Update progress display."""
        if total > 0:
            self._progress_bar.setMaximum(total)
            self._progress_bar.setValue(verified)
            percent = int((verified / total) * 100)
            self._progress_bar.setFormat(f"{percent}%")
        else:
            self._progress_bar.setMaximum(100)
            self._progress_bar.setValue(0)
            self._progress_bar.setFormat("0%")

        self._progress_label.setText(f"{verified} / {total} LEDs verified")

    def set_callbacks(
        self,
        on_start_test=None,
        on_stop_test=None,
        on_reset=None,
        on_led_selected=None,
        on_lock_wire=None,
        on_verify_connection=None
    ) -> None:
        """Set callbacks for external coordination."""
        self._on_start_test = on_start_test
        self._on_stop_test = on_stop_test
        self._on_reset = on_reset
        self._on_led_selected = on_led_selected
        self._on_lock_wire = on_lock_wire
        self._on_verify_connection = on_verify_connection

    def set_hardware_mode(self, enabled: bool) -> None:
        """
        Enable/disable hardware mode.

        In hardware mode:
        - Lock Wire and Verify buttons are hidden
        - Actions are triggered by hardware GPIO inputs
        """
        self._hardware_mode = enabled
        self._lock_btn.setVisible(not enabled)
        self._verify_btn.setVisible(not enabled)

        if enabled:
            self._step_label.setText("Hardware mode: waiting for switch inputs")
        else:
            self._step_label.setText("Step: Select pattern and start test")

    def set_live_matrix_mode(self, enabled: bool) -> None:
        """
        Enable sequential live mode for external switch-driven progression.

        In live mode:
        - Pattern selection auto-starts test
        - Start button is hidden
        - Hardware mode is enabled
        """
        self._live_matrix_mode = enabled
        self._start_btn.setVisible(not enabled)
        self.set_hardware_mode(enabled)

        if enabled and self._current_pattern and self._state == TestState.PATTERN_LOADED:
            self._start_test()

    def trigger_increment_led(self) -> bool:
        """
        Advance one LED step from hardware limit switch.

        Behavior:
        - Current active LED blinks until switch press
        - On press, current LED is marked done and next LED starts blinking
        """
        if not self._current_pattern:
            return False

        if self._state == TestState.PATTERN_LOADED and self._live_matrix_mode:
            self._start_test()

        if self._state != TestState.TESTING:
            return False

        active_led = self._current_pattern.active_led
        if active_led == 0:
            active_led = self._current_pattern.auto_select_next() or 0
            if active_led == 0:
                return False

        if not self._current_pattern.is_active_led_locked():
            self._current_pattern.lock_active_led()

        if not self._current_pattern.verify_active_led():
            return False

        self._grid_widget.refresh_display()
        verified, total = self._current_pattern.progress
        self._update_progress(verified, total)

        if self._current_pattern.is_complete:
            self._state = TestState.COMPLETE
            self._update_start_button_style(False)
            self._pattern_combo.setEnabled(True)
            self._lock_btn.setEnabled(False)
            self._verify_btn.setEnabled(False)
            self._current_led_label.setText("COMPLETE!")
            self._current_led_label.setStyleSheet("color: #00FF00;")
            self._step_label.setText("All wires verified successfully!")
            self._step_label.setStyleSheet("color: #00FF00; font-weight: bold;")
            self._grid_widget.stop_blinking()
            self._status_bar.showMessage("Test COMPLETE! All LEDs verified.")
        else:
            next_led = self._current_pattern.auto_select_next()
            if next_led:
                self._grid_widget.refresh_display()
                self._current_led_label.setText(f"LED {next_led}")
                self._current_led_label.setStyleSheet("color: #00AAFF;")
                self._step_label.setText("Press limit switch to advance")
                self._step_label.setStyleSheet("color: #FF8800; font-weight: bold;")
                self._status_bar.showMessage(
                    f"LED {active_led} completed. LED {next_led} is now active"
                )

        if self._on_lock_wire:
            self._on_lock_wire(active_led)
        if self._on_verify_connection:
            self._on_verify_connection(active_led)

        return True

    def trigger_toggle_led(self) -> bool:
        """Compatibility toggle action for older switch workflows."""
        if not self._current_pattern or self._state != TestState.TESTING:
            return False

        active_led = self._current_pattern.active_led
        if active_led == 0:
            active_led = self._current_pattern.auto_select_next() or 0
            if active_led == 0:
                return False

        verified_set = getattr(self._current_pattern, "_verified_leds", None)
        if not isinstance(verified_set, set):
            return False

        if active_led in verified_set:
            verified_set.discard(active_led)
            led_on = False
        else:
            verified_set.clear()
            verified_set.add(active_led)
            led_on = True

        self._grid_widget.refresh_display()
        verified, total = self._current_pattern.progress
        self._update_progress(verified, total)
        self._current_led_label.setText(f"LED {active_led}")
        self._step_label.setText("Toggle mode active")
        self._step_label.setStyleSheet("color: #00AAFF; font-weight: bold;")
        self._status_bar.showMessage(f"LED {active_led} {'ON' if led_on else 'OFF'}")
        return True

    def trigger_lock(self) -> bool:
        """
        Trigger lock action from hardware (limit switch).
        Call this when the limit switch detects wire is locked.
        Returns True if successful.
        """
        if not self._current_pattern or self._state != TestState.TESTING:
            return False

        active_led = self._current_pattern.active_led
        if active_led == 0:
            return False

        # Lock the wire in slot
        if self._current_pattern.lock_active_led():
            self._grid_widget.refresh_display()
            self._lock_btn.setEnabled(False)
            self._verify_btn.setEnabled(True)
            self._step_label.setText("Wire locked - Touch metal plate to verify")
            self._step_label.setStyleSheet("color: #FF8800; font-weight: bold;")
            self._status_bar.showMessage(f"LED {active_led} wire locked - Now verify connectivity")

            # Callback for buzzer beep (lock tone)
            if self._on_lock_wire:
                self._on_lock_wire(active_led)
            return True
        return False

    def trigger_verify(self) -> bool:
        """
        Trigger verify action from hardware (metal plate touch).
        Call this when the metal plate detects circuit complete.
        Returns True if successful.
        """
        if not self._current_pattern or self._state != TestState.TESTING:
            return False

        active_led = self._current_pattern.active_led
        if active_led == 0:
            return False

        # Check if wire is locked first
        if not self._current_pattern.is_active_led_locked():
            self._status_bar.showMessage("Wire must be locked first!")
            return False

        # Verify the LED (circuit complete)
        self._current_pattern.verify_active_led()
        self._grid_widget.refresh_display()

        verified, total = self._current_pattern.progress
        self._update_progress(verified, total)

        self._status_bar.showMessage(f"LED {active_led} verified! ({verified}/{total})")

        # Check if complete
        if self._current_pattern.is_complete:
            self._state = TestState.COMPLETE
            self._update_start_button_style(False)
            self._start_btn.setEnabled(False)
            self._pattern_combo.setEnabled(True)
            self._lock_btn.setEnabled(False)
            self._verify_btn.setEnabled(False)
            self._current_led_label.setText("COMPLETE!")
            self._current_led_label.setStyleSheet("color: #00FF00;")
            self._step_label.setText("All wires verified successfully!")
            self._step_label.setStyleSheet("color: #00FF00; font-weight: bold;")

            # Stop blinking
            self._grid_widget.stop_blinking()

            self._status_bar.showMessage("Test COMPLETE! All LEDs verified.")
            QMessageBox.information(self, "Complete", "All LEDs verified successfully!")
        else:
            # Auto-select next LED
            next_led = self._current_pattern.auto_select_next()
            if next_led:
                self._grid_widget.refresh_display()
                self._current_led_label.setText(f"LED {next_led}")
                self._current_led_label.setStyleSheet("color: #00AAFF;")
                self._lock_btn.setEnabled(True)
                self._verify_btn.setEnabled(False)
                if self._hardware_mode:
                    self._step_label.setText("Insert wire and lock it")
                else:
                    self._step_label.setText("Step 1: Insert wire in slot and lock it")
                self._step_label.setStyleSheet("color: #FF8800; font-weight: bold;")

        if self._on_verify_connection:
            self._on_verify_connection(active_led)

        return True

    def update_led_status(self, led_num: int, status: LEDStatus) -> None:
        """Update LED status from external source."""
        self._grid_widget.update_led_status(led_num, status)

    def show_error(self, message: str) -> None:
        """Show error message."""
        self._status_bar.showMessage(f"ERROR: {message}")
        QMessageBox.critical(self, "Error", message)

    def show_message(self, message: str) -> None:
        """Show message in status bar."""
        self._status_bar.showMessage(message)

    @property
    def current_pattern(self) -> Optional[Pattern]:
        """Get current pattern."""
        return self._current_pattern

    def _on_new_pattern(self) -> None:
        """Open pattern editor to create a new pattern."""
        dialog = PatternEditorDialog(str(self._patterns_file), self)
        dialog.pattern_saved.connect(self._reload_patterns)
        dialog.exec_()

    def _on_edit_pattern(self) -> None:
        """Open pattern editor to edit current pattern."""
        if not self._current_pattern:
            return

        dialog = PatternEditorDialog(str(self._patterns_file), self)
        dialog.load_pattern(self._current_pattern.id)
        dialog.pattern_saved.connect(self._reload_patterns)
        dialog.exec_()

    def _on_delete_pattern(self) -> None:
        """Delete the current pattern."""
        if not self._current_pattern:
            return

        reply = QMessageBox.question(
            self, "Delete Pattern",
            f"Are you sure you want to delete '{self._current_pattern.name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self._delete_current_pattern()

    def _delete_current_pattern(self) -> None:
        """Delete the current pattern from JSON file."""
        import json

        if not self._current_pattern:
            return

        try:
            with open(self._patterns_file, 'r') as f:
                data = json.load(f)

            # Remove the pattern
            data['patterns'] = [
                p for p in data.get('patterns', [])
                if p['id'] != self._current_pattern.id
            ]

            with open(self._patterns_file, 'w') as f:
                json.dump(data, f, indent=4)

            self._status_bar.showMessage(f"Pattern '{self._current_pattern.name}' deleted")
            self._reload_patterns()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete pattern: {e}")

    def _reload_patterns(self) -> None:
        """Reload patterns after editing."""
        current_id = None
        if self._current_pattern:
            current_id = self._current_pattern.id

        self._pattern_loader = PatternLoader(self._patterns_file)
        self._load_patterns()

        # Try to reselect the same pattern
        if current_id:
            for i in range(self._pattern_combo.count()):
                if self._pattern_combo.itemData(i) == current_id:
                    self._pattern_combo.setCurrentIndex(i)
                    break

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close."""
        event.accept()
