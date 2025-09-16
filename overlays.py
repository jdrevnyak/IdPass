"""
Overlay classes for the NFC Reader GUI application.
"""

import serial
import serial.tools.list_ports
import os
import sys
import subprocess
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QComboBox, QPushButton, QMessageBox, QLineEdit,
                            QFormLayout, QGroupBox, QGridLayout, QSizePolicy, QApplication)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QFont


class KeypadOverlay(QWidget):
    """Overlay with numeric keypad for manual ID entry."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: rgba(0,0,0,0.5);")
        self.setWindowFlags(Qt.Widget | Qt.FramelessWindowHint)
        self.setVisible(False)
        self.setGeometry(parent.rect())
        self.parent = parent

        # Main layout for keypad
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        container = QWidget()
        container.setStyleSheet("background: white; border-radius: 24px;")
        container.setFixedSize(340, 440)
        vbox = QVBoxLayout(container)
        vbox.setAlignment(Qt.AlignCenter)
        vbox.setContentsMargins(24, 24, 24, 24)
        self.input = QLineEdit()
        self.input.setAlignment(Qt.AlignCenter)
        self.input.setFont(QFont('Arial', 28, QFont.Bold))
        self.input.setReadOnly(True)
        self.input.setStyleSheet(
            "QLineEdit { background: #fff; color: #23405a; border: 2px solid #23405a; border-radius: 10px; padding: 8px; }"
        )
        vbox.addWidget(self.input)
        grid = QGridLayout()
        buttons = [
            ('1', 0, 0), ('2', 0, 1), ('3', 0, 2),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2),
            ('7', 2, 0), ('8', 2, 1), ('9', 2, 2),
            ('Clear', 3, 0), ('0', 3, 1), ('OK', 3, 2)
        ]
        for text, row, col in buttons:
            btn = QPushButton(text)
            btn.setFont(QFont('Arial', 22, QFont.Bold))
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            if text.isdigit():
                btn.setStyleSheet(
                    "QPushButton { background: #f5f7fa; color: #23405a; border-radius: 16px; border: 2px solid #23405a; }"
                    "QPushButton:hover { background: #e0e7ef; }"
                    "QPushButton:pressed { background: #cfd8e3; }"
                )
            elif text == 'Clear':
                btn.setStyleSheet(
                    "QPushButton { background: #e0e0e0; color: #23405a; border-radius: 16px; border: 2px solid #b0b0b0; }"
                    "QPushButton:hover { background: #cccccc; }"
                    "QPushButton:pressed { background: #bbbbbb; }"
                )
            elif text == 'OK':
                btn.setStyleSheet(
                    "QPushButton { background: #2bb3a3; color: white; border-radius: 16px; border: 2px solid #249e90; }"
                    "QPushButton:hover { background: #249e90; }"
                    "QPushButton:pressed { background: #1e857a; }"
                )
            grid.addWidget(btn, row, col)
            if text.isdigit():
                btn.clicked.connect(lambda _, t=text: self.input.setText(self.input.text() + t))
            elif text == 'Clear':
                btn.clicked.connect(lambda: self.input.setText(''))
            elif text == 'OK':
                btn.clicked.connect(self.ok_pressed)
        vbox.addLayout(grid)
        # Cancel button below keypad
        cancel_btn = QPushButton('Cancel')
        cancel_btn.setFont(QFont('Arial', 18))
        cancel_btn.setStyleSheet('QPushButton { background: #eee; color: #23405a; border-radius: 12px; padding: 8px 0; border: 2px solid #b0b0b0; } QPushButton:hover { background: #e0e0e0; } QPushButton:pressed { background: #cccccc; }')
        cancel_btn.clicked.connect(self.hide)
        vbox.addWidget(cancel_btn)
        layout.addWidget(container)

    def ok_pressed(self):
        student_id = self.input.text()
        self.hide()
        if student_id:
            self.parent.handle_manual_id_entry(student_id)

    def show_overlay(self):
        self.input.setText("")
        self.setGeometry(self.parent.rect())
        self.setVisible(True)
        self.raise_()

    def hideEvent(self, event):
        self.setVisible(False)


class SettingsOverlay(QWidget):
    """Overlay for application settings including ESP32 connection."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: rgba(0,0,0,0.5);")
        self.setWindowFlags(Qt.Widget | Qt.FramelessWindowHint)
        self.setVisible(False)
        self.setGeometry(parent.rect())
        self.parent = parent
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create scrollable container
        from PyQt5.QtWidgets import QScrollArea
        scroll_area = QScrollArea()
        scroll_area.setFixedSize(550, 450)  # Fits in 800x480 screen
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setFrameShape(0)  # NoFrame
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                border-radius: 24px;
                background: white;
            }
            QScrollBar:vertical {
                background: #f0f0f0;
                width: 12px;
                border-radius: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #c0c0c0;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a0a0a0;
            }
        """)
        
        container = QWidget()
        container.setStyleSheet("background: white; border-radius: 24px;")
        vbox = QVBoxLayout(container)
        vbox.setAlignment(Qt.AlignTop)
        vbox.setContentsMargins(20, 20, 20, 20)
        vbox.setSpacing(12)
        
        # Title
        title = QLabel("Settings")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont('Arial', 22, QFont.Bold))
        title.setStyleSheet("color: #23405a; margin-bottom: 8px;")
        vbox.addWidget(title)
        
        # Serial Connection Section
        connection_group = QGroupBox("ESP32 Connection")
        connection_group.setFont(QFont('Arial', 14, QFont.Bold))
        connection_group.setStyleSheet("QGroupBox { font-weight: bold; border: 2px solid #23405a; border-radius: 8px; margin-top: 8px; padding-top: 8px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px 0 5px; }")
        connection_layout = QVBoxLayout(connection_group)
        
        # Port selection
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(200)
        self.refresh_ports()
        port_layout.addWidget(self.port_combo)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_ports)
        port_layout.addWidget(refresh_btn)
        connection_layout.addLayout(port_layout)
        
        # Connection button
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.toggle_connection)
        self.connect_button.setStyleSheet('QPushButton { background: #2bb3a3; color: white; border-radius: 12px; padding: 8px 0; } QPushButton:hover { background: #249e90; } QPushButton:pressed { background: #1e857a; }')
        connection_layout.addWidget(self.connect_button)
        
        # Status label
        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        connection_layout.addWidget(self.status_label)
        
        vbox.addWidget(connection_group)
        
        # Database Sync Status Section
        sync_group = QGroupBox("Database Sync Status")
        sync_group.setFont(QFont('Arial', 14, QFont.Bold))
        sync_group.setStyleSheet("QGroupBox { font-weight: bold; border: 2px solid #23405a; border-radius: 8px; margin-top: 8px; padding-top: 8px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px 0 5px; }")
        sync_layout = QVBoxLayout(sync_group)
        
        # Sync status label
        self.sync_status_label = QLabel("Checking sync status...")
        self.sync_status_label.setStyleSheet("color: #666; font-size: 12px; margin: 5px 0;")
        sync_layout.addWidget(self.sync_status_label)
        
        # Force sync button
        force_sync_btn = QPushButton('Force Sync Now')
        force_sync_btn.setFont(QFont('Arial', 12))
        force_sync_btn.setStyleSheet('QPushButton { background: #3498db; color: white; border-radius: 8px; padding: 6px 12px; } QPushButton:hover { background: #2980b9; } QPushButton:pressed { background: #21618c; }')
        force_sync_btn.clicked.connect(self.force_sync)
        sync_layout.addWidget(force_sync_btn)
        
        # Check for updates button
        check_updates_btn = QPushButton('Check for Updates')
        check_updates_btn.setFont(QFont('Arial', 12))
        check_updates_btn.setStyleSheet('QPushButton { background: #9b59b6; color: white; border-radius: 8px; padding: 6px 12px; } QPushButton:hover { background: #8e44ad; } QPushButton:pressed { background: #7d3c98; }')
        check_updates_btn.clicked.connect(self.check_for_updates)
        sync_layout.addWidget(check_updates_btn)
        
        # Current version display
        self.current_version_label = QLabel("Current Version: Checking...")
        self.current_version_label.setStyleSheet("color: #666; font-size: 11px; margin: 5px 0;")
        sync_layout.addWidget(self.current_version_label)
        
        vbox.addWidget(sync_group)
        
        # Add New Student button
        add_btn = QPushButton('Add New Student')
        add_btn.setFont(QFont('Arial', 14, QFont.Bold))
        add_btn.setStyleSheet('QPushButton { background: #2bb3a3; color: white; border-radius: 12px; padding: 10px 0; } QPushButton:hover { background: #249e90; } QPushButton:pressed { background: #1e857a; }')
        add_btn.clicked.connect(self.show_add_student_dialog)
        vbox.addWidget(add_btn)
        
        # Student Management Section
        student_mgmt_group = QGroupBox("Student Management")
        student_mgmt_group.setFont(QFont('Arial', 14, QFont.Bold))
        student_mgmt_group.setStyleSheet("QGroupBox { font-weight: bold; border: 2px solid #23405a; border-radius: 8px; margin-top: 8px; padding-top: 8px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px 0 5px; }")
        student_mgmt_layout = QVBoxLayout(student_mgmt_group)
        
        # End Active Breaks button
        end_breaks_btn = QPushButton('End All Active Breaks')
        end_breaks_btn.setFont(QFont('Arial', 12))
        end_breaks_btn.setStyleSheet('QPushButton { background: #e67e22; color: white; border-radius: 8px; padding: 8px 12px; } QPushButton:hover { background: #d35400; } QPushButton:pressed { background: #a04000; }')
        end_breaks_btn.clicked.connect(self.end_all_active_breaks)
        student_mgmt_layout.addWidget(end_breaks_btn)
        
        # Status display for active breaks
        self.active_breaks_label = QLabel("Checking for active breaks...")
        self.active_breaks_label.setStyleSheet("color: #666; font-size: 11px; margin: 5px 0;")
        student_mgmt_layout.addWidget(self.active_breaks_label)
        
        vbox.addWidget(student_mgmt_group)
        
        # App Control Section
        app_control_group = QGroupBox("Application Control")
        app_control_group.setFont(QFont('Arial', 14, QFont.Bold))
        app_control_group.setStyleSheet("QGroupBox { font-weight: bold; border: 2px solid #23405a; border-radius: 8px; margin-top: 8px; padding-top: 8px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px 0 5px; }")
        app_control_layout = QHBoxLayout(app_control_group)
        
        # Restart button
        restart_btn = QPushButton('Restart App')
        restart_btn.setFont(QFont('Arial', 14, QFont.Bold))
        restart_btn.setStyleSheet('QPushButton { background: #f39c12; color: white; border-radius: 12px; padding: 8px 16px; } QPushButton:hover { background: #e67e22; } QPushButton:pressed { background: #d35400; }')
        restart_btn.clicked.connect(self.restart_application)
        app_control_layout.addWidget(restart_btn)
        
        # Quit button
        quit_btn = QPushButton('Quit App')
        quit_btn.setFont(QFont('Arial', 14, QFont.Bold))
        quit_btn.setStyleSheet('QPushButton { background: #e74c3c; color: white; border-radius: 12px; padding: 8px 16px; } QPushButton:hover { background: #c0392b; } QPushButton:pressed { background: #a93226; }')
        quit_btn.clicked.connect(self.quit_application)
        app_control_layout.addWidget(quit_btn)
        
        vbox.addWidget(app_control_group)
        
        # Close button
        close_btn = QPushButton('Close Settings')
        close_btn.setFont(QFont('Arial', 12))
        close_btn.setStyleSheet('QPushButton { background: #95a5a6; color: white; border-radius: 8px; padding: 8px 12px; margin-top: 8px; } QPushButton:hover { background: #7f8c8d; } QPushButton:pressed { background: #6c7b7d; }')
        close_btn.clicked.connect(lambda: self.setVisible(False))
        vbox.addWidget(close_btn)
        
        # Set the container as the scroll area widget
        scroll_area.setWidget(container)
        layout.addWidget(scroll_area)
        
        # Update connection status
        self.update_connection_status()
        
        # Update active breaks status
        self.update_active_breaks_status()

    def refresh_ports(self):
        """Refresh the list of available serial ports"""
        self.port_combo.clear()
        ports = [port.device for port in serial.tools.list_ports.comports() 
                if not port.device.endswith('debugconsole')]
        if not ports:
            self.status_label.setText("Status: No serial ports found")
        self.port_combo.addItems(ports)
    
    def toggle_connection(self):
        """Connect to or disconnect from the selected serial port"""
        if self.parent.serial_connection is None:
            try:
                port = self.port_combo.currentText()
                if not port:
                    QMessageBox.warning(self, "Connection Error", "No port selected")
                    return
                
                self.parent.serial_connection = serial.Serial(port, 115200, timeout=0.1)
                self.status_label.setText(f"Status: Connected to {port}")
                self.connect_button.setText("Disconnect")
                self.parent.timer.start(100)  # Read every 100ms
                self.parent.connection_error_count = 0
            except Exception as e:
                QMessageBox.critical(self, "Connection Error", str(e))
        else:
            self.disconnect()
    
    def disconnect(self):
        """Safely disconnect from the serial port"""
        try:
            if self.parent.serial_connection and self.parent.serial_connection.is_open:
                self.parent.serial_connection.close()
        except:
            pass
        finally:
            self.parent.serial_connection = None
            self.status_label.setText("Status: Disconnected")
            self.connect_button.setText("Connect")
            self.parent.timer.stop()
    
    def update_connection_status(self):
        """Update the connection status display"""
        if self.parent.serial_connection and self.parent.serial_connection.is_open:
            port = self.parent.serial_connection.port
            self.status_label.setText(f"Status: Connected to {port}")
            self.connect_button.setText("Disconnect")
        else:
            self.status_label.setText("Status: Disconnected")
            self.connect_button.setText("Connect")

    def show_add_student_dialog(self):
        self.parent.add_student_overlay.show_overlay()
    
    def force_sync(self):
        """Force an immediate sync to Google Sheets"""
        try:
            self.parent.db.force_sync()
            self.update_sync_status()
            QMessageBox.information(self, "Sync Complete", "Data has been synced to Google Sheets successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Sync Error", f"Error during sync: {str(e)}")
    
    def check_for_updates(self):
        """Check for application updates"""
        try:
            # Check if update manager exists
            if hasattr(self.parent, 'update_manager') and self.parent.update_manager:
                # Disable the button temporarily to prevent multiple clicks
                sender = self.sender()
                if sender:
                    sender.setEnabled(False)
                    sender.setText("Checking...")
                
                # Check for updates (show_message=True to show result)
                self.parent.update_manager.check_for_updates(show_message=True)
                
                # Re-enable the button after a delay
                QTimer.singleShot(3000, lambda: self.restore_update_button(sender))
            else:
                QMessageBox.warning(self, "Update Check", "Update manager is not available.")
        except Exception as e:
            QMessageBox.critical(self, "Update Check Error", f"Error checking for updates: {str(e)}")
    
    def restore_update_button(self, button):
        """Restore the update button to its original state"""
        if button:
            button.setEnabled(True)
            button.setText("Check for Updates")
    
    def update_version_display(self):
        """Update the current version display"""
        try:
            if hasattr(self.parent, 'update_manager') and self.parent.update_manager:
                version = self.parent.update_manager.current_version
                self.current_version_label.setText(f"Current Version: {version}")
            else:
                self.current_version_label.setText("Current Version: Unknown")
        except Exception as e:
            self.current_version_label.setText("Current Version: Error")
    
    def update_sync_status(self):
        """Update the sync status display"""
        try:
            status = self.parent.db.get_sync_status()
            
            last_sync_text = "Never"
            if status['last_sync']:
                last_sync_text = status['last_sync'].strftime("%H:%M:%S")
            
            status_text = f"Google Sheets: {'Connected' if status['google_sheets_connected'] else 'Disconnected'}\n"
            status_text += f"Last Sync: {last_sync_text}\n"
            status_text += f"Pending Changes: {status['pending_changes']}\n"
            status_text += f"Sync Interval: {status['sync_interval_minutes']} minutes"
            
            self.sync_status_label.setText(status_text)
            
            # Color coding
            if status['google_sheets_connected']:
                if status['pending_changes'] == 0:
                    color = "#27ae60"  # Green - all synced
                else:
                    color = "#f39c12"  # Orange - pending changes
            else:
                color = "#e74c3c"  # Red - disconnected
            
            self.sync_status_label.setStyleSheet(f"color: {color}; font-size: 12px; margin: 5px 0;")
            
        except Exception as e:
            self.sync_status_label.setText(f"Error getting sync status: {str(e)}")
            self.sync_status_label.setStyleSheet("color: #e74c3c; font-size: 12px; margin: 5px 0;")
    
    def update_active_breaks_status(self):
        """Update the active breaks status display"""
        try:
            # Get active bathroom breaks and nurse visits
            active_breaks = self.get_active_breaks_info()
            
            if not active_breaks:
                self.active_breaks_label.setText("No active breaks or nurse visits")
                self.active_breaks_label.setStyleSheet("color: #27ae60; font-size: 11px; margin: 5px 0;")
            else:
                break_text = f"Active: {len(active_breaks)} student(s) out"
                self.active_breaks_label.setText(break_text)
                self.active_breaks_label.setStyleSheet("color: #e67e22; font-size: 11px; margin: 5px 0;")
                
        except Exception as e:
            self.active_breaks_label.setText(f"Error checking active breaks: {str(e)}")
            self.active_breaks_label.setStyleSheet("color: #e74c3c; font-size: 11px; margin: 5px 0;")
    
    def get_active_breaks_info(self):
        """Get information about active bathroom breaks and nurse visits"""
        active_breaks = []
        
        try:
            import sqlite3
            conn = sqlite3.connect(self.parent.db.db_name)
            cursor = conn.cursor()
            
            # Get active bathroom breaks
            cursor.execute('''
                SELECT s.name, 'bathroom' as type, b.break_start, b.student_uid
                FROM bathroom_breaks b
                JOIN students s ON b.student_uid = s.id OR b.student_uid = s.student_id
                WHERE b.break_end IS NULL
            ''')
            
            for row in cursor.fetchall():
                active_breaks.append({
                    'name': row[0],
                    'type': row[1],
                    'start_time': row[2],
                    'uid': row[3]  # Use the actual student_uid for ending breaks
                })
            
            # Get active nurse visits
            cursor.execute('''
                SELECT s.name, 'nurse' as type, n.visit_start, n.student_uid
                FROM nurse_visits n
                JOIN students s ON n.student_uid = s.id OR n.student_uid = s.student_id
                WHERE n.visit_end IS NULL
            ''')
            
            for row in cursor.fetchall():
                active_breaks.append({
                    'name': row[0],
                    'type': row[1],
                    'start_time': row[2],
                    'uid': row[3]  # Use the actual student_uid for ending breaks
                })
            
            conn.close()
            
        except Exception as e:
            print(f"Error getting active breaks info: {e}")
            
        return active_breaks
    
    def end_all_active_breaks(self):
        """End all active bathroom breaks and nurse visits"""
        try:
            # Get active breaks first
            active_breaks = self.get_active_breaks_info()
            
            if not active_breaks:
                QMessageBox.information(self, "No Active Breaks", "There are currently no active bathroom breaks or nurse visits.")
                return
            
            # Confirm action
            break_list = []
            for break_info in active_breaks:
                break_list.append(f"• {break_info['name']} ({break_info['type']} break)")
            
            break_text = "\\n".join(break_list)
            
            reply = QMessageBox.question(
                self, 
                "End Active Breaks", 
                f"Are you sure you want to end all active breaks?\\n\\n{break_text}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                ended_count = 0
                
                # End each active break
                for break_info in active_breaks:
                    try:
                        if break_info['type'] == 'bathroom':
                            # End bathroom break using the stored UID
                            success, message = self.parent.db.end_bathroom_break(break_info['uid'])
                            if success:
                                ended_count += 1
                        elif break_info['type'] == 'nurse':
                            # End nurse visit using the stored UID
                            # Check if the UID looks like an NFC UID or student ID
                            if len(break_info['uid']) > 10 or break_info['uid'].isalnum() and not break_info['uid'].isdigit():
                                # Looks like NFC UID
                                success, message = self.parent.db.end_nurse_visit(nfc_uid=break_info['uid'])
                            else:
                                # Looks like student ID
                                success, message = self.parent.db.end_nurse_visit(student_id=break_info['uid'])
                            if success:
                                ended_count += 1
                    except Exception as e:
                        print(f"Error ending break for {break_info['name']}: {e}")
                
                # Update status and show result
                self.update_active_breaks_status()
                self.parent.update_gpio_led_status()  # Update LED status
                
                QMessageBox.information(
                    self, 
                    "Breaks Ended", 
                    f"Successfully ended {ended_count} active break(s)."
                )
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error ending active breaks: {str(e)}")
    
    def restart_application(self):
        """Restart the application"""
        reply = QMessageBox.question(self, 'Restart Application', 
                                   'Are you sure you want to restart the application?',
                                   QMessageBox.Yes | QMessageBox.No, 
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            print("[INFO] Restarting application...")
            
            # Clean up GPIO before restart
            self.parent.cleanup_gpio()
            
            # Simple approach: just exit and let systemd restart
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                app.closeAllWindows()
                app.quit()
            
            # Force exit
            import sys
            sys.exit(0)
    
    def quit_application(self):
        """Quit the application"""
        reply = QMessageBox.question(self, 'Quit Application', 
                                   'Are you sure you want to quit the application?',
                                   QMessageBox.Yes | QMessageBox.No, 
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            print("[INFO] Quitting application...")
            # Clean up GPIO before quitting
            self.parent.cleanup_gpio()
            QApplication.quit()

    def show_overlay(self):
        self.setGeometry(self.parent.rect())
        self.setVisible(True)
        self.raise_()
        self.refresh_ports()
        self.update_connection_status()
        self.update_sync_status()
        self.update_active_breaks_status()
        self.update_version_display()

    def mousePressEvent(self, event):
        # Dismiss if click outside the white box
        for child in self.children():
            if isinstance(child, QWidget) and child.geometry().contains(event.pos()):
                return
        self.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()


class BathroomOverlay(QWidget):
    """Overlay for bathroom break functionality."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: rgba(0,0,0,0.7);")
        self.setWindowFlags(Qt.Widget | Qt.FramelessWindowHint)
        self.setVisible(False)
        self.setGeometry(parent.rect())
        self.parent = parent
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Left side: Keypad (full height)
        keypad_container = QWidget()
        keypad_container.setStyleSheet("background: white; border-top-left-radius: 24px; border-bottom-left-radius: 24px;")
        keypad_container.setFixedWidth(400)
        keypad_layout = QVBoxLayout(keypad_container)
        keypad_layout.setContentsMargins(24, 24, 24, 24)
        keypad_layout.setSpacing(16)
        
        # Keypad title
        keypad_title = QLabel("Enter ID Number")
        keypad_title.setAlignment(Qt.AlignCenter)
        keypad_title.setFont(QFont('Arial', 20, QFont.Bold))
        keypad_title.setStyleSheet("color: #23405a; margin-bottom: 16px;")
        keypad_layout.addWidget(keypad_title)
        
        # Input field
        self.input = QLineEdit()
        self.input.setAlignment(Qt.AlignCenter)
        self.input.setFont(QFont('Arial', 24, QFont.Bold))
        self.input.setReadOnly(True)
        self.input.setStyleSheet(
            "QLineEdit { background: #fff; color: #23405a; border: 2px solid #23405a; border-radius: 12px; padding: 12px; margin-bottom: 16px; }"
        )
        keypad_layout.addWidget(self.input)
        
        # Keypad grid
        grid = QGridLayout()
        grid.setSpacing(12)
        buttons = [
            ('1', 0, 0), ('2', 0, 1), ('3', 0, 2),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2),
            ('7', 2, 0), ('8', 2, 1), ('9', 2, 2),
            ('Clear', 3, 0), ('0', 3, 1), ('OK', 3, 2)
        ]
        for text, row, col in buttons:
            btn = QPushButton(text)
            btn.setFont(QFont('Arial', 18, QFont.Bold))
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setMinimumHeight(60)
            if text.isdigit():
                btn.setStyleSheet(
                    "QPushButton { background: #f5f7fa; color: #23405a; border-radius: 16px; border: 2px solid #23405a; }"
                    "QPushButton:hover { background: #e0e7ef; }"
                    "QPushButton:pressed { background: #cfd8e3; }"
                )
            elif text == 'Clear':
                btn.setStyleSheet(
                    "QPushButton { background: #e0e0e0; color: #23405a; border-radius: 16px; border: 2px solid #b0b0b0; }"
                    "QPushButton:hover { background: #cccccc; }"
                    "QPushButton:pressed { background: #bbbbbb; }"
                )
            elif text == 'OK':
                btn.setStyleSheet(
                    "QPushButton { background: #2bb3a3; color: white; border-radius: 16px; border: 2px solid #249e90; }"
                    "QPushButton:hover { background: #249e90; }"
                    "QPushButton:pressed { background: #1e857a; }"
                )
            grid.addWidget(btn, row, col)
            if text.isdigit():
                btn.clicked.connect(lambda _, t=text: self.input.setText(self.input.text() + t))
            elif text == 'Clear':
                btn.clicked.connect(lambda: self.input.setText(''))
            elif text == 'OK':
                btn.clicked.connect(self.ok_pressed)
        
        keypad_layout.addLayout(grid)
        keypad_layout.addStretch()
        
        # Right side: Text and info (full height)
        text_container = QWidget()
        text_container.setStyleSheet("background: white; border-top-right-radius: 24px; border-bottom-right-radius: 24px;")
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(40, 40, 40, 40)
        text_layout.setSpacing(24)
        
        # Main title
        main_title = QLabel("Bathroom Break")
        main_title.setAlignment(Qt.AlignCenter)
        main_title.setFont(QFont('Arial', 24, QFont.Bold))
        main_title.setStyleSheet("color: #23405a; margin-bottom: 32px;")
        text_layout.addWidget(main_title)
        
        # Instructions
        instructions = QLabel("Scan your ID card or enter your ID number using the keypad on the left.")
        instructions.setAlignment(Qt.AlignCenter)
        instructions.setWordWrap(True)
        instructions.setFont(QFont('Arial', 18))
        instructions.setStyleSheet("color: #23405a; line-height: 1.4; margin-bottom: 32px;")
        text_layout.addWidget(instructions)
        
        # Current status
        self.status_label = QLabel("Ready to scan")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont('Arial', 20, QFont.Bold))
        self.status_label.setStyleSheet("color: #2bb3a3; margin-bottom: 32px;")
        text_layout.addWidget(self.status_label)
        
        # Message area for errors/info
        self.message_label = QLabel("")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.setFont(QFont('Arial', 16))
        self.message_label.setStyleSheet("color: #b71c1c; margin-bottom: 32px;")
        self.message_label.hide()
        text_layout.addWidget(self.message_label)
        
        text_layout.addStretch()
        
        # Cancel button at bottom
        cancel_btn = QPushButton('Cancel')
        cancel_btn.setFont(QFont('Arial', 18, QFont.Bold))
        cancel_btn.setStyleSheet('''
            QPushButton { 
                background: #e0e0e0; 
                color: #23405a; 
                border-radius: 16px; 
                padding: 16px 0; 
                border: 2px solid #b0b0b0; 
            } 
            QPushButton:hover { 
                background: #cccccc; 
            } 
            QPushButton:pressed { 
                background: #bbbbbb; 
            }
        ''')
        cancel_btn.clicked.connect(self.hide)
        text_layout.addWidget(cancel_btn)
        
        # Add both containers to main layout
        layout.addWidget(keypad_container)
        layout.addWidget(text_container)
        
        # Message timer
        self._message_timer = QTimer(self)
        self._message_timer.setSingleShot(True)
        self._message_timer.timeout.connect(self.clear_message)

    def show_overlay(self):
        self.input.setText("")
        self.setGeometry(self.parent.rect())
        self.setVisible(True)
        self.raise_()
        self.clear_message()
        self.status_label.setText("Ready to scan")
        self.status_label.setStyleSheet("color: #2bb3a3; margin-bottom: 32px;")

    def show_message(self, message, duration=4000):
        self.message_label.setText(message)
        self.message_label.show()
        self._message_timer.start(duration)

    def clear_message(self):
        self.message_label.hide()
        self.message_label.setText("")

    def ok_pressed(self):
        student_id = self.input.text()
        if student_id:
            self.parent.process_bathroom_entry(student_id=student_id)
            self.hide()

    def process_card(self, nfc_uid):
        self.parent.process_bathroom_entry(nfc_uid=nfc_uid)
        self.hide()


class NurseOverlay(QWidget):
    """Overlay for nurse visit functionality."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: rgba(0,0,0,0.7);")
        self.setWindowFlags(Qt.Widget | Qt.FramelessWindowHint)
        self.setVisible(False)
        self.setGeometry(parent.rect())
        self.parent = parent
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Left side: Keypad (full height)
        keypad_container = QWidget()
        keypad_container.setStyleSheet("background: white; border-top-left-radius: 24px; border-bottom-left-radius: 24px;")
        keypad_container.setFixedWidth(400)
        keypad_layout = QVBoxLayout(keypad_container)
        keypad_layout.setContentsMargins(24, 24, 24, 24)
        keypad_layout.setSpacing(16)
        
        # Keypad title
        keypad_title = QLabel("Enter ID Number")
        keypad_title.setAlignment(Qt.AlignCenter)
        keypad_title.setFont(QFont('Arial', 20, QFont.Bold))
        keypad_title.setStyleSheet("color: #23405a; margin-bottom: 16px;")
        keypad_layout.addWidget(keypad_title)
        
        # Input field
        self.input = QLineEdit()
        self.input.setAlignment(Qt.AlignCenter)
        self.input.setFont(QFont('Arial', 24, QFont.Bold))
        self.input.setReadOnly(True)
        self.input.setStyleSheet(
            "QLineEdit { background: #fff; color: #23405a; border: 2px solid #23405a; border-radius: 12px; padding: 12px; margin-bottom: 16px; }"
        )
        keypad_layout.addWidget(self.input)
        
        # Keypad grid
        grid = QGridLayout()
        grid.setSpacing(12)
        buttons = [
            ('1', 0, 0), ('2', 0, 1), ('3', 0, 2),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2),
            ('7', 2, 0), ('8', 2, 1), ('9', 2, 2),
            ('Clear', 3, 0), ('0', 3, 1), ('OK', 3, 2)
        ]
        for text, row, col in buttons:
            btn = QPushButton(text)
            btn.setFont(QFont('Arial', 18, QFont.Bold))
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setMinimumHeight(60)
            if text.isdigit():
                btn.setStyleSheet(
                    "QPushButton { background: #f5f7fa; color: #23405a; border-radius: 16px; border: 2px solid #23405a; }"
                    "QPushButton:hover { background: #e0e7ef; }"
                    "QPushButton:pressed { background: #cfd8e3; }"
                )
            elif text == 'Clear':
                btn.setStyleSheet(
                    "QPushButton { background: #e0e0e0; color: #23405a; border-radius: 16px; border: 2px solid #b0b0b0; }"
                    "QPushButton:hover { background: #cccccc; }"
                    "QPushButton:pressed { background: #bbbbbb; }"
                )
            elif text == 'OK':
                btn.setStyleSheet(
                    "QPushButton { background: #23405a; color: white; border-radius: 16px; border: 2px solid #1a2e3d; }"
                    "QPushButton:hover { background: #1a2e3d; }"
                    "QPushButton:pressed { background: #162534; }"
                )
            grid.addWidget(btn, row, col)
            if text.isdigit():
                btn.clicked.connect(lambda _, t=text: self.input.setText(self.input.text() + t))
            elif text == 'Clear':
                btn.clicked.connect(lambda: self.input.setText(''))
            elif text == 'OK':
                btn.clicked.connect(self.ok_pressed)
        
        keypad_layout.addLayout(grid)
        keypad_layout.addStretch()
        
        # Right side: Text and info (full height)
        text_container = QWidget()
        text_container.setStyleSheet("background: white; border-top-right-radius: 24px; border-bottom-right-radius: 24px;")
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(40, 40, 40, 40)
        text_layout.setSpacing(24)
        
        # Main title
        main_title = QLabel("Nurse Visit")
        main_title.setAlignment(Qt.AlignCenter)
        main_title.setFont(QFont('Arial', 24, QFont.Bold))
        main_title.setStyleSheet("color: #23405a; margin-bottom: 32px;")
        text_layout.addWidget(main_title)
        
        # Instructions
        instructions = QLabel("Scan your ID card or enter your ID number using the keypad on the left.")
        instructions.setAlignment(Qt.AlignCenter)
        instructions.setWordWrap(True)
        instructions.setFont(QFont('Arial', 18))
        instructions.setStyleSheet("color: #23405a; line-height: 1.4; margin-bottom: 32px;")
        text_layout.addWidget(instructions)
        
        # Current status
        self.status_label = QLabel("Ready to scan")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont('Arial', 20, QFont.Bold))
        self.status_label.setStyleSheet("color: #23405a; margin-bottom: 32px;")
        text_layout.addWidget(self.status_label)
        
        # Message area for errors/info
        self.message_label = QLabel("")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.setFont(QFont('Arial', 16))
        self.message_label.setStyleSheet("color: #b71c1c; margin-bottom: 32px;")
        self.message_label.hide()
        text_layout.addWidget(self.message_label)
        
        text_layout.addStretch()
        
        # Cancel button at bottom
        cancel_btn = QPushButton('Cancel')
        cancel_btn.setFont(QFont('Arial', 18, QFont.Bold))
        cancel_btn.setStyleSheet('''
            QPushButton { 
                background: #e0e0e0; 
                color: #23405a; 
                border-radius: 16px; 
                padding: 16px 0; 
                border: 2px solid #b0b0b0; 
            } 
            QPushButton:hover { 
                background: #cccccc; 
            } 
            QPushButton:pressed { 
                background: #bbbbbb; 
            }
        ''')
        cancel_btn.clicked.connect(self.hide)
        text_layout.addWidget(cancel_btn)
        
        # Add both containers to main layout
        layout.addWidget(keypad_container)
        layout.addWidget(text_container)
        
        # Message timer
        self._message_timer = QTimer(self)
        self._message_timer.setSingleShot(True)
        self._message_timer.timeout.connect(self.clear_message)

    def show_overlay(self):
        self.input.setText("")
        self.setGeometry(self.parent.rect())
        self.setVisible(True)
        self.raise_()
        self.clear_message()
        self.status_label.setText("Ready to scan")
        self.status_label.setStyleSheet("color: #23405a; margin-bottom: 32px;")

    def show_message(self, message, duration=4000):
        self.message_label.setText(message)
        self.message_label.show()
        self._message_timer.start(duration)

    def clear_message(self):
        self.message_label.hide()
        self.message_label.setText("")

    def ok_pressed(self):
        student_id = self.input.text()
        if student_id:
            self.parent.process_nurse_entry(student_id=student_id)
            self.hide()

    def process_card(self, nfc_uid):
        self.parent.process_nurse_entry(nfc_uid=nfc_uid)
        self.hide()


class AddStudentOverlay(QWidget):
    """Overlay for adding new students to the database."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: rgba(0,0,0,0.7);")
        self.setWindowFlags(Qt.Widget | Qt.FramelessWindowHint)
        self.setVisible(False)
        self.setGeometry(parent.rect())
        self.parent = parent
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        
        container = QWidget()
        container.setStyleSheet("background: white; border-radius: 24px;")
        container.setFixedSize(500, 450)
        vbox = QVBoxLayout(container)
        vbox.setAlignment(Qt.AlignCenter)
        vbox.setContentsMargins(40, 40, 40, 40)
        
        # Title
        title = QLabel("Add New Student")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont('Arial', 28, QFont.Bold))
        title.setStyleSheet("color: #23405a; margin-bottom: 32px;")
        vbox.addWidget(title)
        
        # NFC UID section with tap instruction
        nfc_section = QVBoxLayout()
        
        # NFC UID field with tap button
        nfc_layout = QHBoxLayout()
        nfc_layout.addWidget(QLabel("NFC UID:"))
        self.nfc_uid = QLineEdit()
        self.nfc_uid.setFont(QFont('Arial', 16))
        self.nfc_uid.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                border: 2px solid #23405a;
                border-radius: 12px;
                font-size: 16px;
            }
            QLineEdit:focus {
                border-color: #2bb3a3;
            }
        """)
        self.nfc_uid.setPlaceholderText("Tap your card to auto-fill")
        nfc_layout.addWidget(self.nfc_uid)
        
        # Tap card button
        self.tap_button = QPushButton("Tap Card")
        self.tap_button.setFont(QFont('Arial', 12, QFont.Bold))
        self.tap_button.setStyleSheet("""
            QPushButton {
                background: #2bb3a3;
                color: white;
                border-radius: 8px;
                padding: 8px 12px;
                border: none;
            }
            QPushButton:hover {
                background: #249e90;
            }
            QPushButton:pressed {
                background: #1e857a;
            }
        """)
        self.tap_button.clicked.connect(self.start_listening)
        nfc_layout.addWidget(self.tap_button)
        
        nfc_section.addLayout(nfc_layout)
        
        # Listening indicator
        self.listening_label = QLabel("Tap your card to auto-fill NFC UID")
        self.listening_label.setAlignment(Qt.AlignCenter)
        self.listening_label.setFont(QFont('Arial', 12))
        self.listening_label.setStyleSheet("color: #2bb3a3; font-style: italic; margin: 8px 0;")
        self.listening_label.hide()
        nfc_section.addWidget(self.listening_label)
        
        vbox.addLayout(nfc_section)
        
        # Form layout for other fields
        form_layout = QFormLayout()
        form_layout.setSpacing(20)
        
        # Student ID field
        self.student_id = QLineEdit()
        self.student_id.setFont(QFont('Arial', 16))
        self.student_id.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                border: 2px solid #23405a;
                border-radius: 12px;
                font-size: 16px;
            }
            QLineEdit:focus {
                border-color: #2bb3a3;
            }
        """)
        form_layout.addRow("Student ID:", self.student_id)
        
        # Student Name field
        self.student_name = QLineEdit()
        self.student_name.setFont(QFont('Arial', 16))
        self.student_name.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                border: 2px solid #23405a;
                border-radius: 12px;
                font-size: 16px;
            }
            QLineEdit:focus {
                border-color: #2bb3a3;
            }
        """)
        form_layout.addRow("Student Name:", self.student_name)
        
        vbox.addLayout(form_layout)
        
        # Message label for feedback
        self.message_label = QLabel("")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setFont(QFont('Arial', 14))
        self.message_label.setStyleSheet("color: #b71c1c; margin: 16px 0;")
        self.message_label.hide()
        vbox.addWidget(self.message_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(16)
        
        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFont(QFont('Arial', 16, QFont.Bold))
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #e0e0e0;
                color: #23405a;
                border-radius: 16px;
                padding: 12px 24px;
                border: 2px solid #b0b0b0;
            }
            QPushButton:hover {
                background: #cccccc;
            }
            QPushButton:pressed {
                background: #bbbbbb;
            }
        """)
        cancel_btn.clicked.connect(self.hide)
        button_layout.addWidget(cancel_btn)
        
        # Add button
        add_btn = QPushButton("Add Student")
        add_btn.setFont(QFont('Arial', 16, QFont.Bold))
        add_btn.setStyleSheet("""
            QPushButton {
                background: #2bb3a3;
                color: white;
                border-radius: 16px;
                padding: 12px 24px;
                border: 2px solid #249e90;
            }
            QPushButton:hover {
                background: #249e90;
            }
            QPushButton:pressed {
                background: #1e857a;
            }
        """)
        add_btn.clicked.connect(self.add_student)
        button_layout.addWidget(add_btn)
        
        vbox.addLayout(button_layout)
        layout.addWidget(container)
        
        # Message timer
        self._message_timer = QTimer(self)
        self._message_timer.setSingleShot(True)
        self._message_timer.timeout.connect(self.clear_message)
        
        # Listening state
        self.is_listening = False
    
    def show_overlay(self):
        """Show the overlay"""
        self.setGeometry(self.parent.rect())
        self.setVisible(True)
        self.raise_()
        self.clear_form()
        self.clear_message()
        self.stop_listening()
    
    def start_listening(self):
        """Start listening for NFC card"""
        self.is_listening = True
        self.listening_label.setText("Listening for card... Tap your card now")
        self.listening_label.setStyleSheet("color: #2bb3a3; font-style: italic; margin: 8px 0; font-weight: bold;")
        self.listening_label.show()
        self.tap_button.setText("Listening...")
        self.tap_button.setStyleSheet("""
            QPushButton {
                background: #ff9800;
                color: white;
                border-radius: 8px;
                padding: 8px 12px;
                border: none;
            }
            QPushButton:hover {
                background: #f57c00;
            }
            QPushButton:pressed {
                background: #ef6c00;
            }
        """)
    
    def stop_listening(self):
        """Stop listening for NFC card"""
        self.is_listening = False
        self.listening_label.hide()
        self.tap_button.setText("Tap Card")
        self.tap_button.setStyleSheet("""
            QPushButton {
                background: #2bb3a3;
                color: white;
                border-radius: 8px;
                padding: 8px 12px;
                border: none;
            }
            QPushButton:hover {
                background: #249e90;
            }
            QPushButton:pressed {
                background: #1e857a;
            }
        """)
    
    def auto_fill_nfc_uid(self, uid):
        """Auto-fill the NFC UID field when a card is tapped"""
        self.nfc_uid.setText(uid)
        self.listening_label.setText("Card detected! NFC UID auto-filled")
        self.listening_label.setStyleSheet("color: #4caf50; font-style: italic; margin: 8px 0; font-weight: bold;")
        self.listening_label.show()
        
        # Stop listening after successful detection
        QTimer.singleShot(2000, self.stop_listening)
    
    def clear_form(self):
        """Clear all form fields"""
        self.nfc_uid.setText("")
        self.student_id.setText("")
        self.student_name.setText("")
    
    def show_message(self, message, is_error=True, duration=3000):
        """Show a message with specified styling"""
        self.message_label.setText(message)
        if is_error:
            self.message_label.setStyleSheet("color: #b71c1c; margin: 16px 0; font-size: 14px;")
        else:
            self.message_label.setStyleSheet("color: #2bb3a3; margin: 16px 0; font-size: 14px;")
        self.message_label.show()
        self._message_timer.start(duration)
    
    def clear_message(self):
        """Clear the message"""
        self.message_label.hide()
        self.message_label.setText("")
    
    def add_student(self):
        """Add the student to the database"""
        nfc_uid = self.nfc_uid.text().strip()
        student_id = self.student_id.text().strip()
        name = self.student_name.text().strip()
        
        # Validate that at least one identifier is provided
        if not nfc_uid and not student_id:
            self.show_message("Please provide either NFC UID or Student ID")
            return
        
        if not name:
            self.show_message("Please provide a student name")
            return
        
        # Add student to database
        success = self.parent.db.add_student(nfc_uid, student_id, name)
        if success:
            self.show_message("Student added successfully!", is_error=False)
            self.clear_form()
            # Hide after successful addition
            QTimer.singleShot(2000, self.hide)
        else:
            self.show_message("Student with this NFC UID or Student ID already exists")
    
    def mousePressEvent(self, event):
        # Dismiss if click outside the white box
        for child in self.children():
            if isinstance(child, QWidget) and child.geometry().contains(event.pos()):
                return
        self.hide()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.add_student()


class StudentSelectionOverlay(QWidget):
    """Overlay for selecting a student to link an NFC card to."""
    
    # Signal emitted when a card is successfully linked
    card_linked = pyqtSignal(str, str)  # nfc_uid, student_name
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: rgba(0,0,0,0.7);")
        self.setWindowFlags(Qt.Widget | Qt.FramelessWindowHint)
        self.setVisible(False)
        self.setGeometry(parent.rect())
        self.parent = parent
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        
        container = QWidget()
        container.setStyleSheet("background: white; border-radius: 24px;")
        container.setFixedSize(600, 500)
        vbox = QVBoxLayout(container)
        vbox.setAlignment(Qt.AlignCenter)
        vbox.setContentsMargins(40, 40, 40, 40)
        
        # Title
        title = QLabel("Link NFC Card to Student")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont('Arial', 24, QFont.Bold))
        title.setStyleSheet("color: #23405a; margin-bottom: 16px;")
        vbox.addWidget(title)
        
        # NFC UID display
        self.nfc_uid_label = QLabel()
        self.nfc_uid_label.setAlignment(Qt.AlignCenter)
        self.nfc_uid_label.setFont(QFont('Arial', 16))
        self.nfc_uid_label.setStyleSheet("color: #666; background: #f5f7fa; padding: 12px; border-radius: 8px; margin-bottom: 16px;")
        vbox.addWidget(self.nfc_uid_label)
        
        # Instructions
        instructions = QLabel("Select a student to link this card to:")
        instructions.setAlignment(Qt.AlignCenter)
        instructions.setFont(QFont('Arial', 14))
        instructions.setStyleSheet("color: #23405a; margin-bottom: 16px;")
        vbox.addWidget(instructions)
        
        # Student list
        self.student_list = QComboBox()
        self.student_list.setFont(QFont('Arial', 14))
        self.student_list.setStyleSheet("""
            QComboBox {
                padding: 12px;
                border: 2px solid #23405a;
                border-radius: 12px;
                background: white;
                min-height: 20px;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #23405a;
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                border: 2px solid #23405a;
                border-radius: 8px;
                background: white;
                selection-background-color: #2bb3a3;
                selection-color: white;
            }
        """)
        vbox.addWidget(self.student_list)
        
        # Message area for errors/info
        self.message_label = QLabel("")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.setFont(QFont('Arial', 14))
        self.message_label.setStyleSheet("color: #b71c1c; margin: 16px 0; background: #ffebee; padding: 8px; border-radius: 8px; border: 1px solid #ffcdd2;")
        self.message_label.hide()
        vbox.addWidget(self.message_label)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Cancel button
        cancel_btn = QPushButton('Cancel')
        cancel_btn.setFont(QFont('Arial', 14, QFont.Bold))
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #e74c3c;
                color: white;
                border-radius: 12px;
                padding: 12px 24px;
                border: none;
            }
            QPushButton:hover {
                background: #c0392b;
            }
            QPushButton:pressed {
                background: #a93226;
            }
        """)
        cancel_btn.clicked.connect(self.hide)
        button_layout.addWidget(cancel_btn)
        
        # Link button
        self.link_btn = QPushButton('Link Card')
        self.link_btn.setFont(QFont('Arial', 14, QFont.Bold))
        self.link_btn.setStyleSheet("""
            QPushButton {
                background: #2bb3a3;
                color: white;
                border-radius: 12px;
                padding: 12px 24px;
                border: none;
            }
            QPushButton:hover {
                background: #249e90;
            }
            QPushButton:pressed {
                background: #1e857a;
            }
        """)
        self.link_btn.clicked.connect(self.link_card)
        button_layout.addWidget(self.link_btn)
        
        vbox.addLayout(button_layout)
        layout.addWidget(container)
        
        # Store the NFC UID for linking
        self.nfc_uid = None
        self.students_data = []
        
        # Message timer
        self._message_timer = QTimer(self)
        self._message_timer.setSingleShot(True)
        self._message_timer.timeout.connect(self.clear_message)
    
    def show_overlay(self, nfc_uid):
        """Show the overlay with the given NFC UID"""
        self.nfc_uid = nfc_uid
        self.nfc_uid_label.setText(f"NFC Card UID: {nfc_uid}")
        
        # Get students without NFC UIDs
        self.students_data = self.parent.db.get_students_without_nfc_uid()
        
        # Populate the dropdown
        self.student_list.clear()
        for student in self.students_data:
            self.student_list.addItem(f"{student['name']} (ID: {student['student_id']})")
        
        if not self.students_data:
            self.link_btn.setEnabled(False)
            self.link_btn.setText("No Students Available")
        else:
            self.link_btn.setEnabled(True)
            self.link_btn.setText("Link Card")
        
        self.setGeometry(self.parent.rect())
        self.setVisible(True)
        self.raise_()
        self.clear_message()
    
    def link_card(self):
        """Link the NFC card to the selected student"""
        if not self.nfc_uid or not self.students_data:
            return
        
        current_index = self.student_list.currentIndex()
        if current_index >= 0 and current_index < len(self.students_data):
            selected_student = self.students_data[current_index]
            
            # Link the card
            success, message = self.parent.db.link_nfc_card_to_student(
                self.nfc_uid, selected_student['student_id']
            )
            
            if success:
                self.show_message(f"Card successfully linked to {selected_student['name']}!", is_error=False)
                # Emit signal for successful card linking
                self.card_linked.emit(self.nfc_uid, selected_student['name'])
                # Hide after 2 seconds to allow user to see the success message
                QTimer.singleShot(2000, self.hide)
                # Update LED status since we now have a new student with a card
                self.parent.update_gpio_led_status()
            else:
                self.show_message(f"Failed to link card: {message}")
    
    def mousePressEvent(self, event):
        # Dismiss if click outside the white box
        for child in self.children():
            if isinstance(child, QWidget) and child.geometry().contains(event.pos()):
                return
        self.hide()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
    
    def show_message(self, message, is_error=True, duration=4000):
        """Show a message with specified styling"""
        self.message_label.setText(message)
        if is_error:
            self.message_label.setStyleSheet("color: #b71c1c; margin: 16px 0; background: #ffebee; padding: 8px; border-radius: 8px; border: 1px solid #ffcdd2;")
        else:
            self.message_label.setStyleSheet("color: #2e7d32; margin: 16px 0; background: #e8f5e8; padding: 8px; border-radius: 8px; border: 1px solid #c8e6c9;")
        self.message_label.show()
        self._message_timer.start(duration)
    
    def clear_message(self):
        """Clear the message"""
        self.message_label.hide()
        self.message_label.setText("")
    
    def show_message(self, message, is_error=True, duration=4000):
        """Show a message with specified styling"""
        self.message_label.setText(message)
        if is_error:
            self.message_label.setStyleSheet("color: #b71c1c; margin: 16px 0; background: #ffebee; padding: 8px; border-radius: 8px; border: 1px solid #ffcdd2;")
        else:
            self.message_label.setStyleSheet("color: #2e7d32; margin: 16px 0; background: #e8f5e8; padding: 8px; border-radius: 8px; border: 1px solid #c8e6c9;")
        self.message_label.show()
        self._message_timer.start(duration)
    
    def clear_message(self):
        """Clear the message"""
        self.message_label.hide()
        self.message_label.setText("")
