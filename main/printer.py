import qrcode
from PIL import Image
from datetime import datetime
import io
import time
import threading
import glob
import os

EscposUsb = None
EscposSerial = None
EscposFile = None
USBNotFoundError = Exception
usb = None
UsbNoReset = None

try:
    from escpos.printer import Serial as EscposSerial, File as EscposFile
    ESCPOS_AVAILABLE = True
except ImportError:
    ESCPOS_AVAILABLE = False
    print("[WARNING] python-escpos not installed. Printing disabled.")

try:
    from escpos.printer import Usb as EscposUsb
    from escpos.exceptions import USBNotFoundError
    import usb.core as usb_core
    import usb.util as usb_util

    # Keep attribute-style access used elsewhere: usb.core / usb.util
    class _UsbNS:
        core = usb_core
        util = usb_util

    usb = _UsbNS
    USB_AVAILABLE = True
except ImportError:
    USB_AVAILABLE = False
    print("[WARNING] pyusb not installed. USB printer backend disabled (serial still OK).")

PRINTER_LIB_AVAILABLE = ESCPOS_AVAILABLE

DEFAULT_VENDOR_ID = 0x0416
DEFAULT_PRODUCT_ID = 0x5011
DEFAULT_SERIAL_BAUDRATES = (9600, 115200, 19200, 38400)

# Portable 58mm BT/USB minis almost always use a USB-serial bridge, not USB printer class.
_LIKELY_SERIAL_CHIPS = {
    (0x0416, 0x5011),  # Symcode / Winbond USB printer (also sometimes serial)
    (0x1A86, 0x7523),  # CH340
    (0x1A86, 0x5523),  # CH341
    (0x1A86, 0x55D4),  # CH9102
    (0x10C4, 0xEA60),  # Silicon Labs CP210x
    (0x10C4, 0xEA61),
    (0x0403, 0x6001),  # FTDI FT232
    (0x0403, 0x6015),  # FTDI FT231X
    (0x067B, 0x2303),  # Prolific PL2303
    (0x0483, 0x5740),  # STM CDC virtual COM
}

_SERIAL_CHIP_NAMES = {
    (0x1A86, 0x7523): "CH340",
    (0x1A86, 0x5523): "CH341",
    (0x1A86, 0x55D4): "CH9102",
    (0x10C4, 0xEA60): "CP210x",
    (0x10C4, 0xEA61): "CP210x",
    (0x0403, 0x6001): "FTDI",
    (0x0403, 0x6015): "FTDI",
    (0x067B, 0x2303): "PL2303",
    (0x0483, 0x5740): "CDC ACM",
    (0x0416, 0x5011): "thermal printer",
}


def _is_likely_printer_ids(vid, pid):
    try:
        return (int(vid), int(pid)) in _LIKELY_SERIAL_CHIPS
    except Exception:
        return False


def _is_board_uart(path):
    """Raspberry Pi onboard UART — never the USB receipt printer."""
    name = os.path.basename(path or "")
    return name.startswith(("ttyAMA", "ttyS", "serial"))


def _is_usb_serial_path(path):
    name = os.path.basename(path or "")
    return name.startswith(("ttyUSB", "ttyACM", "rfcomm"))


def reload_printer_backends():
    """Re-import escpos/pyusb after pip install in a running process."""
    global EscposUsb, EscposSerial, EscposFile, USBNotFoundError, usb
    global ESCPOS_AVAILABLE, USB_AVAILABLE, PRINTER_LIB_AVAILABLE, UsbNoReset

    try:
        import importlib
        import escpos.printer as escpos_printer
        importlib.reload(escpos_printer)
        EscposSerial = escpos_printer.Serial
        EscposFile = escpos_printer.File
        ESCPOS_AVAILABLE = True
    except Exception as e:
        ESCPOS_AVAILABLE = False
        print(f"[PRINTER] python-escpos still unavailable: {e}")

    try:
        from escpos.printer import Usb as _Usb
        from escpos.exceptions import USBNotFoundError as _USBNotFoundError
        import usb.core as usb_core
        import usb.util as usb_util

        class _UsbNS:
            core = usb_core
            util = usb_util

        EscposUsb = _Usb
        USBNotFoundError = _USBNotFoundError
        usb = _UsbNS
        USB_AVAILABLE = True

        class UsbNoReset(_Usb):
            def open(self, usb_args):
                self.device = usb.core.find(**usb_args)
                if self.device is None:
                    raise USBNotFoundError("Device not found or cable not plugged in.")
                try:
                    if self.device.backend.__module__.endswith("libusb1"):
                        if self.device.is_kernel_driver_active(0):
                            self.device.detach_kernel_driver(0)
                except Exception:
                    pass
                try:
                    self.device.set_configuration()
                except Exception:
                    pass
    except Exception as e:
        USB_AVAILABLE = False
        print(f"[PRINTER] pyusb still unavailable: {e}")

    PRINTER_LIB_AVAILABLE = ESCPOS_AVAILABLE
    return ESCPOS_AVAILABLE


def _project_search_roots():
    """Directories that may contain the IdPass venv."""
    import sys

    roots = []
    env_root = (os.environ.get("VIRTUAL_ENV") or "").strip()
    if env_root:
        roots.append(env_root if os.path.basename(env_root) != "venv" else os.path.dirname(env_root))
        roots.append(env_root)

    here = os.path.dirname(os.path.abspath(__file__))
    roots.append(here)
    roots.append(os.getcwd())

    # Walk parents of this file (main/printer.py -> project root)
    search = here
    for _ in range(8):
        roots.append(search)
        parent = os.path.dirname(search)
        if parent == search:
            break
        search = parent

    # Common classroom Pi layouts
    roots.extend(
        [
            "/home/jdrevnyak/id",
            os.path.expanduser("~/id"),
        ]
    )
    try:
        roots.extend(glob.glob("/home/*/id"))
    except Exception:
        pass

    # Dedupe while preserving order
    out = []
    seen = set()
    for root in roots:
        if not root:
            continue
        root = os.path.normpath(root)
        if root in seen:
            continue
        seen.add(root)
        out.append(root)
    return out


def _venv_python_candidates_in(root):
    """Return possible python binaries under a project/venv root."""
    paths = []
    # root is already the venv directory
    paths.extend(
        [
            os.path.join(root, "bin", "python"),
            os.path.join(root, "bin", "python3"),
            os.path.join(root, "Scripts", "python.exe"),
        ]
    )
    # root is the project directory containing venv/
    paths.extend(
        [
            os.path.join(root, "venv", "bin", "python"),
            os.path.join(root, "venv", "bin", "python3"),
            os.path.join(root, ".venv", "bin", "python"),
            os.path.join(root, "venv", "Scripts", "python.exe"),
        ]
    )
    for pattern in (
        os.path.join(root, "bin", "python3.*"),
        os.path.join(root, "venv", "bin", "python3.*"),
        os.path.join(root, ".venv", "bin", "python3.*"),
    ):
        paths.extend(sorted(glob.glob(pattern)))
    return paths


def _is_usable_python(path):
    if not path:
        return False
    try:
        if os.path.islink(path) or os.path.isfile(path):
            return True
    except Exception:
        return False
    return False


def _find_project_venv_python():
    """Locate the IdPass venv python (never use system python on Bookworm)."""
    import sys

    candidates = []
    searched = []

    exe = getattr(sys, "executable", "") or ""
    if exe:
        candidates.append(exe)

    env_venv = (os.environ.get("VIRTUAL_ENV") or "").strip()
    if env_venv:
        candidates.extend(_venv_python_candidates_in(env_venv))

    for root in _project_search_roots():
        searched.append(root)
        candidates.extend(_venv_python_candidates_in(root))

    seen = set()
    for path in candidates:
        path = os.path.normpath(path)
        if path in seen:
            continue
        seen.add(path)
        # Must look like a venv interpreter — never silent system python
        norm = path.replace("\\", "/")
        if "/venv/" not in norm and "/.venv/" not in norm:
            # Allow current exe only when Python itself reports a venv prefix
            if path == os.path.normpath(exe) and getattr(sys, "base_prefix", sys.prefix) != sys.prefix:
                return path, searched
            continue
        if _is_usable_python(path):
            return path, searched

    return None, searched


def _find_project_root_for_venv():
    """Best guess at the directory where we should create ./venv."""
    for root in _project_search_roots():
        markers = (
            os.path.join(root, "ota-update.py"),
            os.path.join(root, "start_nfc_reader.sh"),
            os.path.join(root, "main", "ota-update.py"),
            os.path.join(root, "main", "printer.py"),
        )
        if any(os.path.isfile(m) for m in markers):
            # If we're inside main/, use parent
            if os.path.basename(root) == "main" and os.path.isfile(os.path.join(root, "printer.py")):
                parent = os.path.dirname(root)
                if parent and parent != root:
                    return parent
            return root
    # Fallbacks
    for fallback in ("/home/jdrevnyak/id", os.path.expanduser("~/id"), os.getcwd()):
        if fallback and os.path.isdir(fallback):
            return fallback
    return os.path.dirname(os.path.abspath(__file__))


def _create_project_venv(project_root):
    """Create a system-site-packages venv so PyQt5 from apt still works."""
    import subprocess
    import sys

    venv_dir = os.path.join(project_root, "venv")
    builder = None
    for cand in (sys.executable, "/usr/bin/python3", "python3"):
        if cand and (cand == "python3" or _is_usable_python(cand)):
            builder = cand
            break
    if not builder:
        return None, "No python3 available to create a venv."

    cmd = [builder, "-m", "venv", "--system-site-packages", venv_dir]
    print(f"[PRINTER] Creating venv: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except Exception as e:
        return None, f"venv creation failed: {e}"
    if result.returncode != 0:
        detail = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
        return None, detail[-800:] or f"venv exited {result.returncode}"

    for path in _venv_python_candidates_in(project_root):
        if _is_usable_python(path) and "/venv/" in path.replace("\\", "/"):
            return path, f"Created venv at {venv_dir}"
    return None, f"venv created at {venv_dir} but python binary not found"


def _add_venv_site_packages(venv_python):
    """Make packages installed into the project venv importable in this process."""
    import sys

    venv_root = os.path.dirname(os.path.dirname(os.path.abspath(venv_python)))
    for site in glob.glob(os.path.join(venv_root, "lib", "python*", "site-packages")):
        if site not in sys.path:
            sys.path.insert(0, site)
            print(f"[PRINTER] Added to sys.path: {site}")
    # Windows venv layout
    win_site = os.path.join(venv_root, "Lib", "site-packages")
    if os.path.isdir(win_site) and win_site not in sys.path:
        sys.path.insert(0, win_site)


def ensure_printer_packages():
    """Install printer deps into the project venv (never system Python)."""
    import subprocess
    import sys

    packages = [
        "python-escpos==3.0a9",
        "pyserial>=3.5",
        "pyusb>=1.2.1",
        "Pillow",
        "qrcode",
    ]

    venv_python, searched = _find_project_venv_python()
    created_note = ""
    if not venv_python:
        project_root = _find_project_root_for_venv()
        venv_python, created_note = _create_project_venv(project_root)
        if not venv_python:
            searched_txt = "\n".join(f"  - {p}" for p in searched[:12])
            return (
                False,
                "No project venv found and could not create one.\n"
                f"Create target: {os.path.join(project_root, 'venv')}\n"
                f"Create error: {created_note}\n"
                f"Searched:\n{searched_txt}\n"
                f"Running python: {sys.executable}",
            )

    cmd = [venv_python, "-m", "pip", "install", "--upgrade", "pip"]
    # Upgrade pip quietly; ignore failure and continue to package install
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except Exception:
        pass

    cmd = [venv_python, "-m", "pip", "install", *packages]
    print(f"[PRINTER] Installing with {venv_python}: {' '.join(packages)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except Exception as e:
        return False, f"pip failed to start ({venv_python}): {e}"

    out = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
    if result.returncode != 0:
        if "externally-managed-environment" in out:
            return (
                False,
                "pip refused install (externally-managed-environment).\n"
                f"Tried venv python: {venv_python}\n"
                "That path is not a real venv. Recreate it with:\n"
                "  python3 -m venv --system-site-packages /home/jdrevnyak/id/venv\n"
                f"{out[-400:]}",
            )
        return False, f"pip via {venv_python} failed:\n{(out[-800:] if out else result.returncode)}"

    _add_venv_site_packages(venv_python)
    ok = reload_printer_backends()
    prefix = (created_note + "\n") if created_note else ""
    if not ok:
        return (
            False,
            prefix
            + f"Packages installed into {venv_python} but python-escpos still cannot be imported. "
            "Quit and reopen the app.",
        )
    return True, prefix + f"Installed python-escpos into {venv_python}"


def _usb_device_label(dev):
    vid = int(dev.idVendor)
    pid = int(dev.idProduct)
    bus = getattr(dev, "bus", None)
    addr = getattr(dev, "address", None)
    loc = f"{bus}:{addr}" if bus is not None and addr is not None else "?"
    chip = _SERIAL_CHIP_NAMES.get((vid, pid))
    extra = f"  {chip}" if chip else ""
    if _is_likely_printer_ids(vid, pid) and not chip:
        extra = "  likely printer"
    return f"{loc}  {vid:04x}:{pid:04x}{extra}"


def _serial_port_label(port):
    vid = getattr(port, "vid", None)
    pid = getattr(port, "pid", None)
    chip = None
    if vid is not None and pid is not None:
        chip = _SERIAL_CHIP_NAMES.get((int(vid), int(pid)))
        ids = f"{int(vid):04x}:{int(pid):04x}"
    else:
        ids = "no-id"
    desc = (getattr(port, "description", None) or "").strip()
    if desc and desc.lower() not in ("n/a", "unknown"):
        name = desc
    elif chip:
        name = chip
    else:
        name = "serial"
    tag = ""
    if _is_board_uart(getattr(port, "device", "") or ""):
        name = "Pi board UART (not printer)"
    elif _is_likely_printer_ids(vid, pid) or _is_usb_serial_path(getattr(port, "device", "") or ""):
        tag = "  ← try this"
    return f"{port.device}  {name}  {ids}{tag}"


def list_usb_devices():
    """USB devices plus serial/lp nodes portable thermal printers use on a Pi."""
    devices = _list_raw_usb_devices()
    extras = []
    seen_serial = set()
    try:
        import serial.tools.list_ports
        for p in serial.tools.list_ports.comports():
            path = getattr(p, "device", None) or ""
            if not path or path.endswith("debugconsole"):
                continue
            if _is_board_uart(path):
                continue  # ttyAMA0 is the Pi's own UART, not the receipt printer
            if path in seen_serial:
                continue
            seen_serial.add(path)
            vid = int(p.vid) if p.vid is not None else None
            pid = int(p.pid) if p.pid is not None else None
            extras.append({
                "kind": "serial",
                "devfile": path,
                "vendor_id": vid if vid is not None else 0,
                "product_id": pid if pid is not None else 0,
                "bus": None,
                "address": None,
                "label": _serial_port_label(p),
                "likely_printer": _is_likely_printer_ids(vid, pid) or _is_usb_serial_path(path),
            })
    except Exception as e:
        print(f"[PRINTER] Serial scan failed: {e}")

    # pyserial sometimes misses nodes that exist on disk — pick them up directly
    for pattern in ("/dev/ttyUSB*", "/dev/ttyACM*", "/dev/rfcomm*"):
        for path in sorted(glob.glob(pattern)):
            if path in seen_serial:
                continue
            seen_serial.add(path)
            extras.append({
                "kind": "serial",
                "devfile": path,
                "vendor_id": 0,
                "product_id": 0,
                "bus": None,
                "address": None,
                "label": f"{path}  USB serial  ← try this",
                "likely_printer": True,
            })

    for rf in sorted(glob.glob("/dev/rfcomm*")):
        if rf in seen_serial:
            continue
        extras.append({
            "kind": "serial",
            "devfile": rf,
            "vendor_id": 0,
            "product_id": 0,
            "bus": None,
            "address": None,
            "label": f"{rf}  Bluetooth serial  ← try this",
            "likely_printer": True,
        })

    for lp in sorted(glob.glob("/dev/usb/lp*")):
        extras.append({
            "kind": "file",
            "devfile": lp,
            "vendor_id": DEFAULT_VENDOR_ID,
            "product_id": DEFAULT_PRODUCT_ID,
            "bus": None,
            "address": None,
            "label": f"{lp}  USB printer port  ← try this",
            "likely_printer": True,
        })
    for d in devices:
        d.setdefault("kind", "usb")
        d.setdefault("devfile", None)
    combined = extras + devices
    combined.sort(key=lambda d: (not d.get("likely_printer"), d.get("label") or ""))
    return combined


def _list_raw_usb_devices():
    if not USB_AVAILABLE:
        return []
    devices = []
    try:
        found = list(usb.core.find(find_all=True) or [])
    except Exception as e:
        print(f"[PRINTER] USB scan failed: {e}")
        return []

    for dev in found:
        try:
            if int(getattr(dev, "bDeviceClass", 0) or 0) == 9:
                continue  # hub
            vid = int(dev.idVendor)
            pid = int(dev.idProduct)
            bus = getattr(dev, "bus", None)
            addr = getattr(dev, "address", None)
            devices.append({
                "vendor_id": vid,
                "product_id": pid,
                "bus": bus,
                "address": addr,
                "label": _usb_device_label(dev),
                "likely_printer": _is_likely_printer_ids(vid, pid),
            })
        except Exception as e:
            print(f"[PRINTER] Skipping USB device: {e}")
        finally:
            try:
                usb.util.dispose_resources(dev)
            except Exception:
                pass
    devices.sort(key=lambda d: (not d["likely_printer"], d["label"]))
    return devices


def _discover_bulk_endpoints(dev):
    """Read bulk IN/OUT endpoint addresses from descriptors (no claim required)."""
    in_ep = None
    out_ep = None
    try:
        for cfg in dev:
            for intf in cfg:
                for ep in intf:
                    try:
                        if usb.util.endpoint_type(ep.bmAttributes) != usb.util.ENDPOINT_TYPE_BULK:
                            continue
                    except Exception:
                        continue
                    addr = ep.bEndpointAddress
                    if usb.util.endpoint_direction(addr) == usb.util.ENDPOINT_OUT:
                        out_ep = addr
                    else:
                        in_ep = addr
    except Exception as e:
        print(f"[PRINTER] Endpoint discovery failed: {e}")
    return in_ep, out_ep


if USB_AVAILABLE and EscposUsb is not None:
    class UsbNoReset(EscposUsb):
        """python-escpos 3.0a9 calls device.reset() in open(), which invalidates
        the handle so the next write times out (Errno 110). Skip the reset."""

        def open(self, usb_args):
            self.device = usb.core.find(**usb_args)
            if self.device is None:
                raise USBNotFoundError("Device not found or cable not plugged in.")
            try:
                if self.device.backend.__module__.endswith("libusb1"):
                    if self.device.is_kernel_driver_active(0):
                        self.device.detach_kernel_driver(0)
                        print("[PRINTER] Detached kernel driver from interface 0")
            except Exception as e:
                print(f"[PRINTER] Kernel detach: {e}")
            try:
                self.device.set_configuration()
            except usb.core.USBError as e:
                print(f"[PRINTER] set_configuration: {e}")


class ThermalPrinter:
    def __init__(
        self,
        vendor_id=DEFAULT_VENDOR_ID,
        product_id=DEFAULT_PRODUCT_ID,
        profile="TM-T88II",
        bus=None,
        address=None,
        backend_kind="auto",
        devfile=None,
        baudrate=None,
    ):
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.bus = bus
        self.address = address
        self.profile = profile
        self.printer = None
        self.backend_kind = backend_kind or "auto"
        self.devfile = devfile or None
        self.baudrate = int(baudrate) if baudrate else None
        self.last_pass_params = None
        self.last_error = ""
        self.usb_timeout_ms = 8000
        self._connect()

    def configure(self, vendor_id, product_id, bus=None, address=None):
        """Point at a specific USB device and open a new handle."""
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.bus = bus
        self.address = address
        return self.reconnect()

    def _disconnect(self):
        """Release USB resources so the device can be opened again after errors or unplug."""
        printer = self.printer
        self.printer = None
        if printer is None:
            return

        def _close():
            try:
                close = getattr(printer, "close", None)
                if callable(close):
                    close()
            except Exception as e:
                print(f"[PRINTER] Error while closing printer handle: {e}")

        closer = threading.Thread(target=_close, daemon=True)
        closer.start()
        closer.join(timeout=2)
        if closer.is_alive():
            print("[PRINTER] USB close timed out; continuing without waiting")

    def _find_device(self, ignore_location=False):
        kwargs = {}
        if not ignore_location:
            if self.bus is not None:
                kwargs["bus"] = int(self.bus)
            if self.address is not None:
                kwargs["address"] = int(self.address)
        return usb.core.find(idVendor=self.vendor_id, idProduct=self.product_id, **kwargs)

    def _detach_kernel_driver(self, dev):
        """Detach usblp/kernel driver without claiming the device for ourselves."""
        try:
            if dev.is_kernel_driver_active(0):
                dev.detach_kernel_driver(0)
                print("[PRINTER] Detached kernel driver from interface 0")
        except NotImplementedError:
            pass
        except Exception as e:
            print(f"[PRINTER] Could not detach kernel driver: {e}")

    def _open_usb(self, in_ep, out_ep):
        """Open USB without python-escpos's device.reset() (that causes Errno 110)."""
        kwargs = dict(
            in_ep=in_ep or 0x81,
            out_ep=out_ep or 0x03,
            timeout=self.usb_timeout_ms,
        )
        print(f"[PRINTER] Opening UsbNoReset({self.vendor_id:#06x}, {self.product_id:#06x}, {kwargs})")
        try:
            return UsbNoReset(self.vendor_id, self.product_id, **kwargs)
        except TypeError:
            return UsbNoReset(
                self.vendor_id, self.product_id,
                in_ep=kwargs["in_ep"],
                out_ep=kwargs["out_ep"],
            )

    def _try_serial(self, devfile, baudrate=9600):
        print(f"[PRINTER] Trying serial {devfile} @ {baudrate}")
        return EscposSerial(
            devfile=devfile,
            baudrate=baudrate,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=1,
            dsrdtr=False,
        )

    def _try_file(self, devfile):
        print(f"[PRINTER] Trying file {devfile}")
        return EscposFile(devfile=devfile, auto_flush=True)

    def _candidate_serial_ports(self):
        """Serial ports to try: selected device first, then likely printer chips."""
        ports = []
        if self.backend_kind == "serial" and self.devfile:
            ports.append(self.devfile)
        try:
            import serial.tools.list_ports
            for p in serial.tools.list_ports.comports():
                path = getattr(p, "device", None)
                if not path or path in ports or _is_board_uart(path):
                    continue
                vid = int(p.vid) if p.vid is not None else None
                pid = int(p.pid) if p.pid is not None else None
                if self.vendor_id and self.product_id and vid is not None and pid is not None:
                    if int(vid) == int(self.vendor_id) and int(pid) == int(self.product_id):
                        ports.append(path)
                        continue
                if _is_likely_printer_ids(vid, pid) or _is_usb_serial_path(path):
                    ports.append(path)
        except Exception as e:
            print(f"[PRINTER] Serial port scan: {e}")
        for pattern in ("/dev/ttyUSB*", "/dev/ttyACM*", "/dev/rfcomm*"):
            for path in sorted(glob.glob(pattern)):
                if path not in ports:
                    ports.append(path)
        return ports

    def _matching_serial_ports(self):
        return self._candidate_serial_ports()

    def _connect(self):
        if not ESCPOS_AVAILABLE:
            self.last_error = "python-escpos is not installed"
            return

        self._disconnect()
        self.last_error = ""
        errors = []
        bauds = DEFAULT_SERIAL_BAUDRATES
        preferred_baud = getattr(self, "baudrate", None)
        if preferred_baud:
            bauds = (int(preferred_baud),) + tuple(b for b in bauds if int(b) != int(preferred_baud))

        if self.backend_kind == "serial" and self.devfile:
            for baud in bauds:
                try:
                    self.printer = self._try_serial(self.devfile, baud)
                    self.baudrate = baud
                    print(f"[PRINTER] Connected via serial {self.devfile} @ {baud}")
                    return
                except Exception as e:
                    errors.append(f"serial {self.devfile}@{baud}: {e}")

        if self.backend_kind == "file" and self.devfile:
            try:
                self.printer = self._try_file(self.devfile)
                print(f"[PRINTER] Connected via {self.devfile}")
                return
            except Exception as e:
                errors.append(f"file {self.devfile}: {e}")

        for port in self._candidate_serial_ports():
            if self.backend_kind == "serial" and self.devfile and port == self.devfile:
                continue  # already tried above
            for baud in bauds:
                try:
                    self.printer = self._try_serial(port, baud)
                    self.backend_kind = "serial"
                    self.devfile = port
                    self.baudrate = baud
                    print(f"[PRINTER] Connected via serial {port} @ {baud}")
                    return
                except Exception as e:
                    errors.append(f"serial {port}@{baud}: {e}")

        for lp in sorted(glob.glob("/dev/usb/lp*")):
            try:
                self.printer = self._try_file(lp)
                self.backend_kind = "file"
                self.devfile = lp
                print(f"[PRINTER] Connected via {lp}")
                return
            except Exception as e:
                errors.append(f"{lp}: {e}")

        if not USB_AVAILABLE or UsbNoReset is None:
            errors.append("pyusb not installed (USB backend unavailable; use serial/ttyACM)")
            self.last_error = " | ".join(errors) if errors else "Could not open the printer"
            return

        for attempt in range(2):
            try:
                dev = self._find_device(ignore_location=True)
                if dev is None:
                    msg = (
                        f"USB printer {self.vendor_id:04x}:{self.product_id:04x} not found "
                        f"(attempt {attempt + 1}/2)"
                    )
                    print(f"[PRINTER] {msg}")
                    errors.append(msg)
                    if attempt == 0:
                        time.sleep(1)
                        continue
                    break

                self.bus = getattr(dev, "bus", self.bus)
                self.address = getattr(dev, "address", self.address)
                self._detach_kernel_driver(dev)
                in_ep, out_ep = _discover_bulk_endpoints(dev)
                if in_ep is None:
                    in_ep = 0x81
                if out_ep is None:
                    out_ep = 0x03
                print(f"[PRINTER] Endpoints IN={hex(in_ep)} OUT={hex(out_ep)}")
                try:
                    usb.util.dispose_resources(dev)
                except Exception:
                    pass

                self.printer = self._open_usb(in_ep, out_ep)
                self.backend_kind = "usb"
                print(
                    f"[PRINTER] Connected to {self.vendor_id:04x}:{self.product_id:04x} "
                    f"at {self.bus}:{self.address} (attempt {attempt + 1}/2)"
                )
                self.last_error = ""
                return
            except Exception as e:
                # USBError is a subclass when pyusb is present
                msg = f"USB/connection error: {e}"
                print(f"[PRINTER] {msg} (attempt {attempt + 1}/2)")
                errors.append(msg)
                self.printer = None
                if attempt == 0:
                    time.sleep(1)

        self.last_error = " | ".join(errors) if errors else "Could not open the printer"

    def reconnect(self):
        """Drop any existing USB session and open a fresh connection."""
        self._connect()
        return self.is_connected()

    def is_connected(self):
        return self.printer is not None

    def print_pass(
        self,
        student_name,
        student_id,
        pass_type="HALL PASS",
        location=None,
        timestamp=None,
        _allow_retry=True,
    ):
        """
        Print a hall pass with QR code.
        """
        if not timestamp:
            timestamp = datetime.now().strftime("%Y-%m-%d %I:%M %p")

        print(f"[PRINTER] Printing {pass_type} for {student_name} ({student_id})")

        if not self.is_connected():
            self._connect()
            if not self.is_connected():
                print("[PRINTER] Printer not available, skipping print.")
                return False

        try:
            self.printer.set(align='center')
            self.printer.text("\n")
            self.printer.set(align='center', bold=True, double_width=True, double_height=True)
            self.printer.text(f"{pass_type.upper()}\n")
            self.printer.set(align='center', bold=False, double_width=False, double_height=False)
            self.printer.text("--------------------------------\n")
            self.printer.text(f"Student: {student_name}\n")
            self.printer.text(f"ID: {student_id}\n")
            if location:
                self.printer.text(f"Loc: {location}\n")
            self.printer.text(f"Time: {timestamp}\n")
            self.printer.text("--------------------------------\n")

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=8,
                border=2,
            )
            qr.add_data(str(student_id))
            qr.make(fit=True)

            img_wrapper = qr.make_image(fill_color="black", back_color="white")
            img_buffer = io.BytesIO()
            img_wrapper.save(img_buffer, format="PNG")
            img_buffer.seek(0)
            pil_img = Image.open(img_buffer)

            self.printer.image(pil_img)
            self.printer.text("Scan to Return\n")
            for _ in range(5):
                self.printer.control('LF')
            try:
                self.printer.cut()
            except Exception:
                pass

            self.last_pass_params = {
                "student_name": student_name,
                "student_id": student_id,
                "pass_type": pass_type,
                "location": location,
                "timestamp": timestamp,
            }
            return True

        except Exception as e:
            print(f"[PRINTER] Print error: {e}")
            self._disconnect()
            if _allow_retry:
                self._connect()
                if self.is_connected():
                    return self.print_pass(
                        student_name,
                        student_id,
                        pass_type=pass_type,
                        location=location,
                        timestamp=timestamp,
                        _allow_retry=False,
                    )
            return False

    def reprint_last_pass(self):
        """Reprint the most recently printed hall pass using cached parameters."""
        if self.last_pass_params is None:
            return False, "No hall pass has been printed yet this session."
        return self.print_pass(**self.last_pass_params), None

    def test_print(self):
        """Reconnect (handles unplug/replug) and print a short test page."""
        global ESCPOS_AVAILABLE
        if not ESCPOS_AVAILABLE:
            ok, msg = ensure_printer_packages()
            if not ok:
                self.last_error = f"python-escpos is not installed ({msg})"
                print(f"[PRINTER] Test skipped: {self.last_error}")
                return False

        if not self.reconnect():
            if not self.last_error:
                self.last_error = "Could not open the printer (is ttyACM0/ttyUSB0 present? Power printer ON.)"
            return False

        ts = datetime.now().strftime("%Y-%m-%d %I:%M %p")
        try:
            # Avoid printer.set() — some profiles choke on it. Send plain ESC/POS text.
            self.printer._raw(b"\nIdPass printer test\n")
            self.printer._raw(ts.encode("ascii", "replace") + b"\n")
            self.printer._raw(b"--------------------------------\n\n\n\n")
            try:
                self.printer.cut()
            except Exception:
                self.printer._raw(b"\n\n\n")
            self.last_error = ""
            return True
        except Exception as e:
            self.last_error = str(e)
            print(f"[PRINTER] Test print error: {e}")
            self._disconnect()
            return False


if __name__ == "__main__":
    printer = ThermalPrinter()
    printer.print_pass("John Doe", "12345")
