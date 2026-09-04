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
    if [ -e "$SEARCH/venv/bin/pip" ] || [ -e "$SEARCH/venv/bin/python" ] || [ -e "$SEARCH/venv/bin/python3" ]; then
        PROJECT_DIR="$SEARCH"
        break
    fi
    SEARCH="$(cd "$SEARCH/.." && pwd)"
done

# Fallbacks for classroom Pi layouts
if [ -z "$PROJECT_DIR" ]; then
    for cand in "/home/jdrevnyak/id" "$HOME/id" /home/*/id; do
        if [ -e "$cand/venv/bin/pip" ] || [ -e "$cand/venv/bin/python3" ]; then
            PROJECT_DIR="$cand"
            break
        fi
    done
fi

# Optional: install into the app venv only. Never use system pip
# (Raspberry Pi OS Bookworm is an externally-managed environment).
REAL_USER="${SUDO_USER:-$(logname 2>/dev/null || true)}"
if [ -z "$PROJECT_DIR" ]; then
    # Create venv next to the app if missing
    for cand in "/home/jdrevnyak/id" "$HOME/id" "$(cd "$SCRIPT_DIR/../.." && pwd)" "$(cd "$SCRIPT_DIR/.." && pwd)"; do
        if [ -f "$cand/ota-update.py" ] || [ -f "$cand/start_nfc_reader.sh" ] || [ -f "$cand/main/printer.py" ]; then
            PROJECT_DIR="$cand"
            break
        fi
    done
fi

if [ -n "$PROJECT_DIR" ]; then
    if [ ! -e "$PROJECT_DIR/venv/bin/python" ] && [ ! -e "$PROJECT_DIR/venv/bin/python3" ]; then
        echo "Creating venv at $PROJECT_DIR/venv ..."
        python3 -m venv --system-site-packages "$PROJECT_DIR/venv" \
            || echo "Warning: could not create venv"
    fi
    VENV_PY=""
    for py in "$PROJECT_DIR/venv/bin/python" "$PROJECT_DIR/venv/bin/python3"; do
        if [ -e "$py" ]; then
            VENV_PY="$py"
            break
        fi
    done
    VENV_PIP="$PROJECT_DIR/venv/bin/pip"
    if [ -z "$VENV_PY" ]; then
        echo "ERROR: venv python not found under $PROJECT_DIR/venv/bin"
    else
        echo "Installing printer packages with $VENV_PY -m pip (not system pip) ..."
        if [ -n "$REAL_USER" ] && [ "$(id -u)" -eq 0 ]; then
            sudo -u "$REAL_USER" "$VENV_PY" -m pip install \
                "pyusb>=1.2.1" "pyserial>=3.5" "python-escpos==3.0a9" "Pillow" "qrcode" \
                || echo "Warning: could not install printer packages; continuing with udev setup."
            echo "python-escpos check:"
            sudo -u "$REAL_USER" "$VENV_PY" -c "import escpos; print('escpos OK', escpos.__file__)" \
                || echo "Warning: escpos import failed after install."
        else
            "$VENV_PY" -m pip install \
                "pyusb>=1.2.1" "pyserial>=3.5" "python-escpos==3.0a9" "Pillow" "qrcode" \
                || echo "Warning: could not install printer packages; continuing with udev setup."
        fi
    fi
else
    echo "No project directory found; skipping Python package install."
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
