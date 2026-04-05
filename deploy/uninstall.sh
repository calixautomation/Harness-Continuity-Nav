#!/bin/bash
#
# Uninstall script for Harness Navigation System
#

set -e

echo "Stopping service..."
systemctl stop harness-nav.service || true

echo "Disabling service..."
systemctl disable harness-nav.service || true

echo "Removing service file..."
rm -f /etc/systemd/system/harness-nav.service

echo "Reloading systemd..."
systemctl daemon-reload

echo "Uninstall complete."
echo "Note: Project files at /home/debian/HarnessNav were not removed."
