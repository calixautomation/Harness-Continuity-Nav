"""Control panel widget for test operations."""

from typing import Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QProgressBar, QFrame
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont

from ...core.patterns.models import WirePattern, TestState


class ControlPanel(QWidget):
    """
    Control panel for test operations.

    Provides:
    - Start/Stop test button
    - Reset button
    - Progress display
    - Current point information
    - Manual switch trigger (for testing)
    """

    # Signals
    start_test_clicked = pyqtSignal()
    stop_test_clicked = pyqtSignal()
    reset_clicked = pyqtSignal()
    manual_switch_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._current_state = TestState.IDLE
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Test controls group
        controls_group = QGroupBox("Test Controls")
        controls_layout = QVBoxLayout(controls_group)

        # Start/Stop button
        self._start_stop_btn = QPushButton("Start Test")
        self._start_stop_btn.setMinimumHeight(40)
        self._start_stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #2E7D32;
                color: white;
                font-weight: bold;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
            QPushButton:disabled {
                background-color: #666666;
            }
        """)
        self._start_stop_btn.clicked.connect(self._on_start_stop_clicked)
        controls_layout.addWidget(self._start_stop_btn)

        # Reset button
        self._reset_btn = QPushButton("Reset Pattern")
        self._reset_btn.clicked.connect(self.reset_clicked.emit)
        controls_layout.addWidget(self._reset_btn)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        controls_layout.addWidget(line)

        # Manual switch trigger (for development/testing)
        self._manual_switch_btn = QPushButton("Simulate Switch Press")
        self._manual_switch_btn.setToolTip("Manually trigger switch press (for testing without hardware)")
        self._manual_switch_btn.clicked.connect(self.manual_switch_clicked.emit)
        controls_layout.addWidget(self._manual_switch_btn)

        layout.addWidget(controls_group)

        # Progress group
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFormat("%v / %m points (%p%)")
        progress_layout.addWidget(self._progress_bar)

        # Status label
        self._status_label = QLabel("Status: Idle")
        self._status_label.setAlignment(Qt.AlignCenter)
        progress_layout.addWidget(self._status_label)

        layout.addWidget(progress_group)

        # Current point info group
        point_group = QGroupBox("Current Point")
        point_layout = QVBoxLayout(point_group)

        # Point coordinates
        self._point_coords_label = QLabel("Position: --")
        point_layout.addWidget(self._point_coords_label)

        # Point description
        self._point_desc_label = QLabel("Description: --")
        self._point_desc_label.setWordWrap(True)
        point_layout.addWidget(self._point_desc_label)

        # Point sequence
        self._point_seq_label = QLabel("Sequence: --")
        point_layout.addWidget(self._point_seq_label)

        layout.addWidget(point_group)

        # Add stretch at bottom
        layout.addStretch()

    def _on_start_stop_clicked(self) -> None:
        """Handle start/stop button click."""
        if self._current_state == TestState.TESTING or self._current_state == TestState.POINT_ACTIVE:
            self.stop_test_clicked.emit()
        else:
            self.start_test_clicked.emit()

    def set_state(self, state: TestState) -> None:
        """
        Update the panel based on test state.

        Args:
            state: Current test state
        """
        self._current_state = state

        state_labels = {
            TestState.IDLE: "Idle",
            TestState.HARNESS_SELECTED: "Harness Selected",
            TestState.PATTERN_LOADED: "Pattern Loaded",
            TestState.TESTING: "Testing",
            TestState.POINT_ACTIVE: "Point Active - Press Switch",
            TestState.COMPLETE: "Complete!",
        }

        self._status_label.setText(f"Status: {state_labels.get(state, 'Unknown')}")

        # Update button state and style
        if state in (TestState.TESTING, TestState.POINT_ACTIVE):
            self._start_stop_btn.setText("Stop Test")
            self._start_stop_btn.setStyleSheet("""
                QPushButton {
                    background-color: #C62828;
                    color: white;
                    font-weight: bold;
                    font-size: 14px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #D32F2F;
                }
            """)
            self._manual_switch_btn.setEnabled(True)
        elif state == TestState.COMPLETE:
            self._start_stop_btn.setText("Test Complete")
            self._start_stop_btn.setEnabled(False)
            self._manual_switch_btn.setEnabled(False)
        else:
            self._start_stop_btn.setText("Start Test")
            self._start_stop_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2E7D32;
                    color: white;
                    font-weight: bold;
                    font-size: 14px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #388E3C;
                }
                QPushButton:disabled {
                    background-color: #666666;
                }
            """)
            self._start_stop_btn.setEnabled(state != TestState.IDLE)
            self._manual_switch_btn.setEnabled(False)

        # Reset button always enabled except during active testing
        self._reset_btn.setEnabled(state not in (TestState.TESTING, TestState.POINT_ACTIVE))

    def set_progress(self, verified: int, total: int) -> None:
        """
        Update progress display.

        Args:
            verified: Number of verified points
            total: Total number of points
        """
        self._progress_bar.setMaximum(total)
        self._progress_bar.setValue(verified)
        self._progress_bar.setFormat(f"{verified} / {total} points (%p%)")

    def set_current_point(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        description: str = "--",
        sequence: Optional[int] = None
    ) -> None:
        """
        Update current point information.

        Args:
            x: X coordinate (None to clear)
            y: Y coordinate (None to clear)
            description: Point description
            sequence: Sequence number
        """
        if x is not None and y is not None:
            self._point_coords_label.setText(f"Position: ({x}, {y})")
        else:
            self._point_coords_label.setText("Position: --")

        self._point_desc_label.setText(f"Description: {description}")

        if sequence is not None:
            self._point_seq_label.setText(f"Sequence: {sequence}")
        else:
            self._point_seq_label.setText("Sequence: --")

    def clear_current_point(self) -> None:
        """Clear current point display."""
        self.set_current_point()

    def reset_progress(self) -> None:
        """Reset progress to zero."""
        self._progress_bar.setValue(0)
        self._progress_bar.setMaximum(100)
        self._progress_bar.setFormat("%v / %m points (%p%)")
        self.clear_current_point()
