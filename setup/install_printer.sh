#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RULES_SRC="$SCRIPT_DIR/99-thermal-printer.rules"
RULES_DST="/etc/udev/rules.d/99-thermal-printer.rules"

if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root (use sudo)."
    exit 1
fi

if [ ! -f "$RULES_SRC" ]; then
    echo "udev rules file not found: $RULES_SRC"
    exit 1
fi

# Walk up until we find the real project venv (not main/ota-update.py)
PROJECT_DIR=""
SEARCH="$SCRIPT_DIR"
while [ "$SEARCH" != "/" ]; do
    if [ -x "$SEARCH/venv/bin/pip" ]; then
        PROJECT_DIR="$SEARCH"
        break
    fi
    SEARCH="$(cd "$SEARCH/.." && pwd)"
done

# Optional: pyusb in the app venv only. Never use system pip
# (Raspberry Pi OS Bookworm is an externally-managed environment).
REAL_USER="${SUDO_USER:-$(logname 2>/dev/null || true)}"
if [ -n "$PROJECT_DIR" ] && [ -n "$REAL_USER" ]; then
    echo "Ensuring pyusb is installed in $PROJECT_DIR/venv ..."
    sudo -u "$REAL_USER" "$PROJECT_DIR/venv/bin/pip" install "pyusb>=1.2.1" \
        || echo "Warning: could not install pyusb; continuing with udev setup."
else
    echo "No project venv found; skipping Python package install."
fi

# Install libusb system library if missing
if ! dpkg -s libusb-1.0-0 >/dev/null 2>&1; then
    echo "Installing libusb system library..."
    apt-get install -y libusb-1.0-0
fi

# Install udev rule so the printer is usable without root
cp "$RULES_SRC" "$RULES_DST"
udevadm control --reload-rules
udevadm trigger

echo "Printer setup complete."
echo "Unplug and re-plug the printer, then restart the app."
