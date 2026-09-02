#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
RULES_SRC="$SCRIPT_DIR/99-thermal-printer.rules"
RULES_DST="/etc/udev/rules.d/99-thermal-printer.rules"

if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root (use sudo)."
    exit 1
fi

# Install all Python dependencies from requirements.txt into the venv
VENV_PIP="$PROJECT_DIR/venv/bin/pip"
REQ_FILE="$PROJECT_DIR/requirements.txt"
REAL_USER="${SUDO_USER:-$(logname)}"

if [ -x "$VENV_PIP" ]; then
    if [ -f "$REQ_FILE" ]; then
        echo "Installing all requirements from $REQ_FILE..."
        sudo -u "$REAL_USER" "$VENV_PIP" install -r "$REQ_FILE"
    else
        echo "No requirements.txt found — installing pyusb only."
        sudo -u "$REAL_USER" "$VENV_PIP" install "pyusb>=1.2.1"
    fi
else
    echo "No venv found at $PROJECT_DIR/venv — installing globally."
    if [ -f "$REQ_FILE" ]; then
        pip3 install -r "$REQ_FILE"
    else
        pip3 install "pyusb>=1.2.1"
    fi
fi

# Install libusb system library if missing
if ! dpkg -s libusb-1.0-0 >/dev/null 2>&1; then
    echo "Installing libusb system library..."
    apt-get install -y libusb-1.0-0
fi

# Install udev rule
cp "$RULES_SRC" "$RULES_DST"
udevadm control --reload-rules
udevadm trigger

echo "Printer setup complete."
echo "Unplug and re-plug the printer, then restart the app."
