#!/usr/bin/env python3
"""
Thermal printer diagnostics.

Tries every way of reaching the printer and reports exactly which one works.

CLI:
    python main/diagnose_printer.py

In-app:
    from diagnose_printer import run_diagnostics
    report, results = run_diagnostics()
"""

import glob
import io
import os
import subprocess
import sys

VID = 0x0416
PID = 0x5011
TEST_BYTES = b"\x1b@IdPass diagnostic\n\n\n\n"


class _Report:
    def __init__(self):
        self._buf = io.StringIO()

    def write(self, text=""):
        self._buf.write(str(text) + "\n")

    def section(self, title):
        self.write()
        self.write("=" * 48)
        self.write(title)
        self.write("=" * 48)

    def text(self):
        return self._buf.getvalue()


def sh(cmd):
    try:
        out = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=15
        )
        return (out.stdout + out.stderr).strip()
    except Exception as e:
        return f"(failed: {e})"


def _system_info(r):
    r.section("1. SYSTEM / USB STATE")
    r.write(f"user: {sh('whoami')}   groups: {sh('groups')}")
    r.write()
    r.write("-- lsusb --")
    r.write(sh("lsusb") or "(lsusb failed)")

    r.write()
    r.write("-- usblp kernel module --")
    r.write(sh("lsmod | grep usblp") or "usblp NOT loaded")

    r.write()
    r.write("-- devices bound to usblp --")
    r.write(sh("ls -1 /sys/bus/usb/drivers/usblp/ 2>/dev/null | grep -v bind") or "(nothing bound)")

    r.write()
    r.write("-- /dev/usb/lp* --")
    r.write(sh("ls -l /dev/usb/lp* 2>/dev/null") or "(none)")

    r.write()
    r.write("-- serial ports --")
    r.write(sh("ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null") or "(none)")

    r.write()
    r.write("-- printer in lsusb --")
    r.write(sh(f"lsusb -d {VID:04x}:{PID:04x}") or "(printer not in lsusb)")

    r.write()
    r.write("-- udev rule installed? --")
    r.write(sh("cat /etc/udev/rules.d/99-thermal-printer.rules 2>/dev/null") or "(no rule)")

    r.write()
    r.write("-- endpoints --")
    r.write(
        sh(
            f"lsusb -v -d {VID:04x}:{PID:04x} 2>/dev/null | "
            "grep -E 'bInterfaceClass|bEndpointAddress|Transfer Type|bInterfaceNumber'"
        )
        or "(need root for verbose USB descriptors)"
    )

    r.write()
    r.write("-- portable printer tip --")
    r.write("Battery BT/USB minis usually show as /dev/ttyUSB0 (CH340), not 0416:5011.")
    r.write("Power ON the printer before plugging USB; charge-only cables will not enumerate.")

    r.write()
    r.write("-- recent kernel messages --")
    r.write(sh("dmesg 2>/dev/null | tail -20") or "(dmesg not readable without root)")


def _test_lp_node(r):
    r.section("2. TEST: /dev/usb/lp* (kernel usblp driver)")
    nodes = sorted(glob.glob("/dev/usb/lp*"))
    if not nodes:
        r.write("SKIP: no /dev/usb/lp* node.")
        r.write("      usblp is not bound, or udev has not created the device.")
        return False
    for node in nodes:
        try:
            with open(node, "wb") as f:
                f.write(TEST_BYTES)
                f.flush()
            r.write(f"SUCCESS: wrote to {node} — printer should have printed.")
            return True
        except Exception as e:
            r.write(f"FAILED {node}: {type(e).__name__}: {e}")
    return False


def _test_serial(r):
    r.section("3. TEST: serial port (virtual COM / CH340 / CP210x)")
    try:
        import serial
        import serial.tools.list_ports
    except ImportError:
        r.write("SKIP: pyserial not installed.")
        return {"ok": False}

    ports = list(serial.tools.list_ports.comports())
    if not ports:
        r.write("SKIP: no serial ports at all.")
        r.write("      Portable battery printers usually appear as /dev/ttyUSB0 (CH340).")
        r.write("      Power the printer ON, use a data Mini-USB cable, then re-run.")
        return {"ok": False}

    r.write("Serial ports found:")
    for p in ports:
        vid = f"{p.vid:04x}" if p.vid is not None else "----"
        pid = f"{p.pid:04x}" if p.pid is not None else "----"
        r.write(f"  {p.device}  {vid}:{pid}  {p.description}")

    ranked = []
    for p in ports:
        if p.device.startswith("/dev/ttyAMA") or os.path.basename(p.device).startswith("ttyS"):
            r.write(f"  {p.device}  (Pi board UART — skipped, not the printer)")
            continue
        score = 2
        if p.vid is not None and p.pid is not None and (int(p.vid), int(p.pid)) in {
            (0x0416, 0x5011), (0x1A86, 0x7523), (0x1A86, 0x5523), (0x1A86, 0x55D4),
            (0x10C4, 0xEA60), (0x10C4, 0xEA61), (0x0403, 0x6001), (0x0403, 0x6015),
            (0x067B, 0x2303), (0x0483, 0x5740),
        }:
            score = 0
        elif p.device.startswith(("/dev/ttyUSB", "/dev/ttyACM", "/dev/rfcomm")):
            score = 1
        ranked.append((score, p))
    # Also include nodes that exist on disk but pyserial missed
    seen = {p.device for _, p in ranked}
    for pattern in ("/dev/ttyUSB*", "/dev/ttyACM*", "/dev/rfcomm*"):
        for path in sorted(glob.glob(pattern)):
            if path in seen:
                continue
            class _P:
                device = path
            ranked.append((1, _P()))
    ranked.sort(key=lambda x: (x[0], x[1].device))

    if not ranked:
        r.write("SKIP: only board UART ports found (e.g. ttyAMA0).")
        r.write("      Power ON the mini printer, then unplug/replug USB.")
        return {"ok": False}

    for _score, p in ranked:
        for baud in (9600, 115200, 19200, 38400):
            try:
                with serial.Serial(p.device, baud, timeout=2, write_timeout=5) as s:
                    s.write(TEST_BYTES)
                    s.flush()
                r.write(f"SUCCESS: wrote to {p.device} @ {baud}")
                return {"ok": True, "devfile": p.device, "baud": baud}
            except Exception as e:
                r.write(f"FAILED {p.device}@{baud}: {type(e).__name__}: {e}")
    return {"ok": False}


def _test_pyusb(r):
    r.section("4. TEST: direct pyusb bulk write")
    try:
        import usb.core
        import usb.util
    except ImportError:
        r.write("SKIP: pyusb not installed.")
        return False

    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        r.write("FAILED: device not found by pyusb (permissions? unplugged?).")
        return False

    r.write(f"Found device on bus {dev.bus} address {dev.address}")

    try:
        active = dev.is_kernel_driver_active(0)
        r.write(f"kernel driver active on interface 0: {active}")
        if active:
            dev.detach_kernel_driver(0)
            r.write("detached kernel driver")
    except NotImplementedError:
        r.write("kernel driver check not supported on this platform")
    except Exception as e:
        r.write(f"kernel driver check/detach failed: {type(e).__name__}: {e}")

    try:
        dev.set_configuration()
        r.write("set_configuration OK")
    except Exception as e:
        r.write(f"set_configuration: {type(e).__name__}: {e}")

    try:
        cfg = dev.get_active_configuration()
    except Exception as e:
        r.write(f"FAILED get_active_configuration: {e}")
        return False

    out_eps = []
    for intf in cfg:
        for ep in intf:
            if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_OUT:
                if usb.util.endpoint_type(ep.bmAttributes) == usb.util.ENDPOINT_TYPE_BULK:
                    out_eps.append((intf.bInterfaceNumber, ep.bEndpointAddress))

    r.write(f"bulk OUT endpoints found: {[(i, hex(a)) for i, a in out_eps]}")
    if not out_eps:
        r.write("FAILED: no bulk OUT endpoint.")
        return False

    for intf_num, addr in out_eps:
        try:
            r.write(f"writing {len(TEST_BYTES)} bytes to interface {intf_num} endpoint {hex(addr)} (5s timeout)")
            written = dev.write(addr, TEST_BYTES, 5000)
            r.write(f"SUCCESS: wrote {written} bytes — printer should have printed.")
            return True
        except Exception as e:
            r.write(f"FAILED endpoint {hex(addr)}: {type(e).__name__}: {e}")
            if "110" in str(e) or "timed out" in str(e).lower():
                r.write("   Errno 110 = printer accepted no data.")
                r.write("   Usually: printer powered off, cover open, out of paper,")
                r.write("   or another process holds the interface.")
            try:
                dev.clear_halt(addr)
                r.write("   cleared halt, retrying once...")
                written = dev.write(addr, TEST_BYTES, 5000)
                r.write(f"   SUCCESS after clear_halt: wrote {written} bytes")
                return True
            except Exception as e2:
                r.write(f"   retry failed: {type(e2).__name__}: {e2}")
    return False


def run_diagnostics():
    """Run all printer checks. Returns (report_text, results_dict)."""
    r = _Report()
    r.write("IdPass thermal printer diagnostics")
    r.write(f"looking for {VID:04x}:{PID:04x}")
    try:
        if os.geteuid() != 0:
            r.write("NOTE: not running as root. Some details may be hidden.")
    except AttributeError:
        pass

    _system_info(r)
    serial_info = _test_serial(r)
    results = {
        "/dev/usb/lp*": _test_lp_node(r),
        "serial": bool(serial_info.get("ok")),
        "pyusb bulk": _test_pyusb(r),
    }
    if serial_info.get("ok"):
        results["serial_devfile"] = serial_info.get("devfile")
        results["serial_baud"] = serial_info.get("baud")

    r.section("SUMMARY")
    for name, ok in results.items():
        if name.startswith("serial_"):
            r.write(f"  {name:15s} {ok}")
            continue
        r.write(f"  {name:15s} {'WORKS' if ok else 'failed/skipped'}")

    if not any(v for k, v in results.items() if k in ("/dev/usb/lp*", "serial", "pyusb bulk") and v):
        r.write()
        r.write("Nothing could write to the printer. Check in this order:")
        r.write("  1. Printer power switch ON and power adapter connected")
        r.write("     (the USB chip enumerates even with the printer unpowered)")
        r.write("  2. Paper loaded and the cover latched shut")
        r.write("  3. Press the feed button — if no paper moves, it is not printing-ready")
        r.write("  4. Try a different USB cable (some are charge-only)")
    else:
        r.write()
        r.write("Use the method marked WORKS as the printer backend.")
        if results.get("serial_devfile"):
            r.write(
                f"App will use serial {results['serial_devfile']} "
                f"@ {results.get('serial_baud', 9600)}."
            )

    return r.text(), results


def main():
    report, _results = run_diagnostics()
    print(report, end="" if report.endswith("\n") else "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
