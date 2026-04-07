#!/bin/bash
#
# Installation script for Harness Navigation System on BeagleBone Black
#
# Run this script on the BeagleBone Black after copying files:
#   chmod +x install.sh && sudo ./install.sh
#

set -e

echo "=========================================="
echo "Harness Navigation System - Installation"
echo "=========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root: sudo ./install.sh"
    exit 1
fi

# Define paths
INSTALL_DIR="/home/debian/HarnessNav"
SERVICE_FILE="/etc/systemd/system/harness-nav.service"
LOG_FILE="/var/log/harness_nav.log"

# Check if project directory exists
if [ ! -d "$INSTALL_DIR" ]; then
    echo "Error: Project directory not found at $INSTALL_DIR"
    echo "Please copy the project first:"
    echo "  scp -r HarnessNav debian@beaglebone.local:~/"
    exit 1
fi

echo "[1/6] Installing system dependencies..."
apt-get update
apt-get install -y python3-pip python3-pyqt5 python3-yaml

echo "[2/6] Installing Python packages..."
pip3 install PyYAML Adafruit_BBIO || echo "Note: Adafruit_BBIO may already be installed"

echo "[3/6] Setting permissions..."
chmod +x "$INSTALL_DIR/harness_nav/scripts/run_hardware.py"
chown -R debian:debian "$INSTALL_DIR"

echo "[4/6] Creating log file..."
touch "$LOG_FILE"
chown debian:debian "$LOG_FILE"

echo "[5/6] Installing systemd service..."
cp "$INSTALL_DIR/deploy/harness-nav.service" "$SERVICE_FILE"
systemctl daemon-reload
systemctl enable harness-nav.service

echo "[6/6] Installation complete!"
echo ""
echo "=========================================="
echo "Next steps:"
echo "=========================================="
echo ""
echo "1. Edit pin configuration if needed:"
echo "   nano $INSTALL_DIR/harness_nav/scripts/run_hardware.py"
echo ""
echo "2. Start the service:"
echo "   sudo systemctl start harness-nav"
echo ""
echo "3. Check service status:"
echo "   sudo systemctl status harness-nav"
echo ""
echo "4. View logs:"
echo "   journalctl -u harness-nav -f"
echo "   cat /var/log/harness_nav.log"
echo ""
echo "5. Reboot to test auto-start:"
echo "   sudo reboot"
echo ""
echo "=========================================="
