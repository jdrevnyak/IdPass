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

# The app exports the interpreter it is actually running under. Installing into
# any other venv leaves the import failing however well pip reports it went.
VENV_PY="${IDPASS_APP_PYTHON:-}"
if [ -n "$VENV_PY" ] && [ ! -e "$VENV_PY" ]; then
    echo "Ignoring IDPASS_APP_PYTHON=$VENV_PY (not found)"
    VENV_PY=""
fi

if [ -z "$VENV_PY" ] && [ -n "$PROJECT_DIR" ]; then
    if [ ! -e "$PROJECT_DIR/venv/bin/python" ] && [ ! -e "$PROJECT_DIR/venv/bin/python3" ]; then
        echo "Creating venv at $PROJECT_DIR/venv ..."
        python3 -m venv --system-site-packages "$PROJECT_DIR/venv" \
            || echo "Warning: could not create venv"
    fi
    for py in "$PROJECT_DIR/venv/bin/python" "$PROJECT_DIR/venv/bin/python3"; do
        if [ -e "$py" ]; then
            VENV_PY="$py"
            break
        fi
    done
    if [ -z "$VENV_PY" ]; then
        echo "ERROR: venv python not found under $PROJECT_DIR/venv/bin"
    fi
fi

if [ -z "$VENV_PY" ]; then
    echo "No app interpreter or project venv found; skipping Python package install."
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

# The app needs lp/plugdev for USB and dialout for serial/TTL UARTs.
if [ -n "$REAL_USER" ]; then
    usermod -aG lp,plugdev,dialout "$REAL_USER" || true
fi

# Raspberry Pi 5: enable the second UART for an embedded TTL printer.
# UART2 uses GPIO4 TX (physical pin 7) and GPIO5 RX (physical pin 29),
# appears as /dev/ttyAMA2, and does not conflict with the ESP32 on UART0.
UART2_CHANGED=0
PI_MODEL="$(tr -d '\0' < /proc/device-tree/model 2>/dev/null || true)"
if [[ "$PI_MODEL" == *"Raspberry Pi 5"* ]]; then
    BOOT_CONFIG=""
    for candidate in /boot/firmware/config.txt /boot/config.txt; do
        if [ -f "$candidate" ]; then
            BOOT_CONFIG="$candidate"
            break
        fi
    done

    if [ -n "$BOOT_CONFIG" ]; then
        if ! grep -Eq '^[[:space:]]*dtoverlay=uart2-pi5([,[:space:]]|$)' "$BOOT_CONFIG"; then
            echo >> "$BOOT_CONFIG"
            echo "# IdPass embedded TTL thermal printer" >> "$BOOT_CONFIG"
            echo "dtoverlay=uart2-pi5" >> "$BOOT_CONFIG"
            UART2_CHANGED=1
            echo "Enabled Raspberry Pi 5 UART2 in $BOOT_CONFIG"
        else
            echo "Raspberry Pi 5 UART2 is already enabled."
        fi
    else
        echo "Warning: Pi 5 detected but boot config was not found."
    fi
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
if [ "$UART2_CHANGED" -eq 1 ]; then
    echo "REBOOT REQUIRED: UART2 will appear as /dev/ttyAMA2 after reboot."
elif [[ "$PI_MODEL" == *"Raspberry Pi 5"* ]]; then
    echo "Pi 5 TTL printer port: /dev/ttyAMA2 (GPIO4 TX, physical pin 7)."
fi
