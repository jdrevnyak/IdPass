"""
Main NFC Reader GUI Application

This module contains the main application window and orchestrates the different
components imported from other modules.
"""

import sys
import serial
import serial.tools.list_ports
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QMessageBox, QPushButton)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont

# GPIO imports for Raspberry Pi LED control
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
    print("[INFO] GPIO library available - LED control enabled")
except ImportError:
    GPIO_AVAILABLE = False
    print("[WARNING] GPIO library not available - LED control disabled")

# Import our custom modules
from hybrid_db import HybridDatabase
from widgets import AnalogClock, StatusIndicator
from dialogs import AddStudentDialog, ImportDialog
from overlays import (KeypadOverlay, SettingsOverlay, BathroomOverlay, 
                     NurseOverlay, AddStudentOverlay, StudentSelectionOverlay)
from updater import UpdateManager


class NFCReaderGUI(QMainWindow):
    """Main application window for the NFC Reader student attendance system."""
    
    # GPIO pin definitions for LEDs
    RED_LED_PIN = 18      # GPIO 18 - Students are out
    GREEN_LED_PIN = 16    # GPIO 16 - No students out
    # School day schedule (local time)
    # Each tuple: (label, (start_hour, start_minute), (end_hour, end_minute))
    SCHEDULE = [
        ("Period 1", (7, 25), (8, 8)),
        ("Period 2", (8, 12), (9, 1)),
        ("Period 3", (9, 5), (9, 48)),
        ("Period 4", (9, 52), (10, 35)),
        ("Period 5", (10, 39), (11, 22)),
        ("Period 6", (11, 26), (12, 9)),
        ("Period 7", (12, 13), (12, 56)),
        ("Period 8", (13, 0), (13, 43)),
        ("Period 9", (13, 47), (14, 30)),
    ]
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Student Attendance System")
        
        # Set up full screen mode
        self.showFullScreen()
        
        # Initialize GPIO for LED control
        self.setup_gpio()
        
        # Initialize Hybrid database (local SQLite + Google Sheets sync)
        self.db = HybridDatabase(sync_interval_minutes=10)
        
        # Serial connection variables
        self.serial_port = None
        self.serial_connection = None
        self.connection_error_count = 0
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Header with date and time
        self.header = QLabel()
        self.header.setAlignment(Qt.AlignCenter)
        self.header.setFont(QFont('Arial', 32, QFont.Bold))
        self.header.setStyleSheet("color: #fff; background-color: #23405a; padding: 24px 0 24px 0; border-top-left-radius: 24px; border-top-right-radius: 24px;")
        main_layout.addWidget(self.header)
        
        # Center layout for clock and buttons
        center_layout = QHBoxLayout()
        center_layout.setContentsMargins(40, 40, 40, 40)
        center_layout.setSpacing(60)
        
        # Left: Analog clock
        clock_layout = QVBoxLayout()
        clock_layout.setAlignment(Qt.AlignCenter)
        self.analog_clock = AnalogClock()
        clock_layout.addWidget(self.analog_clock)
        center_layout.addLayout(clock_layout)
        
        # Right: Buttons
        button_layout = QVBoxLayout()
        button_layout.setAlignment(Qt.AlignVCenter)
        button_layout.setSpacing(32)
        self.break_start_button = QPushButton("Bathroom")
        self.nurse_button = QPushButton("Nurse")
        for btn in [self.break_start_button, self.nurse_button]:
            btn.setMinimumSize(340, 80)
            btn.setFont(QFont('Arial', 32, QFont.Bold))
            btn.setCursor(Qt.PointingHandCursor)
        self.break_start_button.setStyleSheet('''
            QPushButton {
                background-color: #2bb3a3;
                color: white;
                border-radius: 24px;
                border: none;
            }
            QPushButton:hover {
                background-color: #249e90;
            }
            QPushButton:pressed {
                background-color: #1e857a;
            }
        ''')
        self.nurse_button.setStyleSheet('''
            QPushButton {
                background-color: #23405a;
                color: white;
                border-radius: 24px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1a2e3d;
            }
            QPushButton:pressed {
                background-color: #162534;
            }
        ''')
        button_layout.addWidget(self.break_start_button)
        button_layout.addWidget(self.nurse_button)
        center_layout.addLayout(button_layout)
        
        main_layout.addLayout(center_layout)
        
        # Prompt at the bottom
        self.prompt = QLabel("Tap your ID or enter ID number")
        self.prompt.setAlignment(Qt.AlignCenter)
        self.prompt.setFont(QFont('Arial', 24))
        self.prompt.setStyleSheet("color: #23405a; background: #f5f7fa; padding: 24px 0 24px 0; border-bottom-left-radius: 24px; border-bottom-right-radius: 24px;")
        main_layout.addWidget(self.prompt)
        
        # Timer for updating header date and time
        self.time_timer = QTimer()
        self.time_timer.timeout.connect(self.update_header_datetime)
        self.time_timer.timeout.connect(self.update_period_label)
        self.time_timer.start(1000)
        self.update_header_datetime()
        self.update_period_label()
        
        # Timer for updating GPIO LED status
        self.led_timer = QTimer()
        self.led_timer.timeout.connect(self.update_gpio_led_status)
        self.led_timer.start(10000)  # Update every 10 seconds
        self.update_gpio_led_status()  # Initial update
        
        # Serial reading timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.read_serial)
        
        # Message timer for clearing prompt messages
        self.message_timer = QTimer()
        self.message_timer.setSingleShot(True)
        self.message_timer.timeout.connect(self.clear_prompt_message)
        
        # Current student ID
        self.current_student_id = None
        
        # Auto-checkout on startup
        self.db.auto_checkout_students()
        # Periodic auto-checkout every minute
        self.auto_checkout_timer = QTimer(self)
        self.auto_checkout_timer.timeout.connect(self.db.auto_checkout_students)
        self.auto_checkout_timer.start(60 * 1000)  # every 60 seconds
        
        # Initialize overlays
        self.keypad_overlay = KeypadOverlay(self)
        self.analog_clock.mousePressEvent = self.show_keypad_overlay
        self.settings_overlay = SettingsOverlay(self)
        self.header.installEventFilter(self)
        self._header_press_time = None
        self._header_timer = QTimer(self)
        self._header_timer.setSingleShot(True)
        self._header_timer.timeout.connect(self._show_settings_overlay)
        self.bathroom_mode = False
        self.break_start_button.clicked.connect(self.show_bathroom_overlay)
        self.bathroom_overlay = BathroomOverlay(self)
        
        # Connect nurse button to nurse overlay
        self.nurse_button.clicked.connect(self.show_nurse_overlay)
        self.nurse_overlay = NurseOverlay(self)
        
        # Try to auto-connect to ESP32
        self.auto_connect_esp32()
        
        # Add student overlay
        self.add_student_overlay = AddStudentOverlay(self)
        
        # Student selection overlay for linking NFC cards
        self.student_selection_overlay = StudentSelectionOverlay(self)
        
        # Connect the card linking success signal
        self.student_selection_overlay.card_linked.connect(self.handle_card_linked)
        
        # Initialize update manager
        self.update_manager = UpdateManager(
            parent_window=self,
            current_version="1.0.1",  # Update this version number for each release
            repo_owner="jdrevnyak",  # Your GitHub username
            repo_name="IdPass"  # Your repository name
        )
    
    def closeEvent(self, event):
        """Handle application close event"""
        self.cleanup_gpio()
        # Clean up database resources and force final sync
        if hasattr(self, 'db') and self.db:
            print("[INFO] Performing final sync before closing...")
            self.db.force_sync()
            self.db.cleanup()
        super().closeEvent(event)
    
    def auto_connect_esp32(self):
        """Automatically try to connect to ESP32 on UART ports"""
        print("[INFO] Starting ESP32 auto-connect...")
        try:
            # UART ports for Raspberry Pi (ESP32 connected via UART)
            # Prefer serial alias first for portability across models
            uart_ports = ['/dev/serial0', '/dev/ttyAMA10', '/dev/ttyS0', '/dev/ttyAMA0']
            # Fallback to USB ports if UART doesn't work
            usb_ports = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', '/dev/ttyACM1']
            
            # Try UART ports first
            all_ports = uart_ports + usb_ports
            print(f"[INFO] Will try ports: {all_ports}")
            
            for port in all_ports:
                try:
                    # Check if port exists
                    import os
                    if not os.path.exists(port):
                        print(f"[INFO] Port {port} does not exist, skipping")
                        continue
                    
                    print(f"[INFO] Attempting to connect to {port}...")
                    self.serial_connection = serial.Serial(port, 115200, timeout=0.1)
                    print(f"[SUCCESS] Auto-connected to ESP32 on {port}")
                    self.timer.start(100)  # Start reading every 100ms
                    return
                except Exception as e:
                    print(f"[ERROR] Failed to connect to {port}: {e}")
                    continue
            
            print("[WARNING] No ESP32 found on UART or USB ports")
        except Exception as e:
            print(f"[ERROR] Auto-connect error: {e}")

    def keyPressEvent(self, event):
        """Handle key press events for full screen toggle"""
        if event.key() == Qt.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        elif event.key() == Qt.Key_Escape:
            # Allow escape to exit full screen but not close the app
            if self.isFullScreen():
                self.showNormal()
        else:
            super().keyPressEvent(event)

    def parse_uid(self, data):
        """Extract UID from the serial data"""
        print(f"[DEBUG] Parsing UID from data: '{data}'")
        if "UID Value:" in data:
            uid_part = data.split("UID Value:")[1].strip()
            uid = uid_part.replace("0x", "").replace(" ", "")
            print(f"[DEBUG] Extracted UID: '{uid}'")
            return uid
        print(f"[DEBUG] No UID found in data")
        return None
    
    def show_add_student_dialog(self):
        """Show the add student overlay"""
        self.add_student_overlay.show_overlay()

    def show_import_dialog(self):
        """Show dialog to import students from file"""
        dialog = ImportDialog(self)
        if dialog.exec_():
            file_path = dialog.file_path.text()
            if not file_path:
                return
                
            try:
                if file_path.endswith('.csv'):
                    results = self.db.import_from_csv(file_path)
                elif file_path.endswith('.json'):
                    results = self.db.import_from_json(file_path)
                else:
                    QMessageBox.warning(self, "Error", "Unsupported file format")
                    return
                
                # Show results
                message = f"Import completed:\n"
                message += f"Successfully imported: {results['success']}\n"
                message += f"Failed to import: {results['failed']}\n"
                
                if results['errors']:
                    message += "\nErrors:\n"
                    for error in results['errors'][:5]:  # Show first 5 errors
                        message += f"- {error}\n"
                    if len(results['errors']) > 5:
                        message += f"... and {len(results['errors']) - 5} more errors"
                
                QMessageBox.information(self, "Import Results", message)
                
            except Exception as e:
                QMessageBox.critical(self, "Import Error", str(e))

    def update_header_datetime(self):
        """Update the header with current date and time"""
        now = datetime.now()
        date_str = now.strftime('%a, %b %d, %Y')  # Abbreviated day and month
        time_str = now.strftime('%I:%M %p').lstrip('0')
        self.header.setText(f"{date_str}  {time_str}")
    
    def setup_gpio(self):
        """Initialize GPIO pins for LED control"""
        if not GPIO_AVAILABLE:
            return
            
        try:
            # Set GPIO mode
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # Setup LED pins as outputs
            GPIO.setup(self.RED_LED_PIN, GPIO.OUT)
            GPIO.setup(self.GREEN_LED_PIN, GPIO.OUT)
            
            # Turn off all LEDs initially
            GPIO.output(self.RED_LED_PIN, GPIO.LOW)
            GPIO.output(self.GREEN_LED_PIN, GPIO.LOW)
            
            print(f"[INFO] GPIO initialized - LEDs on pins {self.RED_LED_PIN} (Red), {self.GREEN_LED_PIN} (Green)")
            
        except Exception as e:
            print(f"[ERROR] Failed to initialize GPIO: {e}")
    
    def update_gpio_led_status(self):
        """Update GPIO LED status based on whether students are out, restricted windows, or passing time"""
        if not GPIO_AVAILABLE:
            return
         
        try:
            now = datetime.now()
            restricted_period = self._is_bathroom_restricted(now)
            is_passing = (self._determine_current_period(now) == "Passing")
            is_after = (self._determine_current_period(now) == "After School")

            # Also reflect if any students are currently out
            has_students_out = False
            try:
                has_students_out = self.db.has_students_out()
            except Exception as e:
                print(f"[WARN] Could not query has_students_out: {e}")
 
            # Turn off both LEDs first
            GPIO.output(self.RED_LED_PIN, GPIO.LOW)
            GPIO.output(self.GREEN_LED_PIN, GPIO.LOW)
 
            if restricted_period or is_passing or has_students_out:
                GPIO.output(self.RED_LED_PIN, GPIO.HIGH)
                if restricted_period:
                    reason = "restricted window"
                elif is_passing:
                    reason = "passing time"
                else:
                    reason = "students out"
                print(f"[LED] RED - Bathroom not allowed ({reason})")
            else:
                GPIO.output(self.GREEN_LED_PIN, GPIO.HIGH)
                print("[LED] GREEN - Bathroom allowed")
                 
        except Exception as e:
            print(f"[ERROR] Failed to update GPIO LED status: {e}")

    def _get_current_period_range(self, now: datetime):
        """Return (start_dt, end_dt) for the current period, else (None, None)."""
        for name, (sh, sm), (eh, em) in self.SCHEDULE:
            start_dt = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
            end_dt = now.replace(hour=eh, minute=em, second=0, microsecond=0)
            if start_dt <= now < end_dt:
                return start_dt, end_dt
        return None, None

    def _is_bathroom_restricted(self, now: datetime) -> bool:
        """True if within first or last 10 minutes of current period."""
        start_dt, end_dt = self._get_current_period_range(now)
        if not start_dt or not end_dt:
            return False
        first_window = start_dt + timedelta(minutes=10)
        last_window = end_dt - timedelta(minutes=10)
        return now < first_window or now >= last_window

    def update_period_label(self):
        """Update the label under the clock with the current period/passing."""
        now = datetime.now()
        label = self._determine_current_period(now)
        # Render period text inside clock instead of separate label
        self.analog_clock.set_overlay_text(label)

    def _determine_current_period(self, now: datetime) -> str:
        """Return the current period label or Passing/Before/After School."""
        # Build today's datetimes for schedule windows
        periods = []
        for name, (sh, sm), (eh, em) in self.SCHEDULE:
            start_dt = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
            end_dt = now.replace(hour=eh, minute=em, second=0, microsecond=0)
            periods.append((name, start_dt, end_dt))

        # Determine where now falls
        for idx, (name, start_dt, end_dt) in enumerate(periods):
            if start_dt <= now < end_dt:
                return name
            # Passing window: between this end and next start
            if idx < len(periods) - 1:
                next_start = periods[idx + 1][1]
                if end_dt <= now < next_start:
                    return "Passing"

        # Outside school day
        if now < periods[0][1]:
            return "Before School"
        if now >= periods[-1][2]:
            return "After School"
        return ""
    
    def cleanup_gpio(self):
        """Clean up GPIO resources"""
        if GPIO_AVAILABLE:
            try:
                GPIO.cleanup()
                print("[INFO] GPIO cleaned up")
            except Exception as e:
                print(f"[ERROR] GPIO cleanup failed: {e}")

    def show_keypad_overlay(self, event):
        """Show the keypad overlay for manual ID entry"""
        self.keypad_overlay.show_overlay()

    def handle_manual_id_entry(self, student_id):
        """Handle manual ID entry from keypad"""
        result = self.db.get_student_by_student_id(student_id)
        if result:
            nfc_uid, student_name = result
            print(f"[DEBUG] Manual entry resolved student_id {student_id} to nfc_uid {nfc_uid}")
            success, message = self.db.check_in(nfc_uid=nfc_uid if nfc_uid else None, student_id=student_id if not nfc_uid else None)
            if success:
                self.show_prompt_message(f"Student: {student_name}\n(ID: {student_id}) checked in.")
            else:
                self.show_prompt_message(message)
        else:
            self.show_prompt_message(f"No student found with ID: {student_id}")

    def eventFilter(self, obj, event):
        """Event filter for long press on header to show settings"""
        if obj == self.header:
            if event.type() == event.MouseButtonPress:
                self._header_press_time = datetime.now()
                self._header_timer.start(5000)
            elif event.type() == event.MouseButtonRelease:
                self._header_timer.stop()
            elif event.type() == event.Leave:
                self._header_timer.stop()
        return super().eventFilter(obj, event)

    def _show_settings_overlay(self):
        """Show the settings overlay"""
        self.settings_overlay.show_overlay()

    def show_bathroom_overlay(self):
        """Show the bathroom break overlay"""
        self.bathroom_overlay.show_overlay()

    def show_nurse_overlay(self):
        """Show the nurse visit overlay"""
        self.nurse_overlay.show_overlay()

    def process_bathroom_entry(self, student_id=None, nfc_uid=None):
        """Process bathroom break entry/exit"""
        # Disallow during restricted windows
        if self._is_bathroom_restricted(datetime.now()):
            self.prompt.setText("Bathroom closed first/last 10 minutes of class")
            QTimer.singleShot(3000, lambda: self.prompt.setText("Tap your ID or enter ID number"))
            return
        # Unified logic: use nfc_uid if available, else use student_id
        if nfc_uid:
            result = self.db.get_student_by_uid(nfc_uid)
            if not result:
                self.prompt.setText("No student found with that card.")
                return
            student_id_db, _ = result
            identifier = nfc_uid if nfc_uid else student_id_db
        elif student_id:
            result = self.db.get_student_by_student_id(student_id)
            if not result:
                self.prompt.setText("No student found with that ID.")
                return
            nfc_uid_db, _ = result
            identifier = nfc_uid_db if nfc_uid_db else student_id
        else:
            self.prompt.setText("No student information provided.")
            return

        print(f"[DEBUG] Bathroom entry using identifier: {identifier}")
        is_on_break = self.db.is_on_break(identifier)
        if is_on_break:
            success, message = self.db.end_bathroom_break(identifier)
            if success:
                self.prompt.setText("Bathroom break ended!")
                self.update_gpio_led_status()  # Immediately update GPIO LED
                QTimer.singleShot(3000, self.bathroom_overlay.hide)
                QTimer.singleShot(3000, lambda: self.prompt.setText("Tap your ID or enter ID number"))
            else:
                self.prompt.setText(message)
        else:
            # Let start_bathroom_break handle auto-check-in
            success, message = self.db.start_bathroom_break(identifier)
            if success:
                self.prompt.setText("Bathroom break started!")
                self.update_gpio_led_status()  # Immediately update GPIO LED
                QTimer.singleShot(3000, self.bathroom_overlay.hide)
                QTimer.singleShot(3000, lambda: self.prompt.setText("Tap your ID or enter ID number"))
            else:
                self.prompt.setText(message)

    def process_nurse_entry(self, student_id=None, nfc_uid=None):
        """Process nurse visit entry/exit"""
        # Unified logic: use nfc_uid if available, else use student_id
        if nfc_uid:
            result = self.db.get_student_by_uid(nfc_uid)
            if not result:
                self.prompt.setText("No student found with that card.")
                return
            student_id_db, _ = result
            identifier = nfc_uid if nfc_uid else student_id_db
        elif student_id:
            result = self.db.get_student_by_student_id(student_id)
            if not result:
                self.prompt.setText("No student found with that ID.")
                return
            nfc_uid_db, _ = result
            identifier = nfc_uid_db if nfc_uid_db else student_id
        else:
            self.prompt.setText("No student information provided.")
            return

        print(f"[DEBUG] Nurse entry using identifier: {identifier}")
        is_on_nurse_visit = self.db.is_at_nurse(identifier)
        if is_on_nurse_visit:
            # Pass the correct parameters to end_nurse_visit
            success, message = self.db.end_nurse_visit(nfc_uid=nfc_uid, student_id=student_id)
            if success:
                self.prompt.setText("Nurse visit ended!")
                self.update_gpio_led_status()  # Immediately update GPIO LED
                QTimer.singleShot(3000, self.nurse_overlay.hide)
                QTimer.singleShot(3000, lambda: self.prompt.setText("Tap your ID or enter ID number"))
            else:
                self.prompt.setText(message)
        else:
            # Let start_nurse_visit handle auto-check-in
            success, message = self.db.start_nurse_visit(nfc_uid=nfc_uid, student_id=student_id)
            if success:
                self.prompt.setText("Nurse visit started!")
                self.update_gpio_led_status()  # Immediately update GPIO LED
                QTimer.singleShot(3000, self.nurse_overlay.hide)
                QTimer.singleShot(3000, lambda: self.prompt.setText("Tap your ID or enter ID number"))
            else:
                self.prompt.setText(message)

    def read_serial(self):
        """Read data from serial connection and process NFC cards"""
        if not self.serial_connection:
            return
        try:
            if self.serial_connection.is_open and self.serial_connection.in_waiting:
                data = self.serial_connection.readline().decode('utf-8').strip()
                print(f"[DEBUG] Received serial data: '{data}'")
                if data:
                    uid = self.parse_uid(data)
                    print(f"[DEBUG] Parsed UID: {uid}")
                    if uid:
                        # Check if add student overlay is open
                        if hasattr(self, 'add_student_overlay') and self.add_student_overlay.isVisible():
                            print(f"[DEBUG] Auto-filling NFC UID in add student overlay: {uid}")
                            self.add_student_overlay.auto_fill_nfc_uid(uid)
                            return
                        
                        if self.bathroom_overlay.isVisible():
                            print(f"[DEBUG] Processing bathroom entry with UID: {uid}")
                            self.bathroom_overlay.process_card(uid)
                            return
                        
                        if self.nurse_overlay.isVisible():
                            print(f"[DEBUG] Processing nurse entry with UID: {uid}")
                            self.nurse_overlay.process_card(uid)
                            return
                        
                        # Normal check-in process
                        print(f"[DEBUG] Processing normal check-in with UID: {uid}")
                        self.current_student_id = uid
                        result = self.db.get_student_by_uid(uid)
                        if result:
                            student_id, student_name = result
                            print(f"[DEBUG] Found student: {student_name} (ID: {student_id})")
                            success, message = self.db.check_in(nfc_uid=uid)
                            if success:
                                print(f"[DEBUG] Check-in successful for {student_name}")
                                self.show_prompt_message(f"Student: {student_name}\n(ID: {student_id}) checked in.")
                            else:
                                print(f"[DEBUG] Check-in failed: {message}")
                                self.show_prompt_message(message)
                        else:
                            print(f"[DEBUG] Unknown student with UID: {uid}")
                            # Show unknown card message immediately, then check for linking options
                            self.show_prompt_message(f"Unknown Card (UID: {uid})\nChecking for students to link...")
                            # Check if there are students without NFC UIDs
                            unassigned_students = self.db.get_students_without_nfc_uid()
                            if unassigned_students:
                                print(f"[DEBUG] Found {len(unassigned_students)} students without NFC UIDs, showing selection overlay")
                                self.student_selection_overlay.show_overlay(uid)
                            else:
                                print(f"[DEBUG] No students without NFC UIDs found")
                                self.show_prompt_message(f"Unknown Student (UID: {uid})\nNo unassigned students available")
        except Exception as e:
            print(f"[DEBUG] Serial error: {e}")
            QMessageBox.critical(self, "Serial Error", str(e))

    def show_prompt_message(self, message, duration=3000):
        """Show a message in the prompt area for a specified duration"""
        self.prompt.setText(message)
        self.message_timer.start(duration)
    
    def clear_prompt_message(self):
        """Clear the prompt message and restore default text"""
        self.prompt.setText("Tap your ID or enter ID number")
    
    def handle_card_linked(self, nfc_uid, student_name):
        """Handle successful card linking by automatically checking in the student"""
        print(f"[DEBUG] Card {nfc_uid} linked to {student_name}, attempting auto check-in")
        
        # Try to check in the student with the newly linked card
        success, message = self.db.check_in(nfc_uid=nfc_uid)
        if success:
            self.show_prompt_message(f"Card linked to {student_name}\nStudent checked in successfully!")
        else:
            self.show_prompt_message(f"Card linked to {student_name}\nCheck-in: {message}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = NFCReaderGUI()
    window.show()
    
    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        print("\n[INFO] Application interrupted by user")
        window.cleanup_gpio()
        sys.exit(0)
