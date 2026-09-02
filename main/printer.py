import qrcode
from PIL import Image
from datetime import datetime
import io
import time

try:
    from escpos.printer import Usb
    import usb.core
    PRINTER_LIB_AVAILABLE = True
except ImportError:
    PRINTER_LIB_AVAILABLE = False
    print("[WARNING] python-escpos or pyusb not installed. Printing disabled.")

class ThermalPrinter:
    def __init__(self, vendor_id=0x0416, product_id=0x5011, profile="TM-T88II"):
        """
        Initialize the thermal printer.
        """
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.profile = profile
        self.printer = None
        self.last_pass_params = None
        self._connect()

    def _disconnect(self):
        """Release USB resources so the device can be opened again after errors or unplug."""
        if self.printer is None:
            return
        try:
            close = getattr(self.printer, "close", None)
            if callable(close):
                close()
        except Exception as e:
            print(f"[PRINTER] Error while closing printer handle: {e}")
        self.printer = None

    def _detach_kernel_driver(self):
        """Find the raw USB device and detach the kernel driver (e.g. usblp) if active."""
        try:
            dev = usb.core.find(idVendor=self.vendor_id, idProduct=self.product_id)
            if dev is None:
                return False
            if dev.is_kernel_driver_active(0):
                dev.detach_kernel_driver(0)
                print("[PRINTER] Detached kernel driver from interface 0")
            return True
        except NotImplementedError:
            # detach_kernel_driver is Linux-only; safe to ignore on other platforms
            return True
        except Exception as e:
            print(f"[PRINTER] Could not detach kernel driver: {e}")
            return True

    def _connect(self):
        if not PRINTER_LIB_AVAILABLE:
            return

        self._disconnect()

        for attempt in range(2):
            try:
                dev = usb.core.find(idVendor=self.vendor_id, idProduct=self.product_id)
                if dev is None:
                    print(f"[PRINTER] Device not found (attempt {attempt + 1}/2)")
                    if attempt == 0:
                        time.sleep(1)
                        continue
                    return

                self._detach_kernel_driver()

                self.printer = Usb(
                    self.vendor_id, self.product_id,
                    profile=self.profile, in_ep=0x81, out_ep=0x03,
                )
                print(f"[PRINTER] Connected to {hex(self.vendor_id)}:{hex(self.product_id)} (attempt {attempt + 1}/2)")
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
            # Align center
            self.printer.set(align='center')
            
            # Header
            self.printer.text("\n")
            self.printer.set(align='center', bold=True, double_width=True, double_height=True)
            self.printer.text(f"{pass_type.upper()}\n")
            self.printer.set(align='center', bold=False, double_width=False, double_height=False)
            self.printer.text("--------------------------------\n")
            
            # Student Info
            self.printer.text(f"Student: {student_name}\n")
            self.printer.text(f"ID: {student_id}\n")
            if location:
                self.printer.text(f"Loc: {location}\n")
            self.printer.text(f"Time: {timestamp}\n")
            self.printer.text("--------------------------------\n")

            # Generate QR Code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=8,
                border=2,
            )
            qr.add_data(str(student_id))
            qr.make(fit=True)
            
            # Create PIL image via BytesIO to ensure compatibility
            img_wrapper = qr.make_image(fill_color="black", back_color="white")
            img_buffer = io.BytesIO()
            img_wrapper.save(img_buffer, format="PNG")
            img_buffer.seek(0)
            pil_img = Image.open(img_buffer)
            
            # Print QR Code
            self.printer.image(pil_img)
            
            self.printer.text("Scan to Return\n")
            
            # Feed lines using LF control
            for _ in range(5):
                self.printer.control('LF')
            
            # Cut
            try:
                self.printer.cut()
            except Exception:
                # Some cheap printers don't support cut, just ignore
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
        """
        Reconnect and print a short test page (for diagnostics from Settings).
        """
        if not PRINTER_LIB_AVAILABLE:
            print("[PRINTER] Test skipped: python-escpos not installed.")
            return False

        self.reconnect()
        if not self.is_connected():
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
    # Test code
    printer = ThermalPrinter()
    printer.print_pass("John Doe", "12345")

