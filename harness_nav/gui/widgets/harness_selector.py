"""Harness and wire type selector widgets."""

from typing import Optional, List, Dict
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel,
    QGroupBox, QButtonGroup, QRadioButton, QPushButton
)
from PyQt5.QtCore import pyqtSignal

from ...core.patterns.models import Harness, WirePattern


class HarnessSelector(QWidget):
    """
    Widget for selecting harness and wire type.

    Provides:
    - Dropdown for harness selection
    - Radio buttons for wire type selection
    - Signals for selection changes
    """

    # Signals
    harness_changed = pyqtSignal(str)  # Emits harness file path
    wire_type_changed = pyqtSignal(str)  # Emits wire type name

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._harness_map: Dict[str, str] = {}  # Display name -> file path
        self._current_harness: Optional[Harness] = None
        self._wire_type_buttons: Dict[str, QRadioButton] = {}

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Harness selection group
        harness_group = QGroupBox("Harness Selection")
        harness_layout = QVBoxLayout(harness_group)

        # Harness dropdown
        harness_row = QHBoxLayout()
        harness_row.addWidget(QLabel("Harness:"))
        self._harness_combo = QComboBox()
        self._harness_combo.setMinimumWidth(200)
        self._harness_combo.currentTextChanged.connect(self._on_harness_changed)
        harness_row.addWidget(self._harness_combo, 1)
        harness_layout.addLayout(harness_row)

        # Refresh button
        self._refresh_btn = QPushButton("Refresh List")
        self._refresh_btn.clicked.connect(self._on_refresh_clicked)
        harness_layout.addWidget(self._refresh_btn)

        layout.addWidget(harness_group)

        # Wire type selection group
        self._wire_group = QGroupBox("Wire Type")
        self._wire_layout = QVBoxLayout(self._wire_group)
        self._wire_button_group = QButtonGroup(self)
        self._wire_button_group.buttonClicked.connect(self._on_wire_type_changed)

        # Placeholder label when no harness loaded
        self._no_wire_label = QLabel("Load a harness to see wire types")
        self._no_wire_label.setStyleSheet("color: gray; font-style: italic;")
        self._wire_layout.addWidget(self._no_wire_label)

        layout.addWidget(self._wire_group)

        # Add stretch at bottom
        layout.addStretch()

    def set_harness_list(self, harness_map: Dict[str, str]) -> None:
        """
        Set the available harnesses.

        Args:
            harness_map: Dict mapping display name -> file path
        """
        self._harness_map = harness_map
        self._harness_combo.clear()
        self._harness_combo.addItem("-- Select Harness --")
        for name in sorted(harness_map.keys()):
            self._harness_combo.addItem(name)

    def set_current_harness(self, harness: Harness) -> None:
        """
        Set the currently loaded harness to update wire type options.

        Args:
            harness: The loaded Harness object
        """
        self._current_harness = harness
        self._update_wire_types()

    def _update_wire_types(self) -> None:
        """Update wire type radio buttons based on current harness."""
        # Clear existing wire type buttons
        for btn in self._wire_type_buttons.values():
            self._wire_button_group.removeButton(btn)
            self._wire_layout.removeWidget(btn)
            btn.deleteLater()
        self._wire_type_buttons.clear()

        if self._current_harness is None:
            self._no_wire_label.show()
            return

        self._no_wire_label.hide()

        # Create radio buttons for each wire type
        for wire_type in self._current_harness.wire_types:
            pattern = self._current_harness.get_pattern(wire_type)
            point_count = pattern.total_points if pattern else 0

            btn = QRadioButton(f"{wire_type} ({point_count} points)")
            btn.setProperty("wire_type", wire_type)
            self._wire_button_group.addButton(btn)
            self._wire_layout.addWidget(btn)
            self._wire_type_buttons[wire_type] = btn

        # Select first wire type by default
        if self._wire_type_buttons:
            first_btn = list(self._wire_type_buttons.values())[0]
            first_btn.setChecked(True)
            self._on_wire_type_changed(first_btn)

    def _on_harness_changed(self, text: str) -> None:
        """Handle harness selection change."""
        if text == "-- Select Harness --" or text not in self._harness_map:
            return
        file_path = self._harness_map[text]
        self.harness_changed.emit(file_path)

    def _on_wire_type_changed(self, button: QRadioButton) -> None:
        """Handle wire type selection change."""
        wire_type = button.property("wire_type")
        if wire_type:
            self.wire_type_changed.emit(wire_type)

    def _on_refresh_clicked(self) -> None:
        """Handle refresh button click."""
        # Parent should connect to this and reload harness list
        pass

    def get_selected_harness_path(self) -> Optional[str]:
        """Get the file path of the currently selected harness."""
        text = self._harness_combo.currentText()
        if text == "-- Select Harness --":
            return None
        return self._harness_map.get(text)

    def get_selected_wire_type(self) -> Optional[str]:
        """Get the currently selected wire type."""
        checked_btn = self._wire_button_group.checkedButton()
        if checked_btn:
            return checked_btn.property("wire_type")
        return None

    def select_wire_type(self, wire_type: str) -> None:
        """Programmatically select a wire type."""
        if wire_type in self._wire_type_buttons:
            self._wire_type_buttons[wire_type].setChecked(True)
            self.wire_type_changed.emit(wire_type)

    def clear_selection(self) -> None:
        """Clear all selections."""
        self._harness_combo.setCurrentIndex(0)
        self._current_harness = None
        self._update_wire_types()
