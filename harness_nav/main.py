#!/usr/bin/env python3
"""
Harness Navigation System - Main Entry Point

A GUI-controlled harness navigation system for wire connectivity testing.
Designed for BeagleBone Black with WS2812 LED matrix and PyQt5 interface.
"""

import sys
import os
import logging
from pathlib import Path
from typing import Optional

import yaml
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT.parent))

from harness_nav.hal.led_matrix import LEDMatrix, MockLEDMatrix
from harness_nav.hal.switch import SwitchHandler, MockSwitchHandler
from harness_nav.hal.buzzer import BuzzerDriver, MockBuzzerDriver
from harness_nav.core.test_coordinator import TestCoordinator
from harness_nav.core.patterns.models import TestState, PointStatus, TestPoint
from harness_nav.gui.main_window import MainWindow


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HarnessNavApp:
    """Main application class that ties all components together."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the application.

        Args:
            config_path: Path to settings.yaml (uses default if None)
        """
        self._config = self._load_config(config_path)
        self._app: Optional[QApplication] = None
        self._window: Optional[MainWindow] = None
        self._coordinator: Optional[TestCoordinator] = None

        # Hardware components
        self._led_matrix = None
        self._switch = None
        self._buzzer = None

    def _load_config(self, config_path: Optional[str] = None) -> dict:
        """Load configuration from YAML file."""
        if config_path is None:
            config_path = PROJECT_ROOT / "config" / "settings.yaml"

        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
                logger.info(f"Loaded configuration from {config_path}")
                return config
        else:
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return self._default_config()

    def _default_config(self) -> dict:
        """Return default configuration."""
        return {
            'display': {
                'width': 64,
                'height': 64,
                'refresh_rate_hz': 30
            },
            'led_matrix': {
                'gpio_pin': 'P8_11',
                'brightness': 128
            },
            'switch': {
                'gpio_pin': 'P9_12',
                'debounce_ms': 50
            },
            'buzzer': {
                'pwm_pin': 'P9_14',
                'success_freq': 2000,
                'success_duration_ms': 200,
                'error_freq': 500,
                'error_duration_ms': 500
            },
            'paths': {
                'patterns_dir': './data'
            }
        }

    def _init_hardware(self) -> None:
        """Initialize hardware components."""
        config = self._config

        # LED Matrix
        led_config = config.get('led_matrix', {})
        display_config = config.get('display', {})

        self._led_matrix = LEDMatrix()
        self._led_matrix.init(
            width=display_config.get('width', 64),
            height=display_config.get('height', 64),
            gpio_pin=led_config.get('gpio_pin', 'P8_11')
        )
        self._led_matrix.set_brightness(led_config.get('brightness', 128))

        # Switch
        switch_config = config.get('switch', {})
        self._switch = SwitchHandler(
            gpio_pin=switch_config.get('gpio_pin', 'P9_12'),
            debounce_ms=switch_config.get('debounce_ms', 50)
        )

        # Buzzer
        buzzer_config = config.get('buzzer', {})
        self._buzzer = BuzzerDriver(
            pwm_pin=buzzer_config.get('pwm_pin', 'P9_14'),
            success_freq=buzzer_config.get('success_freq', 2000),
            success_duration=buzzer_config.get('success_duration_ms', 200),
            error_freq=buzzer_config.get('error_freq', 500),
            error_duration=buzzer_config.get('error_duration_ms', 500)
        )

        logger.info("Hardware components initialized")

    def _init_coordinator(self) -> None:
        """Initialize the test coordinator."""
        self._coordinator = TestCoordinator(
            led_matrix=self._led_matrix,
            switch=self._switch,
            buzzer=self._buzzer
        )

        # Set up coordinator callbacks
        self._coordinator.set_callbacks(
            on_state_change=self._on_state_change,
            on_point_update=self._on_point_update,
            on_progress_update=self._on_progress_update,
            on_active_point_change=self._on_active_point_change,
            on_test_complete=self._on_test_complete
        )

        logger.info("Test coordinator initialized")

    def _init_gui(self) -> None:
        """Initialize the GUI."""
        patterns_dir = self._config.get('paths', {}).get('patterns_dir', './data')

        # Resolve relative path
        if not os.path.isabs(patterns_dir):
            patterns_dir = str(PROJECT_ROOT / patterns_dir)

        self._window = MainWindow(patterns_dir=patterns_dir)

        # Set up window callbacks
        self._window.set_callbacks(
            on_start_test=self._on_start_test,
            on_stop_test=self._on_stop_test,
            on_reset=self._on_reset,
            on_point_selected=self._on_point_selected,
            on_manual_switch=self._on_manual_switch
        )

        logger.info("GUI initialized")

    # Callback handlers

    def _on_state_change(self, state: TestState) -> None:
        """Handle state change from coordinator."""
        if self._window:
            # Use QTimer to ensure GUI update happens on main thread
            QTimer.singleShot(0, lambda: self._window.set_test_state(state))

    def _on_point_update(self, x: int, y: int, status: PointStatus) -> None:
        """Handle point status update from coordinator."""
        if self._window:
            QTimer.singleShot(0, lambda: self._window.update_point_status(x, y, status))

    def _on_progress_update(self, verified: int, total: int) -> None:
        """Handle progress update from coordinator."""
        if self._window:
            QTimer.singleShot(0, lambda: self._window.update_progress(verified, total))

    def _on_active_point_change(self, point: Optional[TestPoint]) -> None:
        """Handle active point change from coordinator."""
        if self._window:
            if point:
                QTimer.singleShot(0, lambda: self._window.set_active_point(
                    point.x, point.y, point.description, point.sequence
                ))
            else:
                QTimer.singleShot(0, lambda: self._window._control_panel.clear_current_point())

    def _on_test_complete(self) -> None:
        """Handle test completion."""
        if self._window:
            QTimer.singleShot(0, lambda: self._window.show_message(
                "Test Complete! All points verified."
            ))

    def _on_start_test(self) -> None:
        """Handle start test from GUI."""
        if self._coordinator and self._window:
            harness = self._window.current_harness
            pattern = self._window.current_pattern
            if harness and pattern:
                self._coordinator.set_harness(harness)
                self._coordinator.set_wire_type(pattern.wire_type)
                self._coordinator.start_test()

    def _on_stop_test(self) -> None:
        """Handle stop test from GUI."""
        if self._coordinator:
            self._coordinator.stop_test()

    def _on_reset(self) -> None:
        """Handle reset from GUI."""
        if self._coordinator:
            self._coordinator.reset_pattern()

    def _on_point_selected(self, x: int, y: int) -> None:
        """Handle point selection from GUI."""
        if self._coordinator:
            self._coordinator.select_point(x, y)

    def _on_manual_switch(self) -> None:
        """Handle manual switch press from GUI."""
        if self._coordinator:
            self._coordinator.simulate_switch_press()

    def run(self) -> int:
        """
        Run the application.

        Returns:
            Exit code (0 for success)
        """
        try:
            # Create Qt application
            self._app = QApplication(sys.argv)
            self._app.setApplicationName("Harness Navigation System")
            self._app.setOrganizationName("HarnessNav")

            # Initialize components
            self._init_hardware()
            self._init_coordinator()
            self._init_gui()

            # Show window
            self._window.show()

            logger.info("Application started")

            # Run event loop
            return self._app.exec_()

        except Exception as e:
            logger.exception(f"Application error: {e}")
            return 1

        finally:
            self._cleanup()

    def _cleanup(self) -> None:
        """Clean up resources on exit."""
        logger.info("Cleaning up...")

        if self._coordinator:
            self._coordinator.cleanup()

        if self._led_matrix:
            self._led_matrix.cleanup()

        if self._switch:
            self._switch.cleanup()

        if self._buzzer:
            self._buzzer.cleanup()

        logger.info("Cleanup complete")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Harness Navigation System"
    )
    parser.add_argument(
        '-c', '--config',
        help='Path to configuration file',
        default=None
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    app = HarnessNavApp(config_path=args.config)
    sys.exit(app.run())


if __name__ == '__main__':
    main()
