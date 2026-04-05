#!/usr/bin/env python3
"""
Desktop entry point for LED Pattern Tester.

This script runs the application in test mode (with visible Lock/Verify buttons)
for development and testing on a PC before deploying to BeagleBone Black.

Usage:
    python run_desktop.py
"""

import sys
import logging
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PyQt5.QtWidgets import QApplication

from harness_nav.gui.main_window import MainWindow


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run the desktop application."""
    logger.info("Starting LED Pattern Tester (Desktop Mode)...")

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("LED Pattern Tester")

    # Patterns file path
    patterns_file = PROJECT_ROOT / "harness_nav" / "data" / "patterns.json"

    # Create main window (test mode - buttons visible)
    window = MainWindow(patterns_file=str(patterns_file))
    window.setWindowTitle("LED Pattern Tester - Desktop Mode")

    # Hardware mode OFF = test buttons visible
    window.set_hardware_mode(False)

    window.show()

    logger.info("Application started")
    logger.info("Keyboard shortcuts: Escape, Ctrl+Q, or F10 to exit")

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
