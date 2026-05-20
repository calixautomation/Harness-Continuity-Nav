#!/bin/bash
# Deploy Harness Navigation System to Raspberry Pi
# Usage: ./deploy_to_raspberrypi.sh [raspberrypi_ip]

set -e

# Configuration
PI_USER="pi"
PI_HOST="${1:-raspberrypi.local}"
PI_DIR="/home/pi/harness_nav"
PROJECT_DIR="$(dirname \"$(dirname \"$(realpath \"$0\")\")\")"

echo "========================================"
echo "Deploying to Raspberry Pi"
echo "Host: $PI_USER@$PI_HOST"
echo "Source: $PROJECT_DIR"
echo "Target: $PI_DIR"
echo "========================================"

# Step 1: Create directory on Raspberry Pi
echo ""
echo "[1/5] Creating directory on Raspberry Pi..."
ssh "$PI_USER@$PI_HOST" "mkdir -p $PI_DIR"

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
    "$PROJECT_DIR/" "$PI_USER@$PI_HOST:$PI_DIR/"

# Step 3: Install dependencies on Raspberry Pi
echo ""
echo "[3/5] Installing dependencies on Raspberry Pi..."
ssh "$PI_USER@$PI_HOST" << 'EOF'
cd ~/harness_nav
pip3 install --user PyQt5 PyYAML
EOF

# Step 4: Set up autostart (optional)
echo ""
echo "[4/5] Setting up autostart service..."
ssh "$PI_USER@$PI_HOST" << 'EOF'
# Create systemd service file
sudo tee /etc/systemd/system/harness-nav.service > /dev/null << 'SERVICE'
[Unit]
Description=Harness Navigation System
After=graphical.target

[Service]
Type=simple
User=pi
Environment=DISPLAY=:0
WorkingDirectory=/home/pi/harness_nav
ExecStart=/usr/bin/python3 /home/pi/harness_nav/main.py
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
echo "To run manually on Raspberry Pi:"
echo "  ssh $PI_USER@$PI_HOST"
echo "  cd $PI_DIR"
echo "  python3 main.py"
echo ""
echo "To enable autostart on boot:"
echo "  ssh $PI_USER@$PI_HOST"
echo "  sudo systemctl enable harness-nav"
echo "  sudo systemctl start harness-nav"
echo ""
echo "To view logs:"
echo "  journalctl -u harness-nav -f"
