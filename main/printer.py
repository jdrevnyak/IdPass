import qrcode
from PIL import Image
from datetime import datetime
import io

try:
    from escpos.printer import Usb
    PRINTER_LIB_AVAILABLE = True
except ImportError:
    PRINTER_LIB_AVAILABLE = False
    print("[WARNING] python-escpos not installed. Printing disabled.")

class ThermalPrinter:
    def __init__(self, vendor_id=0x0416, product_id=0x5011, profile="TM-T88II"):
        """
        Initialize the thermal printer.
        """
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.profile = profile
        self.printer = None
        self._connect()

    def _connect(self):
        if not PRINTER_LIB_AVAILABLE:
            return
        
        try:
            # Attempt to find the printer
            # Explicitly set endpoints for POS58/0416:5011 printer
            # IN: 0x81 (129), OUT: 0x03 (3)
            self.printer = Usb(self.vendor_id, self.product_id, profile=self.profile, in_ep=0x81, out_ep=0x03)
            print(f"[PRINTER] Connected to printer {hex(self.vendor_id)}:{hex(self.product_id)}")
        except Exception as e:
            # Only print error if we really tried and failed, to avoid spamming logs if just not present
            print(f"[PRINTER] Connection failed: {e}") 
            self.printer = None

    def is_connected(self):
        return self.printer is not None

    def print_pass(self, student_name, student_id, pass_type="HALL PASS", location=None, timestamp=None):
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
            
            return True

        except Exception as e:
            print(f"[PRINTER] Print error: {e}")
            self.printer = None
            return False

if __name__ == "__main__":
    # Test code
    printer = ThermalPrinter()
    printer.print_pass("John Doe", "12345")

