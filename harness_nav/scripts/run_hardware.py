#!/usr/bin/env python3
"""
Main application entry point for BeagleBone Black hardware mode.

This script runs the LED Pattern Tester in hardware mode with:
- GPIO-based limit switch and metal plate detection
- Buzzer feedback
- Auto-start capability
"""

import sys
import signal
import logging
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from harness_nav.gui.main_window import MainWindow
from harness_nav.hal.switch.switch_handler import DualSwitchHandler
from harness_nav.hal.buzzer.buzzer_driver import BuzzerDriver

# Configure logging
def setup_logging():
    """Setup logging with platform-appropriate file path."""
    handlers = [logging.StreamHandler()]

    # Add file handler only on Linux (BeagleBone)
    if sys.platform.startswith('linux'):
        try:
            handlers.append(logging.FileHandler('/var/log/harness_nav.log'))
        except PermissionError:
            # Fall back to home directory if /var/log not writable
            log_file = Path.home() / 'harness_nav.log'
            handlers.append(logging.FileHandler(str(log_file)))

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

setup_logging()
logger = logging.getLogger(__name__)

# ============================================================
# HARDWARE PIN CONFIGURATION - Adjust these for your setup
# ============================================================
LIMIT_SWITCH_PIN = "P9_12"   # GPIO for limit switch (wire lock)
METAL_PLATE_PIN = "P9_14"    # GPIO for metal plate (verify)
BUZZER_PIN = "P9_16"         # PWM for buzzer
DEBOUNCE_MS = 50             # Debounce time in milliseconds

# Buzzer frequencies
LOCK_FREQ = 1500             # Hz - short beep when wire locked
LOCK_DURATION = 100          # ms
VERIFY_FREQ = 2500           # Hz - longer beep when verified
VERIFY_DURATION = 200        # ms


class HarnessNavApp:
    """Main application controller for hardware mode."""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.window = None
        self.switch = None
        self.buzzer = None

        # Handle Ctrl+C gracefully
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Timer to allow signal handling in Qt event loop
        self._signal_timer = QTimer()
        self._signal_timer.timeout.connect(lambda: None)
        self._signal_timer.start(100)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.cleanup()
        self.app.quit()

    def setup(self):
        """Initialize all components."""
        logger.info("Starting Harness Navigation System...")

        # Patterns file path
        patterns_file = PROJECT_ROOT / "harness_nav" / "data" / "patterns.json"

        # Create main window
        self.window = MainWindow(patterns_file=str(patterns_file))
        self.window.setWindowTitle("Harness Navigation System")

        # Enable hardware mode (hides test buttons)
        self.window.set_hardware_mode(True)

        # Initialize buzzer
        logger.info(f"Initializing buzzer on pin {BUZZER_PIN}")
        self.buzzer = BuzzerDriver(
            pwm_pin=BUZZER_PIN,
            lock_freq=LOCK_FREQ,
            lock_duration=LOCK_DURATION,
            verify_freq=VERIFY_FREQ,
            verify_duration=VERIFY_DURATION
        )

        # Initialize dual switch handler
        logger.info(f"Initializing switches: limit={LIMIT_SWITCH_PIN}, plate={METAL_PLATE_PIN}")
        self.switch = DualSwitchHandler(
            limit_switch_pin=LIMIT_SWITCH_PIN,
            metal_plate_pin=METAL_PLATE_PIN,
            debounce_ms=DEBOUNCE_MS
        )

        # Connect hardware callbacks
        self.switch.set_lock_callback(self._on_lock_switch)
        self.switch.set_verify_callback(self._on_verify_switch)

        # Start monitoring switches
        self.switch.start_monitoring()

        logger.info("Hardware initialization complete")

    def _on_lock_switch(self):
        """Called when limit switch detects wire is locked."""
        logger.debug("Lock switch triggered")
        if self.window.trigger_lock():
            self.buzzer.beep_lock()
            logger.info("Wire locked successfully")

    def _on_verify_switch(self):
        """Called when metal plate detects circuit complete."""
        logger.debug("Verify switch triggered")
        if self.window.trigger_verify():
            self.buzzer.beep_verify()
            logger.info("Wire verified successfully")

    def run(self):
        """Run the application."""
        self.setup()

        # Show window (fullscreen for embedded display)
        # self.window.showFullScreen()  # Uncomment for fullscreen
        self.window.show()

        logger.info("Application started")
        return self.app.exec_()

    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up...")
        if self.switch:
            self.switch.cleanup()
        if self.buzzer:
            self.buzzer.cleanup()
        logger.info("Cleanup complete")


def main():
    """Entry point."""
    try:
        app = HarnessNavApp()
        exit_code = app.run()
        app.cleanup()
        sys.exit(exit_code)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
