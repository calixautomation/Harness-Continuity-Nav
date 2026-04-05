#!/bin/bash
# Deploy Harness Navigation System to BeagleBone Black
# Usage: ./deploy_to_beaglebone.sh [beaglebone_ip]

set -e

# Configuration
BBB_USER="debian"
BBB_HOST="${1:-beaglebone.local}"
BBB_DIR="/home/debian/harness_nav"
PROJECT_DIR="$(dirname "$(dirname "$(realpath "$0")")")"

echo "========================================"
echo "Deploying to BeagleBone Black"
echo "Host: $BBB_USER@$BBB_HOST"
echo "Source: $PROJECT_DIR"
echo "Target: $BBB_DIR"
echo "========================================"

# Step 1: Create directory on BeagleBone
echo ""
echo "[1/5] Creating directory on BeagleBone..."
ssh "$BBB_USER@$BBB_HOST" "mkdir -p $BBB_DIR"

# Step 2: Sync files (exclude unnecessary files)
echo ""
echo "[2/5] Syncing files..."
rsync -avz --progress \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.git' \
    --exclude '.vscode' \
    --exclude 'venv' \
    --exclude '*.egg-info' \
    --exclude 'build' \
    --exclude 'dist' \
    --exclude 'toolchain' \
    "$PROJECT_DIR/" "$BBB_USER@$BBB_HOST:$BBB_DIR/"

# Step 3: Install dependencies on BeagleBone
echo ""
echo "[3/5] Installing dependencies on BeagleBone..."
ssh "$BBB_USER@$BBB_HOST" << 'EOF'
cd ~/harness_nav
pip3 install --user PyQt5 PyYAML

# Install Adafruit libraries for GPIO/PWM
pip3 install --user Adafruit-BBIO

# Optional: Install NeoPixel library
pip3 install --user adafruit-circuitpython-neopixel adafruit-blinka
EOF

# Step 4: Set up autostart (optional)
echo ""
echo "[4/5] Setting up autostart service..."
ssh "$BBB_USER@$BBB_HOST" << 'EOF'
# Create systemd service file
sudo tee /etc/systemd/system/harness-nav.service > /dev/null << 'SERVICE'
[Unit]
Description=Harness Navigation System
After=graphical.target

[Service]
Type=simple
User=debian
Environment=DISPLAY=:0
WorkingDirectory=/home/debian/harness_nav
ExecStart=/usr/bin/python3 /home/debian/harness_nav/main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=graphical.target
SERVICE

# Reload systemd but don't enable yet
sudo systemctl daemon-reload
echo "Service created. To enable autostart, run:"
echo "  sudo systemctl enable harness-nav"
echo "  sudo systemctl start harness-nav"
EOF

# Step 5: Instructions
echo ""
echo "========================================"
echo "Deployment complete!"
echo "========================================"
echo ""
echo "To run manually on BeagleBone:"
echo "  ssh $BBB_USER@$BBB_HOST"
echo "  cd $BBB_DIR"
echo "  python3 main.py"
echo ""
echo "To enable autostart on boot:"
echo "  ssh $BBB_USER@$BBB_HOST"
echo "  sudo systemctl enable harness-nav"
echo "  sudo systemctl start harness-nav"
echo ""
echo "To view logs:"
echo "  journalctl -u harness-nav -f"
