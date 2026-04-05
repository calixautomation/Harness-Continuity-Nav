"""Pattern Editor Dialog for creating and editing LED patterns."""

import json
from typing import Optional, List, Set
from pathlib import Path
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit,
    QGroupBox, QMessageBox, QWidget, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


class LEDToggleButton(QPushButton):
    """LED button that can be toggled on/off for pattern creation."""

    def __init__(self, led_num: int, parent=None):
        super().__init__(parent)
        self.led_num = led_num
        self.selected = False

        self.setFixedSize(50, 50)
        self.setCheckable(True)
        self.setText(str(led_num))

        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        self.setFont(font)

        self.update_style()
        self.toggled.connect(self._on_toggled)

    def _on_toggled(self, checked: bool) -> None:
        self.selected = checked
        self.update_style()

    def update_style(self) -> None:
        if self.selected:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #FFFF00;
                    color: #000000;
                    border: 2px solid #888800;
                    border-radius: 6px;
                    font-weight: bold;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #404040;
                    color: #888888;
                    border: 2px solid #555555;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #505050;
                    border: 2px solid #777777;
                }
            """)

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        self.setChecked(selected)
        self.update_style()


class PatternEditorDialog(QDialog):
    """Dialog for creating and editing LED patterns."""

    pattern_saved = pyqtSignal()  # Emitted when a pattern is saved

    def __init__(self, patterns_file: str, parent=None):
        super().__init__(parent)
        self._patterns_file = Path(patterns_file)
        self._led_buttons: dict = {}
        self._editing_pattern_id: Optional[str] = None

        self.setWindowTitle("Pattern Editor")
        self.setMinimumSize(700, 600)
        self._setup_ui()
        self._apply_styles()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Instructions
        instructions = QLabel(
            "Click LEDs to select/deselect them for the pattern.\n"
            "Yellow = Selected for pattern"
        )
        instructions.setAlignment(Qt.AlignCenter)
        instructions.setStyleSheet("color: #AAAAAA; font-style: italic;")
        layout.addWidget(instructions)

        # LED Grid
        grid_group = QGroupBox("Select LEDs for Pattern")
        grid_layout = QGridLayout(grid_group)
        grid_layout.setSpacing(4)

        for row in range(8):
            for col in range(8):
                led_num = row * 8 + col + 1
                btn = LEDToggleButton(led_num)
                grid_layout.addWidget(btn, row, col)
                self._led_buttons[led_num] = btn

        layout.addWidget(grid_group)

        # Quick selection buttons
        quick_group = QGroupBox("Quick Select")
        quick_layout = QHBoxLayout(quick_group)

        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self._select_all)
        quick_layout.addWidget(select_all_btn)

        clear_all_btn = QPushButton("Clear All")
        clear_all_btn.clicked.connect(self._clear_all)
        quick_layout.addWidget(clear_all_btn)

        select_row_btn = QPushButton("Select Row 1")
        select_row_btn.clicked.connect(lambda: self._select_row(1))
        quick_layout.addWidget(select_row_btn)

        select_corners_btn = QPushButton("Select Corners")
        select_corners_btn.clicked.connect(self._select_corners)
        quick_layout.addWidget(select_corners_btn)

        layout.addWidget(quick_group)

        # Pattern details
        details_group = QGroupBox("Pattern Details")
        details_layout = QVBoxLayout(details_group)

        # Pattern name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("e.g., Pattern 1")
        name_layout.addWidget(self._name_input)
        details_layout.addLayout(name_layout)

        # Pattern description
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self._desc_input = QLineEdit()
        self._desc_input.setPlaceholderText("e.g., Power connections")
        desc_layout.addWidget(self._desc_input)
        details_layout.addLayout(desc_layout)

        # Selected LEDs display
        self._selected_label = QLabel("Selected LEDs: None")
        self._selected_label.setStyleSheet("color: #FFFF00;")
        details_layout.addWidget(self._selected_label)

        layout.addWidget(details_group)

        # Buttons
        btn_layout = QHBoxLayout()

        self._save_btn = QPushButton("Save Pattern")
        self._save_btn.setMinimumHeight(40)
        self._save_btn.clicked.connect(self._save_pattern)
        self._save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2E7D32;
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #388E3C; }
        """)
        btn_layout.addWidget(self._save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

        # Connect LED buttons to update selected label
        for btn in self._led_buttons.values():
            btn.toggled.connect(self._update_selected_label)

    def _apply_styles(self) -> None:
        self.setStyleSheet("""
            QDialog { background-color: #2D2D2D; }
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
            QLineEdit {
                background-color: #404040;
                color: #FFFFFF;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 8px;
                font-size: 13px;
            }
            QPushButton {
                background-color: #404040;
                color: #FFFFFF;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 8px 15px;
            }
            QPushButton:hover { background-color: #505050; }
        """)

    def _get_selected_leds(self) -> List[int]:
        """Get list of selected LED numbers."""
        return sorted([
            led_num for led_num, btn in self._led_buttons.items()
            if btn.selected
        ])

    def _update_selected_label(self) -> None:
        """Update the selected LEDs display."""
        selected = self._get_selected_leds()
        if selected:
            self._selected_label.setText(f"Selected LEDs: {', '.join(map(str, selected))}")
        else:
            self._selected_label.setText("Selected LEDs: None")

    def _select_all(self) -> None:
        for btn in self._led_buttons.values():
            btn.set_selected(True)
        self._update_selected_label()

    def _clear_all(self) -> None:
        for btn in self._led_buttons.values():
            btn.set_selected(False)
        self._update_selected_label()

    def _select_row(self, row: int) -> None:
        """Select all LEDs in a row (1-8)."""
        self._clear_all()
        start = (row - 1) * 8 + 1
        for led_num in range(start, start + 8):
            self._led_buttons[led_num].set_selected(True)
        self._update_selected_label()

    def _select_corners(self) -> None:
        """Select corner LEDs."""
        self._clear_all()
        for led_num in [1, 8, 57, 64]:
            self._led_buttons[led_num].set_selected(True)
        self._update_selected_label()

    def _save_pattern(self) -> None:
        """Save the pattern to JSON file."""
        name = self._name_input.text().strip()
        description = self._desc_input.text().strip()
        selected_leds = self._get_selected_leds()

        # Validation
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a pattern name.")
            return

        if not selected_leds:
            QMessageBox.warning(self, "Error", "Please select at least one LED.")
            return

        # Generate ID from name
        pattern_id = name.lower().replace(" ", "_").replace("-", "_")

        # Load existing patterns
        patterns_data = {"patterns": []}
        if self._patterns_file.exists():
            try:
                with open(self._patterns_file, 'r') as f:
                    patterns_data = json.load(f)
            except:
                pass

        # Check for duplicate ID
        existing_ids = [p['id'] for p in patterns_data.get('patterns', [])]
        if pattern_id in existing_ids and pattern_id != self._editing_pattern_id:
            # Add number suffix
            counter = 2
            new_id = f"{pattern_id}_{counter}"
            while new_id in existing_ids:
                counter += 1
                new_id = f"{pattern_id}_{counter}"
            pattern_id = new_id

        # Create pattern entry
        new_pattern = {
            "id": pattern_id,
            "name": name,
            "description": description or f"LEDs {', '.join(map(str, selected_leds))}",
            "leds": selected_leds
        }

        # Add or update pattern
        if self._editing_pattern_id:
            # Update existing
            for i, p in enumerate(patterns_data['patterns']):
                if p['id'] == self._editing_pattern_id:
                    patterns_data['patterns'][i] = new_pattern
                    break
        else:
            # Add new
            patterns_data['patterns'].append(new_pattern)

        # Save to file
        try:
            with open(self._patterns_file, 'w') as f:
                json.dump(patterns_data, f, indent=4)

            QMessageBox.information(
                self, "Success",
                f"Pattern '{name}' saved!\n\nLEDs: {', '.join(map(str, selected_leds))}"
            )
            self.pattern_saved.emit()
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save pattern: {e}")

    def load_pattern(self, pattern_id: str) -> None:
        """Load an existing pattern for editing."""
        if not self._patterns_file.exists():
            return

        try:
            with open(self._patterns_file, 'r') as f:
                data = json.load(f)

            for pattern in data.get('patterns', []):
                if pattern['id'] == pattern_id:
                    self._editing_pattern_id = pattern_id
                    self._name_input.setText(pattern.get('name', ''))
                    self._desc_input.setText(pattern.get('description', ''))

                    self._clear_all()
                    for led_num in pattern.get('leds', []):
                        if led_num in self._led_buttons:
                            self._led_buttons[led_num].set_selected(True)

                    self._update_selected_label()
                    self.setWindowTitle(f"Edit Pattern: {pattern.get('name', '')}")
                    break

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load pattern: {e}")

    def set_selected_leds(self, leds: List[int]) -> None:
        """Set selected LEDs programmatically."""
        self._clear_all()
        for led_num in leds:
            if led_num in self._led_buttons:
                self._led_buttons[led_num].set_selected(True)
        self._update_selected_label()
