#!/bin/bash
#
# Installation script for Harness Navigation System on Raspberry Pi
#
# Usage on Raspberry Pi:
#   cd HarnessNav/deploy
#   chmod +x install_rpi.sh
#   sudo ./install_rpi.sh
#
# This script will:
#   1. Install system dependencies
#   2. Enable SPI interface
#   3. Install Python packages
#   4. Set up systemd service
#   5. Configure permissions

set -e

echo "=========================================="
echo "HarnessNav - Raspberry Pi Installation"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root"
    echo "Usage: sudo ./install_rpi.sh"
    exit 1
fi

# Detect Raspberry Pi user
if id "pi" &>/dev/null; then
    INSTALL_USER="pi"
    INSTALL_HOME="/home/pi"
elif id "ubuntu" &>/dev/null; then
    INSTALL_USER="ubuntu"
    INSTALL_HOME="/home/ubuntu"
else
    echo "Error: Could not detect Raspberry Pi OS user (pi or ubuntu)"
    exit 1
fi

INSTALL_DIR="$INSTALL_HOME/HarnessNav"
SERVICE_FILE="/etc/systemd/system/harness-nav.service"
LOG_FILE="/var/log/harness_nav.log"

echo "Detected user: $INSTALL_USER"
echo "Installation directory: $INSTALL_DIR"
echo ""

# Verify project directory exists
if [ ! -d "$INSTALL_DIR" ]; then
    echo "Error: Project not found at $INSTALL_DIR"
    echo ""
    echo "Please copy the project first:"
    echo "  scp -r HarnessNav pi@raspberrypi.local:~/"
    echo ""
    exit 1
fi

# Step 1: System updates
echo "[1/7] Updating package lists..."
apt-get update -qq
apt-get upgrade -y -qq > /dev/null

# Step 2: Install system dependencies
echo "[2/7] Installing system dependencies..."
apt-get install -y \
    python3-pip \
    python3-pyqt5 \
    python3-yaml \
    python3-dev \
    git \
    build-essential \
    > /dev/null 2>&1

echo "  ✓ System packages installed"

# Step 3: Enable SPI interface
echo "[3/7] Enabling SPI interface..."
if ! grep -q "^dtparam=spi=on" /boot/config.txt 2>/dev/null; then
    echo "dtparam=spi=on" >> /boot/config.txt
    echo "  ⚠ SPI enabled - reboot required for changes to take effect"
else
    echo "  ✓ SPI already enabled"
fi

# Step 4: Configure GPIO permissions
echo "[4/7] Setting up GPIO permissions..."
if [ ! -f "/etc/udev/rules.d/99-gpio.rules" ]; then
    cat > /etc/udev/rules.d/99-gpio.rules <<EOF
SUBSYSTEM=="gpio", GROUP="gpio", MODE="0660"
SUBSYSTEM=="gpio", KERNEL=="gpiochip*", ACTION=="add", PROGRAM="/bin/sh -c 'chown root:gpio /sys/class/gpio/export /sys/class/gpio/unexport 2>/dev/null'"
EOF
    echo "  ✓ GPIO udev rules created"
fi

# Add user to gpio group
if ! id "$INSTALL_USER" | grep -q "gpio"; then
    usermod -aG gpio "$INSTALL_USER"
    echo "  ✓ Added $INSTALL_USER to gpio group"
fi

# Step 5: Install Python requirements
echo "[5/7] Installing Python packages..."
pip3 install --upgrade pip setuptools wheel > /dev/null 2>&1
pip3 install -r "$INSTALL_DIR/harness_nav/requirements.txt" > /dev/null 2>&1
echo "  ✓ Python packages installed"

# Step 6: Create systemd service
echo "[6/7] Installing systemd service..."
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Harness Navigation System
After=graphical-session.target
Wants=graphical-session.target

[Service]
Type=simple
User=$INSTALL_USER
Group=$INSTALL_USER
Environment=DISPLAY=:0
Environment=XAUTHORITY=$INSTALL_HOME/.Xauthority
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/harness_nav/scripts/run_hardware_rpi.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

# Allow GPIO access
SupplementaryGroups=gpio

[Install]
WantedBy=graphical-session.target
EOF

systemctl daemon-reload
systemctl enable harness-nav.service
echo "  ✓ Systemd service installed and enabled"

# Step 7: Create log file
echo "[7/7] Setting up logging..."
touch "$LOG_FILE"
chmod 666 "$LOG_FILE"
chown $INSTALL_USER:$INSTALL_USER "$INSTALL_DIR"
echo "  ✓ Logging configured"

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "IMPORTANT - Next steps:"
echo ""
echo "1. REBOOT REQUIRED (SPI was enabled):"
echo "   sudo reboot"
echo ""
echo "2. After reboot, verify SPI is working:"
echo "   ls -la /dev/spidev*"
echo "   (should show /dev/spidev0.0 and /dev/spidev0.1)"
echo ""
echo "3. Test GPIO access:"
echo "   python3 -c 'import RPi.GPIO as GPIO; print(\"GPIO OK\")'"
echo ""
echo "4. Start the service manually:"
echo "   sudo systemctl start harness-nav"
echo ""
echo "5. Check service status:"
echo "   sudo systemctl status harness-nav"
echo "   journalctl -u harness-nav -f"
echo ""
echo "6. View application logs:"
echo "   tail -f $LOG_FILE"
echo ""
echo "7. Enable auto-start on boot:"
echo "   sudo systemctl start harness-nav"
echo ""
echo "CONFIGURATION:"
echo "  GPIO pins: See harness_nav/config/pins_rpi.yaml"
echo "  Startup script: harness_nav/scripts/run_hardware_rpi.py"
echo ""
echo "TROUBLESHOOTING:"
echo "  - If GPIO access denied: Check gpio group membership"
echo "  - If SPI fails: Verify /boot/config.txt has dtparam=spi=on"
echo "  - If display issues: Check DISPLAY and XAUTHORITY settings"
echo ""
echo "=========================================="
