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
    sudo -u "$REAL_USER" "$PROJECT_DIR/venv/bin/pip" install "pyusb>=1.2.1" "pyserial>=3.5" \
        || echo "Warning: could not install pyusb; continuing with udev setup."
else
    echo "No project venv found; skipping Python package install."
fi

# The app needs to read /dev/usb/lp0 (group lp) and raw USB (group plugdev)
if [ -n "$REAL_USER" ]; then
    usermod -aG lp,plugdev "$REAL_USER" || true
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

# An earlier version of this rule unbound usblp, which removed /dev/usb/lp0 and
# left raw libusb as the only path. Put the kernel printer driver back.
modprobe usblp 2>/dev/null || true
for dev in /sys/bus/usb/devices/*; do
    [ -f "$dev/idVendor" ] || continue
    [ "$(cat "$dev/idVendor")" = "0416" ] || continue
    [ "$(cat "$dev/idProduct")" = "5011" ] || continue
    for intf in "$dev":*; do
        if [ -d "$intf" ] && [ ! -e "$intf/driver" ]; then
            echo -n "$(basename "$intf")" > /sys/bus/usb/drivers/usblp/bind 2>/dev/null || true
        fi
    done
done
sleep 1

echo
echo "Printer setup complete."
if ls /dev/usb/lp* >/dev/null 2>&1; then
    echo "Kernel printer device found: $(ls /dev/usb/lp*)"
else
    echo "No /dev/usb/lp* device. Unplug and re-plug the printer, then re-run this."
fi
echo "Group changes require a reboot (or logout) to take effect."
