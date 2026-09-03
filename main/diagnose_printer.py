#!/usr/bin/env python3
"""
Thermal printer diagnostics.

Tries every way of reaching the printer and reports exactly which one works.
Run on the Pi:

    cd /home/jdrevnyak/id
    source venv/bin/activate
    python main/diagnose_printer.py
"""

import glob
import os
import subprocess
import sys

VID = 0x0416
PID = 0x5011
TEST_BYTES = b"\x1b@IdPass diagnostic\n\n\n\n"


def sh(cmd):
    try:
        out = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=15
        )
        return (out.stdout + out.stderr).strip()
    except Exception as e:
        return f"(failed: {e})"


def section(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def system_info():
    section("1. SYSTEM / USB STATE")
    print(f"user: {sh('whoami')}   groups: {sh('groups')}")
    print("\n-- lsusb --")
    print(sh("lsusb"))

    print("\n-- usblp kernel module --")
    lsmod = sh("lsmod | grep usblp")
    print(lsmod or "usblp NOT loaded")

    print("\n-- devices bound to usblp --")
    bound = sh("ls -1 /sys/bus/usb/drivers/usblp/ 2>/dev/null | grep -v bind")
    print(bound or "(nothing bound)")

    print("\n-- /dev/usb/lp* --")
    print(sh("ls -l /dev/usb/lp* 2>/dev/null") or "(none)")

    print("\n-- serial ports --")
    print(sh("ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null") or "(none)")

    print("\n-- raw usb node permissions --")
    print(sh(f"lsusb -d {VID:04x}:{PID:04x}") or "(printer not in lsusb!)")
    print(sh("ls -l /dev/bus/usb/*/* 2>/dev/null | head -20"))

    print("\n-- udev rule installed? --")
    print(sh("cat /etc/udev/rules.d/99-thermal-printer.rules 2>/dev/null") or "(no rule)")

    print("\n-- endpoints --")
    print(sh(f"lsusb -v -d {VID:04x}:{PID:04x} 2>/dev/null | grep -E 'bInterfaceClass|bEndpointAddress|Transfer Type|bInterfaceNumber'")
          or "(need sudo for -v, try: sudo lsusb -v -d 0416:5011)")

    print("\n-- recent kernel messages --")
    print(sh("dmesg 2>/dev/null | tail -20") or "(need sudo: sudo dmesg | tail -20)")


def test_lp_node():
    section("2. TEST: /dev/usb/lp* (kernel usblp driver)")
    nodes = sorted(glob.glob("/dev/usb/lp*"))
    if not nodes:
        print("SKIP: no /dev/usb/lp* node.")
        print("      The installed udev rule unbinds usblp, so this is expected.")
        return False
    for node in nodes:
        try:
            with open(node, "wb") as f:
                f.write(TEST_BYTES)
                f.flush()
            print(f"SUCCESS: wrote to {node} — printer should have printed.")
            return True
        except Exception as e:
            print(f"FAILED {node}: {type(e).__name__}: {e}")
    return False


def test_serial():
    section("3. TEST: serial port (virtual COM)")
    try:
        import serial
        import serial.tools.list_ports
    except ImportError:
        print("SKIP: pyserial not installed.")
        return False

    ports = [
        p.device
        for p in serial.tools.list_ports.comports()
        if p.vid == VID and p.pid == PID
    ]
    if not ports:
        print("SKIP: no serial port with 0416:5011.")
        return False

    for port in ports:
        for baud in (9600, 19200, 38400, 115200):
            try:
                with serial.Serial(port, baud, timeout=2, write_timeout=5) as s:
                    s.write(TEST_BYTES)
                    s.flush()
                print(f"SUCCESS: wrote to {port} @ {baud}")
                return True
            except Exception as e:
                print(f"FAILED {port}@{baud}: {type(e).__name__}: {e}")
    return False


def test_pyusb():
    section("4. TEST: direct pyusb bulk write")
    try:
        import usb.core
        import usb.util
    except ImportError:
        print("SKIP: pyusb not installed.")
        return False

    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        print("FAILED: device not found by pyusb (permissions? unplugged?).")
        return False

    print(f"Found device on bus {dev.bus} address {dev.address}")

    try:
        active = dev.is_kernel_driver_active(0)
        print(f"kernel driver active on interface 0: {active}")
        if active:
            dev.detach_kernel_driver(0)
            print("detached kernel driver")
    except NotImplementedError:
        print("kernel driver check not supported on this platform")
    except Exception as e:
        print(f"kernel driver check/detach failed: {type(e).__name__}: {e}")

    try:
        dev.set_configuration()
        print("set_configuration OK")
    except Exception as e:
        print(f"set_configuration: {type(e).__name__}: {e}")

    try:
        cfg = dev.get_active_configuration()
    except Exception as e:
        print(f"FAILED get_active_configuration: {e}")
        return False

    out_eps = []
    for intf in cfg:
        for ep in intf:
            if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_OUT:
                if usb.util.endpoint_type(ep.bmAttributes) == usb.util.ENDPOINT_TYPE_BULK:
                    out_eps.append((intf.bInterfaceNumber, ep.bEndpointAddress))

    print(f"bulk OUT endpoints found: {[(i, hex(a)) for i, a in out_eps]}")
    if not out_eps:
        print("FAILED: no bulk OUT endpoint.")
        return False

    for intf_num, addr in out_eps:
        try:
            print(f"\n-> writing {len(TEST_BYTES)} bytes to interface {intf_num} endpoint {hex(addr)} (5s timeout)")
            written = dev.write(addr, TEST_BYTES, 5000)
            print(f"SUCCESS: wrote {written} bytes — printer should have printed.")
            return True
        except Exception as e:
            print(f"FAILED endpoint {hex(addr)}: {type(e).__name__}: {e}")
            if "110" in str(e) or "timed out" in str(e).lower():
                print("   Errno 110 = printer accepted no data.")
                print("   Usually: printer powered off, cover open, out of paper,")
                print("   or another process holds the interface.")
            try:
                dev.clear_halt(addr)
                print("   cleared halt, retrying once...")
                written = dev.write(addr, TEST_BYTES, 5000)
                print(f"   SUCCESS after clear_halt: wrote {written} bytes")
                return True
            except Exception as e2:
                print(f"   retry failed: {type(e2).__name__}: {e2}")
    return False


def main():
    print("IdPass thermal printer diagnostics")
    print(f"looking for {VID:04x}:{PID:04x}")
    if os.geteuid() != 0:
        print("\nNOTE: not running as root. If everything fails, retry with:")
        print("      sudo venv/bin/python main/diagnose_printer.py")

    system_info()
    results = {
        "/dev/usb/lp*": test_lp_node(),
        "serial": test_serial(),
        "pyusb bulk": test_pyusb(),
    }

    section("SUMMARY")
    for name, ok in results.items():
        print(f"  {name:15s} {'WORKS' if ok else 'failed/skipped'}")

    if not any(results.values()):
        print("\nNothing could write to the printer. Check in this order:")
        print("  1. Printer power switch ON and power adapter connected")
        print("     (the USB chip enumerates even with the printer unpowered)")
        print("  2. Paper loaded and the cover latched shut")
        print("  3. Press the feed button — if no paper moves, it is not printing-ready")
        print("  4. Try a different USB cable (some are charge-only)")
    else:
        print("\nUse the method marked WORKS as the printer backend.")


if __name__ == "__main__":
    sys.exit(main())
