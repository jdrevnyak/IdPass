import qrcode
from PIL import Image
from datetime import datetime
import io
import time
import threading

try:
    from escpos.printer import Usb
    import usb.core
    import usb.util
    PRINTER_LIB_AVAILABLE = True
except ImportError:
    PRINTER_LIB_AVAILABLE = False
    print("[WARNING] python-escpos or pyusb not installed. Printing disabled.")

DEFAULT_VENDOR_ID = 0x0416
DEFAULT_PRODUCT_ID = 0x5011


def _usb_device_label(dev):
    vid = int(dev.idVendor)
    pid = int(dev.idProduct)
    bus = getattr(dev, "bus", None)
    addr = getattr(dev, "address", None)
    product = ""
    manufacturer = ""
    try:
        product = (usb.util.get_string(dev, dev.iProduct) or "").strip()
    except Exception:
        pass
    try:
        manufacturer = (usb.util.get_string(dev, dev.iManufacturer) or "").strip()
    except Exception:
        pass
    name = product or manufacturer or "USB device"
    loc = f"{bus}:{addr}" if bus is not None and addr is not None else "?"
    return f"{loc}  {vid:04x}:{pid:04x}  {name}"


def list_usb_devices():
    """Return USB devices the user can pick (skips hubs)."""
    if not PRINTER_LIB_AVAILABLE:
        return []
    devices = []
    try:
        found = usb.core.find(find_all=True) or []
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
                "likely_printer": vid == DEFAULT_VENDOR_ID and pid == DEFAULT_PRODUCT_ID,
            })
        except Exception as e:
            print(f"[PRINTER] Skipping USB device: {e}")
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


class ThermalPrinter:
    def __init__(
        self,
        vendor_id=DEFAULT_VENDOR_ID,
        product_id=DEFAULT_PRODUCT_ID,
        profile="TM-T88II",
        bus=None,
        address=None,
    ):
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.bus = bus
        self.address = address
        self.profile = profile
        self.printer = None
        self.last_pass_params = None
        # libusb timeout 0 = wait forever and can freeze the whole UI
        self.usb_timeout_ms = 5000
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
        """Detach kernel drivers (e.g. usblp) on all interfaces."""
        try:
            try:
                cfg = dev.get_active_configuration()
            except Exception:
                try:
                    dev.set_configuration()
                    cfg = dev.get_active_configuration()
                except Exception:
                    cfg = None
            interfaces = range(1)
            if cfg is not None:
                interfaces = range(cfg.bNumInterfaces)
            for i in interfaces:
                try:
                    if dev.is_kernel_driver_active(i):
                        dev.detach_kernel_driver(i)
                        print(f"[PRINTER] Detached kernel driver from interface {i}")
                except NotImplementedError:
                    return
                except Exception as e:
                    print(f"[PRINTER] Could not detach kernel driver on interface {i}: {e}")
        except Exception as e:
            print(f"[PRINTER] Could not detach kernel driver: {e}")

    def _open_usb(self, in_ep, out_ep):
        usb_args = {}
        if self.bus is not None:
            usb_args["bus"] = int(self.bus)
        if self.address is not None:
            usb_args["address"] = int(self.address)
        kwargs = dict(
            profile=self.profile,
            timeout=self.usb_timeout_ms,
        )
        if in_ep is not None:
            kwargs["in_ep"] = in_ep
        if out_ep is not None:
            kwargs["out_ep"] = out_ep
        if usb_args:
            kwargs["usb_args"] = usb_args
        try:
            return Usb(self.vendor_id, self.product_id, **kwargs)
        except TypeError:
            kwargs.pop("timeout", None)
            kwargs.pop("usb_args", None)
            return Usb(
                self.vendor_id, self.product_id,
                profile=self.profile,
                in_ep=in_ep if in_ep is not None else 0x81,
                out_ep=out_ep if out_ep is not None else 0x03,
            )

    def _connect(self):
        if not PRINTER_LIB_AVAILABLE:
            return

        self._disconnect()

        for attempt in range(2):
            try:
                dev = self._find_device()
                if dev is None and (self.bus is not None or self.address is not None):
                    print("[PRINTER] Selected USB address not found; falling back to VID/PID")
                    self.bus = None
                    self.address = None
                    dev = self._find_device(ignore_location=True)
                if dev is None:
                    print(f"[PRINTER] Device not found (attempt {attempt + 1}/2)")
                    if attempt == 0:
                        time.sleep(1)
                        continue
                    return

                self.bus = getattr(dev, "bus", self.bus)
                self.address = getattr(dev, "address", self.address)

                try:
                    dev.reset()
                    time.sleep(0.4)
                except Exception as e:
                    print(f"[PRINTER] USB reset skipped: {e}")

                self._detach_kernel_driver(dev)
                in_ep, out_ep = _discover_bulk_endpoints(dev)
                print(f"[PRINTER] Endpoints IN={None if in_ep is None else hex(in_ep)} "
                      f"OUT={None if out_ep is None else hex(out_ep)}")

                self.printer = self._open_usb(in_ep, out_ep)
                print(
                    f"[PRINTER] Connected to {self.vendor_id:04x}:{self.product_id:04x} "
                    f"at {self.bus}:{self.address} (attempt {attempt + 1}/2)"
                )
                return
            except usb.core.USBError as e:
                print(f"[PRINTER] USB error (attempt {attempt + 1}/2): {e}")
                self.printer = None
                if attempt == 0:
                    time.sleep(1)
            except Exception as e:
                print(f"[PRINTER] Connection failed (attempt {attempt + 1}/2): {e}")
                self.printer = None
                if attempt == 0:
                    time.sleep(1)

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
        if not PRINTER_LIB_AVAILABLE:
            print("[PRINTER] Test skipped: python-escpos not installed.")
            return False

        if not self.reconnect():
            return False

        ts = datetime.now().strftime("%Y-%m-%d %I:%M %p")
        try:
            self.printer.set(align="center")
            self.printer.text("\n")
            self.printer.text("IdPass printer test\n")
            self.printer.text(f"{ts}\n")
            self.printer.text("--------------------------------\n")
            for _ in range(4):
                self.printer.control("LF")
            try:
                self.printer.cut()
            except Exception:
                pass
            return True
        except Exception as e:
            print(f"[PRINTER] Test print error: {e}")
            self._disconnect()
            return False


if __name__ == "__main__":
    printer = ThermalPrinter()
    printer.print_pass("John Doe", "12345")
