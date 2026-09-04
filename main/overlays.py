"""
Overlay classes for the NFC Reader GUI application.
"""

import serial
import serial.tools.list_ports
import os
import sys
import subprocess
import threading
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QComboBox, QPushButton, QMessageBox, QLineEdit,
                            QFormLayout, QGroupBox, QGridLayout, QSizePolicy, QApplication,
                            QScrollArea, QScroller, QFrame, QDialog, QTextEdit)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QEvent
from PyQt5.QtGui import QFont

from printer import list_usb_devices


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


class OnScreenKeyboard(QWidget):
    """Generic on-screen keyboard overlay for text input fields."""

    _KEY_W = 56
    _KEY_H = 48
    _KEY_SPACING = 5

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: rgba(0,0,0,0.55);")
        self.setWindowFlags(Qt.Widget | Qt.FramelessWindowHint)
        self.setVisible(False)
        self.setGeometry(parent.rect())
        self.parent = parent
        self.target_field = None

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setContentsMargins(0, 0, 0, 0)

        container = QWidget()
        container.setStyleSheet("background: #ecf0f4; border-radius: 18px;")
        container.setFixedSize(780, 430)
        vbox = QVBoxLayout(container)
        vbox.setAlignment(Qt.AlignTop)
        vbox.setContentsMargins(16, 14, 16, 14)
        vbox.setSpacing(8)

        self.title_label = QLabel("On-Screen Keyboard")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setFont(QFont('Arial', 18, QFont.Bold))
        self.title_label.setStyleSheet("color: #23405a;")
        vbox.addWidget(self.title_label)

        self.preview_field = QLineEdit()
        self.preview_field.setReadOnly(True)
        self.preview_field.setAlignment(Qt.AlignCenter)
        self.preview_field.setFont(QFont('Arial', 20, QFont.Bold))
        self.preview_field.setStyleSheet(
            "QLineEdit { background: white; color: #23405a; border: 2px solid #1f8b83; "
            "border-radius: 12px; padding: 8px; }"
        )
        self.preview_field.setFixedHeight(44)
        vbox.addWidget(self.preview_field)

        key_style = (
            "QPushButton { background: white; color: #23405a; border-radius: 8px; "
            "border: 1px solid #c8d0dc; font-weight: bold; }"
            "QPushButton:pressed { background: #cfd8e3; }"
        )

        key_rows = [
            list("1234567890"),
            list("QWERTYUIOP"),
            list("ASDFGHJKL"),
            list("ZXCVBNM"),
        ]

        for row_keys in key_rows:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(self._KEY_SPACING)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.addStretch(1)
            for key in row_keys:
                btn = QPushButton(key)
                btn.setFixedSize(self._KEY_W, self._KEY_H)
                btn.setFont(QFont('Arial', 16, QFont.Bold))
                btn.setStyleSheet(key_style)
                btn.clicked.connect(lambda _, char=key: self._append_text(char))
                row_layout.addWidget(btn)
            row_layout.addStretch(1)
            vbox.addLayout(row_layout)

        control_layout = QHBoxLayout()
        control_layout.setSpacing(8)
        control_layout.setContentsMargins(0, 4, 0, 0)

        control_buttons = [
            ("Space", self._append_space, "#2bb3a3"),
            ("Backspace", self._backspace, "#e67e22"),
            ("Clear", self._clear_text, "#c0392b"),
            ("Done", self.hide, "#3498db"),
        ]

        for label, handler, bg in control_buttons:
            btn = QPushButton(label)
            btn.setFixedHeight(48)
            btn.setFont(QFont('Arial', 15, QFont.Bold))
            btn.setStyleSheet(
                f"QPushButton {{ background: {bg}; color: white; border-radius: 10px; padding: 0 18px; }}"
                f"QPushButton:pressed {{ background: {self._darken_color(bg, 0.75)}; }}"
            )
            btn.clicked.connect(handler)
            control_layout.addWidget(btn, 1)

        vbox.addLayout(control_layout)
        main_layout.addWidget(container)

    def _darken_color(self, hex_color, factor):
        """Utility to darken a hex color."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            return hex_color
        r = max(0, min(255, int(int(hex_color[0:2], 16) * factor)))
        g = max(0, min(255, int(int(hex_color[2:4], 16) * factor)))
        b = max(0, min(255, int(int(hex_color[4:6], 16) * factor)))
        return f"#{r:02x}{g:02x}{b:02x}"

    def show_for(self, line_edit, label):
        """Display the keyboard for the provided QLineEdit."""
        self.target_field = line_edit
        self.title_label.setText(f"Editing: {label}")
        self._sync_preview()
        self.setGeometry(self.parent.rect())
        self.setVisible(True)
        self.raise_()

    def hideEvent(self, event):
        self.setVisible(False)
        self.target_field = None
        super().hideEvent(event)

    def _append_text(self, char):
        if not self.target_field:
            return
        self.target_field.setText(self.target_field.text() + char)
        self._sync_preview()

    def _append_space(self):
        self._append_text(" ")

    def _backspace(self):
        if not self.target_field:
            return
        current = self.target_field.text()
        self.target_field.setText(current[:-1])
        self._sync_preview()

    def _clear_text(self):
        if not self.target_field:
            return
        self.target_field.setText("")
        self._sync_preview()

    def _sync_preview(self):
        if self.target_field:
            self.preview_field.setText(self.target_field.text())
        else:
            self.preview_field.setText("")


class PasswordOverlay(QWidget):
    """Fullscreen numeric PIN overlay that gates access to the settings page."""

    authenticated = pyqtSignal()

    _MAX_PIN_LEN = 8
    _AUTO_DISMISS_MS = 30000

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: rgba(0,0,0,0.6);")
        self.setWindowFlags(Qt.Widget | Qt.FramelessWindowHint)
        self.setVisible(False)
        if parent:
            self.setGeometry(parent.rect())

        self._pin = ""
        self._custom_submit = None

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setContentsMargins(0, 0, 0, 0)

        container = QWidget()
        container.setStyleSheet("background: white; border-radius: 24px;")
        container.setFixedSize(420, 460)
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(28, 20, 28, 20)
        vbox.setSpacing(10)

        self._title_label = QLabel("Enter PIN")
        self._title_label.setAlignment(Qt.AlignCenter)
        self._title_label.setFont(QFont("Arial", 22, QFont.Bold))
        self._title_label.setStyleSheet("color: #23405a;")
        vbox.addWidget(self._title_label)

        self._dots_label = QLabel("")
        self._dots_label.setAlignment(Qt.AlignCenter)
        self._dots_label.setFont(QFont("Arial", 32))
        self._dots_label.setStyleSheet("color: #23405a; letter-spacing: 12px;")
        self._dots_label.setFixedHeight(48)
        vbox.addWidget(self._dots_label)

        self._error_label = QLabel("")
        self._error_label.setAlignment(Qt.AlignCenter)
        self._error_label.setFont(QFont("Arial", 13))
        self._error_label.setStyleSheet("color: #e74c3c;")
        self._error_label.setFixedHeight(20)
        vbox.addWidget(self._error_label)

        digit_style = (
            "QPushButton { background: #f0f3f8; color: #23405a; border-radius: 12px; "
            "border: 1px solid #d0dae8; font-weight: bold; }"
            "QPushButton:pressed { background: #cfd8e3; }"
        )

        grid = QGridLayout()
        grid.setSpacing(10)
        for i, digit in enumerate("123456789"):
            btn = QPushButton(digit)
            btn.setFixedSize(90, 64)
            btn.setFont(QFont("Arial", 24, QFont.Bold))
            btn.setStyleSheet(digit_style)
            btn.clicked.connect(lambda _, d=digit: self._digit_pressed(d))
            grid.addWidget(btn, i // 3, i % 3, Qt.AlignCenter)

        zero_btn = QPushButton("0")
        zero_btn.setFixedSize(90, 64)
        zero_btn.setFont(QFont("Arial", 24, QFont.Bold))
        zero_btn.setStyleSheet(digit_style)
        zero_btn.clicked.connect(lambda: self._digit_pressed("0"))
        grid.addWidget(zero_btn, 3, 1, Qt.AlignCenter)

        backspace_btn = QPushButton("\u232b")
        backspace_btn.setFixedSize(90, 64)
        backspace_btn.setFont(QFont("Arial", 22, QFont.Bold))
        backspace_btn.setStyleSheet(
            "QPushButton { background: #e67e22; color: white; border-radius: 12px; }"
            "QPushButton:pressed { background: #bf6516; }"
        )
        backspace_btn.clicked.connect(self._backspace)
        grid.addWidget(backspace_btn, 3, 2, Qt.AlignCenter)

        clear_btn = QPushButton("C")
        clear_btn.setFixedSize(90, 64)
        clear_btn.setFont(QFont("Arial", 22, QFont.Bold))
        clear_btn.setStyleSheet(
            "QPushButton { background: #c0392b; color: white; border-radius: 12px; }"
            "QPushButton:pressed { background: #922b21; }"
        )
        clear_btn.clicked.connect(self._clear)
        grid.addWidget(clear_btn, 3, 0, Qt.AlignCenter)

        vbox.addLayout(grid)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(48)
        cancel_btn.setFont(QFont("Arial", 15, QFont.Bold))
        cancel_btn.setStyleSheet(
            "QPushButton { background: #e0e0e0; color: #23405a; border-radius: 12px; }"
            "QPushButton:pressed { background: #bbb; }"
        )
        cancel_btn.clicked.connect(self.hide)
        btn_row.addWidget(cancel_btn, 1)

        self._unlock_btn = QPushButton("Unlock")
        self._unlock_btn.setFixedHeight(48)
        self._unlock_btn.setFont(QFont("Arial", 15, QFont.Bold))
        self._unlock_btn.setStyleSheet(
            "QPushButton { background: #2bb3a3; color: white; border-radius: 12px; }"
            "QPushButton:pressed { background: #1f8b83; }"
        )
        self._unlock_btn.clicked.connect(self._try_authenticate)
        btn_row.addWidget(self._unlock_btn, 1)

        vbox.addLayout(btn_row)

        main_layout.addWidget(container)

        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self.hide)

    # ------------------------------------------------------------------

    def show_overlay(self, *, title=None, submit_label=None, on_submit=None):
        """Show the PIN overlay.

        *title* / *submit_label* let callers reuse this for "Enter New PIN" flows.
        *on_submit* replaces the default authentication check — receives the entered
        PIN string and should return True to close the overlay or False to stay open.
        """
        self._pin = ""
        self._update_dots()
        self._error_label.setText("")
        self._custom_submit = on_submit
        self._title_label.setText(title or "Enter PIN")
        self._unlock_btn.setText(submit_label or "Unlock")
        if self.parent:
            self.setGeometry(self.parent.rect())
        self.setVisible(True)
        self.raise_()
        self._dismiss_timer.start(self._AUTO_DISMISS_MS)

    def hideEvent(self, event):
        self._dismiss_timer.stop()
        super().hideEvent(event)

    # ------------------------------------------------------------------

    def _digit_pressed(self, digit):
        if len(self._pin) >= self._MAX_PIN_LEN:
            return
        self._pin += digit
        self._update_dots()
        self._error_label.setText("")

    def _backspace(self):
        self._pin = self._pin[:-1]
        self._update_dots()
        self._error_label.setText("")

    def _clear(self):
        self._pin = ""
        self._update_dots()
        self._error_label.setText("")

    def _update_dots(self):
        self._dots_label.setText("\u25cf " * len(self._pin))

    # ------------------------------------------------------------------

    def _get_correct_pin(self):
        from device_config import load_device_config
        cfg = load_device_config()
        return cfg.get("settings_pin", "1234")

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Escape:
            self.hide()
        elif key == Qt.Key_Return or key == Qt.Key_Enter:
            self._try_authenticate()
        elif key == Qt.Key_Backspace:
            self._backspace()
        elif event.text().isdigit():
            self._digit_pressed(event.text())
        else:
            super().keyPressEvent(event)

    def _try_authenticate(self):
        cb = getattr(self, "_custom_submit", None)
        if cb is not None:
            if cb(self._pin):
                self._dismiss_timer.stop()
                self.hide()
            return
        if self._pin == self._get_correct_pin():
            self._dismiss_timer.stop()
            self.hide()
            self.authenticated.emit()
        else:
            self._error_label.setText("Incorrect PIN")
            self._pin = ""
            self._update_dots()

    def mousePressEvent(self, event):
        for child in self.children():
            if isinstance(child, QWidget) and child.geometry().contains(event.pos()):
                return
        self.hide()


class SettingsOverlay(QWidget):
    """Overlay for application settings including ESP32 connection."""

    printer_test_finished = pyqtSignal(object, object)
    printer_diag_finished = pyqtSignal(object, object)

    # Compact 5" / 800×480-friendly group box chrome
    _SETTINGS_GROUP_STYLE = (
        "QGroupBox { font-weight: bold; border: 1px solid #23405a; border-radius: 6px; "
        "margin-top: 4px; padding-top: 6px; } "
        "QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }"
    )
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: rgba(0,0,0,0.55);")
        self.setWindowFlags(Qt.Widget | Qt.FramelessWindowHint)
        self.setVisible(False)
        self.setGeometry(parent.rect())
        self.parent = parent
        self.printer_test_finished.connect(self._printer_test_finished)
        self.printer_diag_finished.connect(self._printer_diag_finished)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(0)

        # Fixed header: title + close always visible (no scrolling to exit)
        header = QWidget()
        header.setStyleSheet("background: white; border-top-left-radius: 14px; border-top-right-radius: 14px;")
        header_l = QHBoxLayout(header)
        header_l.setContentsMargins(12, 8, 10, 8)
        title = QLabel("Settings")
        title.setFont(QFont("Arial", 17, QFont.Bold))
        title.setStyleSheet("color: #23405a;")
        header_l.addWidget(title)
        header_l.addStretch()
        close_header = QPushButton("Close")
        close_header.setFont(QFont("Arial", 13, QFont.Bold))
        close_header.setMinimumHeight(48)
        close_header.setStyleSheet(
            "QPushButton { background: #95a5a6; color: white; border-radius: 8px; padding: 6px 16px; } "
            "QPushButton:hover { background: #7f8c8d; } QPushButton:pressed { background: #6c7b7d; }"
        )
        close_header.clicked.connect(lambda: self.setVisible(False))
        header_l.addWidget(close_header)
        root.addWidget(header)

        scroll_area = QScrollArea()
        self._settings_scroll = scroll_area
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: white;
                border-bottom-left-radius: 14px;
                border-bottom-right-radius: 14px;
            }
            QScrollBar:vertical {
                background: #e8ecf0;
                width: 20px;
                border-radius: 8px;
                margin: 4px 2px 4px 0;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: #8fa4b8;
                border-radius: 8px;
                min-height: 48px;
            }
            QScrollBar::handle:vertical:hover {
                background: #6d8499;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)
        try:
            QScroller.grabGesture(scroll_area.viewport(), QScroller.LeftMouseButtonGesture)
        except Exception:
            pass

        container = QWidget()
        container.setStyleSheet("background: white;")
        vbox = QVBoxLayout(container)
        vbox.setAlignment(Qt.AlignTop)
        vbox.setContentsMargins(12, 8, 12, 14)
        vbox.setSpacing(8)
        
        # Serial Connection Section
        connection_group = QGroupBox("ESP32")
        connection_group.setFont(QFont("Arial", 12, QFont.Bold))
        connection_group.setStyleSheet(self._SETTINGS_GROUP_STYLE)
        connection_layout = QVBoxLayout(connection_group)
        connection_layout.setSpacing(6)
        
        # Port selection
        port_layout = QHBoxLayout()
        port_lbl = QLabel("Port:")
        port_lbl.setFont(QFont("Arial", 14))
        port_layout.addWidget(port_lbl)
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(140)
        self.port_combo.setFont(QFont("Arial", 14))
        self.refresh_ports()
        port_layout.addWidget(self.port_combo, 1)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFont(QFont("Arial", 14))
        refresh_btn.setMinimumHeight(48)
        refresh_btn.clicked.connect(self.refresh_ports)
        port_layout.addWidget(refresh_btn)
        connection_layout.addLayout(port_layout)

        self.connect_button = QPushButton("Connect")
        self.connect_button.setMinimumHeight(48)
        self.connect_button.setFont(QFont("Arial", 14, QFont.Bold))
        self.connect_button.clicked.connect(self.toggle_connection)
        self.connect_button.setStyleSheet(
            "QPushButton { background: #2bb3a3; color: white; border-radius: 8px; padding: 6px 0; } "
            "QPushButton:hover { background: #249e90; } QPushButton:pressed { background: #1e857a; }"
        )
        connection_layout.addWidget(self.connect_button)

        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #666; font-size: 14px;")
        connection_layout.addWidget(self.status_label)
        
        vbox.addWidget(connection_group)

        wifi_group = QGroupBox("Wi-Fi")
        wifi_group.setFont(QFont("Arial", 12, QFont.Bold))
        wifi_group.setStyleSheet(self._SETTINGS_GROUP_STYLE)
        wifi_layout = QVBoxLayout(wifi_group)
        wifi_layout.setSpacing(6)
        self.wifi_status_label = QLabel("Loading…")
        self.wifi_status_label.setWordWrap(True)
        self.wifi_status_label.setStyleSheet("color: #666; font-size: 14px;")
        wifi_layout.addWidget(self.wifi_status_label)
        wifi_btn_row = QHBoxLayout()
        wifi_btn_row.setSpacing(6)
        refresh_wifi_btn = QPushButton("Refresh")
        refresh_wifi_btn.setFont(QFont("Arial", 14))
        refresh_wifi_btn.setMinimumHeight(48)
        refresh_wifi_btn.setStyleSheet(
            "QPushButton { background: #5dade2; color: white; border-radius: 6px; padding: 4px 8px; } "
            "QPushButton:hover { background: #3498db; } QPushButton:pressed { background: #2874a6; }"
        )
        refresh_wifi_btn.clicked.connect(self.update_wifi_status)
        wifi_btn_row.addWidget(refresh_wifi_btn, 1)
        retry_wifi_btn = QPushButton("Retry")
        retry_wifi_btn.setFont(QFont("Arial", 14))
        retry_wifi_btn.setMinimumHeight(48)
        retry_wifi_btn.setStyleSheet(
            "QPushButton { background: #1abc9c; color: white; border-radius: 6px; padding: 4px 8px; } "
            "QPushButton:hover { background: #17a589; } QPushButton:pressed { background: #148f77; }"
        )
        retry_wifi_btn.clicked.connect(self.retry_wifi_now)
        wifi_btn_row.addWidget(retry_wifi_btn, 1)
        wifi_layout.addLayout(wifi_btn_row)
        vbox.addWidget(wifi_group)

        self._wifi_refresh_timer = QTimer(self)
        self._wifi_refresh_timer.setInterval(8000)
        self._wifi_refresh_timer.timeout.connect(self.update_wifi_status)
        
        sync_group = QGroupBox("Database / Firebase")
        sync_group.setFont(QFont("Arial", 12, QFont.Bold))
        sync_group.setStyleSheet(self._SETTINGS_GROUP_STYLE)
        sync_layout = QVBoxLayout(sync_group)
        sync_layout.setSpacing(6)

        self.sync_status_label = QLabel("Checking sync status...")
        self.sync_status_label.setWordWrap(True)
        self.sync_status_label.setStyleSheet("color: #666; font-size: 14px;")
        sync_layout.addWidget(self.sync_status_label)

        btn_row_style = (
            "QPushButton { font-size: 14px; padding: 6px 6px; border-radius: 6px; min-height: 48px; }"
        )
        sync_grid = QGridLayout()
        sync_grid.setSpacing(6)

        force_sync_btn = QPushButton("Force sync")
        force_sync_btn.setStyleSheet(
            btn_row_style + "QPushButton { background: #3498db; color: white; } "
            "QPushButton:hover { background: #2980b9; } QPushButton:pressed { background: #21618c; }"
        )
        force_sync_btn.clicked.connect(self.force_sync)
        sync_grid.addWidget(force_sync_btn, 0, 0)

        firebase_check_btn = QPushButton("Check Firebase")
        firebase_check_btn.setStyleSheet(
            btn_row_style + "QPushButton { background: #1f8b83; color: white; } "
            "QPushButton:hover { background: #1a756f; } QPushButton:pressed { background: #15635e; }"
        )
        firebase_check_btn.clicked.connect(self.check_firebase_connection)
        sync_grid.addWidget(firebase_check_btn, 0, 1)

        firebase_reconnect_btn = QPushButton("Reconnect")
        firebase_reconnect_btn.setStyleSheet(
            btn_row_style + "QPushButton { background: #16a085; color: white; } "
            "QPushButton:hover { background: #138d75; } QPushButton:pressed { background: #117a65; }"
        )
        firebase_reconnect_btn.clicked.connect(self.reconnect_firebase)
        sync_grid.addWidget(firebase_reconnect_btn, 1, 0)

        check_updates_btn = QPushButton("Updates")
        check_updates_btn.setStyleSheet(
            btn_row_style + "QPushButton { background: #9b59b6; color: white; } "
            "QPushButton:hover { background: #8e44ad; } QPushButton:pressed { background: #7d3c98; }"
        )
        check_updates_btn.clicked.connect(self.check_for_updates)
        sync_grid.addWidget(check_updates_btn, 1, 1)

        sync_layout.addLayout(sync_grid)

        self.current_version_label = QLabel("Version: …")
        self.current_version_label.setStyleSheet("color: #666; font-size: 14px;")
        sync_layout.addWidget(self.current_version_label)

        vbox.addWidget(sync_group)

        classroom_group = QGroupBox("Classroom")
        classroom_group.setFont(QFont("Arial", 12, QFont.Bold))
        classroom_group.setStyleSheet(self._SETTINGS_GROUP_STYLE)
        classroom_layout = QVBoxLayout(classroom_group)
        classroom_layout.setSpacing(6)

        self.classroom_status_label = QLabel("")
        self.classroom_status_label.setWordWrap(True)
        self.classroom_status_label.setStyleSheet("color: #666; font-size: 14px;")
        classroom_layout.addWidget(self.classroom_status_label)

        # Stacked label + field (full width). QFormLayout side-by-side squeezes fields on 5" screens.
        lbl_style = "font-size: 12px; color: #23405a; font-weight: bold; margin-top: 2px;"
        input_style = (
            "QLineEdit {"
            " font-size: 15px;"
            " font-weight: bold;"
            " color: #23405a;"
            " padding: 8px 10px;"
            " border: 2px solid #2bb3a3;"
            " border-radius: 8px;"
            " background: #f8fbfd;"
            " min-height: 40px;"
            "}"
            "QLineEdit:focus {"
            " border-color: #1f8b83;"
            " background: #ffffff;"
            "}"
        )

        def _add_field_row(caption: str, line_edit: QLineEdit, placeholder: str):
            cap = QLabel(caption)
            cap.setStyleSheet(lbl_style)
            cap.setWordWrap(True)
            line_edit.setPlaceholderText(placeholder)
            line_edit.setStyleSheet(input_style)
            line_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            line_edit.setMinimumHeight(40)
            classroom_layout.addWidget(cap)
            classroom_layout.addWidget(line_edit)

        self.classroom_id_input = QLineEdit()
        _add_field_row("Classroom ID *", self.classroom_id_input, "e.g. 201, Library, Lab-A")

        self.classroom_label_input = QLineEdit()
        _add_field_row("Display name (optional)", self.classroom_label_input, "Shown on device / passes")

        self.teacher_name_input = QLineEdit()
        _add_field_row("Teacher", self.teacher_name_input, "Teacher for this device")

        classroom_buttons = QHBoxLayout()
        classroom_buttons.setSpacing(8)

        button_style_template = (
            "QPushButton {{ background: {}; color: white; border-radius: 8px; padding: 8px 12px; font-size: 13px; min-height: 40px; }}"
            "QPushButton:hover {{ background: {}; }}"
            "QPushButton:pressed {{ background: {}; }}"
        )
        save_classroom_btn = QPushButton("Save")
        save_classroom_btn.setStyleSheet(button_style_template.format("#2bb3a3", "#249e90", "#1e857a"))
        save_classroom_btn.clicked.connect(self.save_classroom_settings)
        classroom_buttons.addWidget(save_classroom_btn, 1)

        reset_classroom_btn = QPushButton("Reset")
        reset_classroom_btn.setStyleSheet(
            "QPushButton { background: #e0e0e0; color: #23405a; border-radius: 8px; padding: 8px 12px; font-size: 13px; min-height: 40px; } "
            "QPushButton:hover { background: #cccccc; } "
            "QPushButton:pressed { background: #bbbbbb; }"
        )
        reset_classroom_btn.clicked.connect(self.populate_classroom_fields)
        classroom_buttons.addWidget(reset_classroom_btn, 1)

        classroom_layout.addLayout(classroom_buttons)
        vbox.addWidget(classroom_group)

        add_btn = QPushButton("Add student")
        add_btn.setFont(QFont("Arial", 14, QFont.Bold))
        add_btn.setMinimumHeight(48)
        add_btn.setStyleSheet(
            "QPushButton { background: #2bb3a3; color: white; border-radius: 8px; padding: 6px 0; } "
            "QPushButton:hover { background: #249e90; } QPushButton:pressed { background: #1e857a; }"
        )
        add_btn.clicked.connect(self.show_add_student_dialog)
        vbox.addWidget(add_btn)

        student_mgmt_group = QGroupBox("Breaks / visits")
        student_mgmt_group.setFont(QFont("Arial", 12, QFont.Bold))
        student_mgmt_group.setStyleSheet(self._SETTINGS_GROUP_STYLE)
        student_mgmt_layout = QVBoxLayout(student_mgmt_group)
        student_mgmt_layout.setSpacing(4)

        end_breaks_btn = QPushButton("End all active breaks")
        end_breaks_btn.setMinimumHeight(48)
        end_breaks_btn.setStyleSheet(
            "QPushButton { background: #e67e22; color: white; border-radius: 6px; padding: 6px 8px; font-size: 14px; } "
            "QPushButton:hover { background: #d35400; } QPushButton:pressed { background: #a04000; }"
        )
        end_breaks_btn.clicked.connect(self.end_all_active_breaks)
        student_mgmt_layout.addWidget(end_breaks_btn)

        self.active_breaks_label = QLabel("Checking for active breaks...")
        self.active_breaks_label.setWordWrap(True)
        self.active_breaks_label.setStyleSheet("color: #666; font-size: 14px;")
        student_mgmt_layout.addWidget(self.active_breaks_label)

        vbox.addWidget(student_mgmt_group)

        printer_group = QGroupBox("Printer")
        printer_group.setFont(QFont("Arial", 12, QFont.Bold))
        printer_group.setStyleSheet(self._SETTINGS_GROUP_STYLE)
        printer_layout = QVBoxLayout(printer_group)
        printer_layout.setSpacing(6)
        usb_row = QHBoxLayout()
        usb_lbl = QLabel("USB:")
        usb_lbl.setFont(QFont("Arial", 14))
        usb_row.addWidget(usb_lbl)
        self.printer_combo = QComboBox()
        self.printer_combo.setMinimumHeight(48)
        self.printer_combo.setFont(QFont("Arial", 13))
        usb_row.addWidget(self.printer_combo, 1)
        refresh_printer_btn = QPushButton("Refresh")
        refresh_printer_btn.setFont(QFont("Arial", 14))
        refresh_printer_btn.setMinimumHeight(48)
        refresh_printer_btn.clicked.connect(self.refresh_printer_devices)
        usb_row.addWidget(refresh_printer_btn)
        printer_layout.addLayout(usb_row)
        self.printer_status_label = QLabel("Select the printer USB device, then Test printer.")
        self.printer_status_label.setWordWrap(True)
        self.printer_status_label.setStyleSheet("color: #666; font-size: 14px;")
        printer_layout.addWidget(self.printer_status_label)
        diagnose_printer_btn = QPushButton("Diagnose printer")
        self.diagnose_printer_btn = diagnose_printer_btn
        diagnose_printer_btn.setFont(QFont("Arial", 14, QFont.Bold))
        diagnose_printer_btn.setMinimumHeight(48)
        diagnose_printer_btn.setStyleSheet(
            "QPushButton { background: #34495e; color: white; border-radius: 6px; padding: 8px 4px; } "
            "QPushButton:hover { background: #2c3e50; } QPushButton:pressed { background: #1b2631; }"
        )
        diagnose_printer_btn.clicked.connect(self.run_printer_diagnostics)
        printer_layout.addWidget(diagnose_printer_btn)
        vbox.addWidget(printer_group)

        app_control_group = QGroupBox("App")
        app_control_group.setFont(QFont("Arial", 12, QFont.Bold))
        app_control_group.setStyleSheet(self._SETTINGS_GROUP_STYLE)
        app_grid = QGridLayout()
        app_grid.setSpacing(6)

        ac_style = (
            "QPushButton { font-size: 14px; font-weight: bold; padding: 8px 4px; border-radius: 6px; min-height: 48px; }"
        )
        restart_btn = QPushButton("Restart")
        restart_btn.setStyleSheet(
            ac_style + "QPushButton { background: #f39c12; color: white; } "
            "QPushButton:hover { background: #e67e22; } QPushButton:pressed { background: #d35400; }"
        )
        restart_btn.clicked.connect(self.restart_application)
        app_grid.addWidget(restart_btn, 0, 0)

        test_printer_btn = QPushButton("Test printer")
        self.test_printer_btn = test_printer_btn
        test_printer_btn.setStyleSheet(
            ac_style + "QPushButton { background: #3498db; color: white; } "
            "QPushButton:hover { background: #2980b9; } QPushButton:pressed { background: #21618c; }"
        )
        test_printer_btn.clicked.connect(self.run_printer_test)
        app_grid.addWidget(test_printer_btn, 0, 1)

        reprint_btn = QPushButton("Reprint pass")
        reprint_btn.setStyleSheet(
            ac_style + "QPushButton { background: #8e44ad; color: white; } "
            "QPushButton:hover { background: #7d3c98; } QPushButton:pressed { background: #6c3483; }"
        )
        reprint_btn.clicked.connect(self.reprint_last_pass)
        app_grid.addWidget(reprint_btn, 1, 0)

        change_pin_btn = QPushButton("Change PIN")
        change_pin_btn.setStyleSheet(
            ac_style + "QPushButton { background: #1abc9c; color: white; } "
            "QPushButton:hover { background: #16a085; } QPushButton:pressed { background: #0e6655; }"
        )
        change_pin_btn.clicked.connect(self.change_settings_pin)
        app_grid.addWidget(change_pin_btn, 1, 1)

        install_printer_btn = QPushButton("Install printer")
        install_printer_btn.setStyleSheet(
            ac_style + "QPushButton { background: #27ae60; color: white; } "
            "QPushButton:hover { background: #229954; } QPushButton:pressed { background: #1e8449; }"
        )
        install_printer_btn.clicked.connect(self.install_printer_rule)
        app_grid.addWidget(install_printer_btn, 2, 0)

        quit_btn = QPushButton("Quit")
        quit_btn.setStyleSheet(
            ac_style + "QPushButton { background: #e74c3c; color: white; } "
            "QPushButton:hover { background: #c0392b; } QPushButton:pressed { background: #a93226; }"
        )
        quit_btn.clicked.connect(self.quit_application)
        app_grid.addWidget(quit_btn, 2, 1)

        app_outer = QVBoxLayout(app_control_group)
        app_outer.setSpacing(6)
        app_outer.addLayout(app_grid)

        vbox.addWidget(app_control_group)

        scroll_area.setWidget(container)
        root.addWidget(scroll_area, 1)
        
        # Update connection status
        self.update_connection_status()
        
        # Update active breaks status
        self.update_active_breaks_status()
        self.keyboard = OnScreenKeyboard(self)
        self._keyboard_fields = {}
        self._register_keyboard_field(self.classroom_id_input, "Classroom ID")
        self._register_keyboard_field(self.classroom_label_input, "Display Name")
        self._register_keyboard_field(self.teacher_name_input, "Teacher")
        self.populate_classroom_fields()
        self.refresh_printer_devices()

    def refresh_ports(self):
        """Refresh the list of available serial ports"""
        self.port_combo.clear()
        ports = [port.device for port in serial.tools.list_ports.comports() 
                if not port.device.endswith('debugconsole')]
        if not ports:
            self.status_label.setText("Status: No serial ports found")
        self.port_combo.addItems(ports)

    def refresh_printer_devices(self):
        """Rescan USB / serial devices for the printer dropdown."""
        previous = self.printer_combo.currentData()
        printer = getattr(self.parent, "printer", None)
        if (not previous or not previous.get("devfile")) and printer and getattr(printer, "devfile", None):
            previous = {
                "kind": getattr(printer, "backend_kind", "serial") or "serial",
                "devfile": printer.devfile,
                "vendor_id": getattr(printer, "vendor_id", None),
                "product_id": getattr(printer, "product_id", None),
                "bus": getattr(printer, "bus", None),
                "address": getattr(printer, "address", None),
            }
        self.printer_combo.clear()
        devices = list_usb_devices()
        if not devices:
            self.printer_combo.addItem("No USB/serial devices found — tap Refresh", None)
            self.printer_status_label.setText(
                "No ttyACM/ttyUSB printer found. Power the mini printer ON, wait for its LED, "
                "unplug/replug USB, then Refresh. ttyAMA0 is the Pi itself — ignore it."
            )
            return

        preferred_idx = 0
        for i, dev in enumerate(devices):
            self.printer_combo.addItem(dev["label"], dev)
            if previous:
                same_serial = (
                    previous.get("devfile")
                    and previous.get("devfile") == dev.get("devfile")
                )
                same_usb = (
                    previous.get("vendor_id") == dev.get("vendor_id")
                    and previous.get("product_id") == dev.get("product_id")
                    and previous.get("bus") == dev.get("bus")
                    and previous.get("address") == dev.get("address")
                    and previous.get("kind", "usb") == dev.get("kind", "usb")
                    and not previous.get("devfile")
                )
                if same_serial or same_usb:
                    preferred_idx = i
            elif not previous and dev.get("likely_printer"):
                preferred_idx = i
        self.printer_combo.setCurrentIndex(preferred_idx)
        current = self.printer_combo.currentData() or {}
        self.printer_status_label.setText(
            f"{len(devices)} device(s). Selected: {current.get('label', 'none')}. "
            "Portable minis usually appear as ttyACM0 / ttyUSB0 — pick that, then Test."
        )

    def _apply_selected_printer(self, connect=False):
        """Point the ThermalPrinter at the dropdown selection and save it."""
        from device_config import update_device_config

        printer = getattr(self.parent, "printer", None)
        data = self.printer_combo.currentData() if hasattr(self, "printer_combo") else None
        if printer is None or not data:
            return
        vid = data.get("vendor_id") or 0
        pid = data.get("product_id") or 0
        bus = data.get("bus")
        addr = data.get("address")
        kind = data.get("kind") or "auto"
        devfile = data.get("devfile") or ""
        printer.vendor_id = vid
        printer.product_id = pid
        printer.bus = bus
        printer.address = addr
        printer.backend_kind = kind
        printer.devfile = devfile or None
        update_device_config(
            printer_vendor_id=f"0x{int(vid):04x}",
            printer_product_id=f"0x{int(pid):04x}",
            printer_bus="" if bus is None else str(bus),
            printer_address="" if addr is None else str(addr),
            printer_backend=kind,
            printer_devfile=devfile,
            printer_baudrate=str(getattr(printer, "baudrate", "") or ""),
        )
        if connect:
            printer.reconnect()

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

    def _register_keyboard_field(self, line_edit, label):
        """Attach the on-screen keyboard handler to a line edit."""
        if not hasattr(self, '_keyboard_fields'):
            self._keyboard_fields = {}
        self._keyboard_fields[line_edit] = label
        line_edit.installEventFilter(self)

    def eventFilter(self, obj, event):
        """Intercept direct taps on text fields to show the on-screen keyboard.

        Only MouseButtonPress — not FocusIn. Otherwise tapping another button
        (e.g. Updates) steals focus into Classroom ID and opens the keyboard
        instead of showing the update dialog.
        """
        if hasattr(self, '_keyboard_fields') and obj in self._keyboard_fields:
            if event.type() == QEvent.MouseButtonPress:
                if hasattr(self, 'keyboard') and self.keyboard:
                    self.keyboard.show_for(obj, self._keyboard_fields[obj])
        return super().eventFilter(obj, event)

    def populate_classroom_fields(self):
        """Load classroom settings into the form fields."""
        config = getattr(self.parent, 'device_config', {}) or {}
        classroom_id = config.get('classroom_id', '') or ''
        classroom_label = config.get('classroom_label', '') or ''
        teacher_name = config.get('teacher_name', '') or ''

        self.classroom_id_input.setText(classroom_id)
        self.classroom_label_input.setText(classroom_label)
        self.teacher_name_input.setText(teacher_name)

        if classroom_id:
            display_label = classroom_label or f"Classroom {classroom_id}"
            teacher_display = teacher_name or "Teacher not set"
            status = f"Current: {display_label} • {teacher_display}"
        else:
            status = "Current: Not configured"
        self.classroom_status_label.setText(status)

    def save_classroom_settings(self):
        """Persist classroom settings through the parent GUI."""
        classroom_id = self.classroom_id_input.text().strip()
        classroom_label = self.classroom_label_input.text().strip()
        teacher_name = self.teacher_name_input.text().strip()

        if not classroom_id:
            QMessageBox.warning(self, "Missing Classroom ID", "Please enter a classroom ID or number for this device.")
            self.classroom_id_input.setFocus()
            return

        try:
            self.parent.save_classroom_settings(classroom_id, classroom_label, teacher_name)
            self.populate_classroom_fields()
            QMessageBox.information(self, "Saved", "Classroom settings updated successfully.")
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", f"Unable to save classroom settings:\n{exc}")
    
    def force_sync(self):
        """Force an immediate sync to Firebase Firestore"""
        try:
            self.parent.db.force_sync()
            self.update_sync_status()
            QMessageBox.information(self, "Sync Complete", "Data has been synced to Firebase Firestore successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Sync Error", f"Error during sync: {str(e)}")

    def check_firebase_connection(self):
        """Ping internet + Firestore (OnlineFirstDatabase)."""
        db = self.parent.db
        if not hasattr(db, 'check_firebase_connection'):
            QMessageBox.information(
                self, "Not available",
                "This database mode does not support Firebase connection checks."
            )
            return
        try:
            ok, msg = db.check_firebase_connection()
            self.update_sync_status()
            if ok:
                QMessageBox.information(self, "Firebase", msg)
            else:
                QMessageBox.warning(self, "Firebase", msg)
        except Exception as e:
            QMessageBox.critical(self, "Firebase", str(e))

    def reconnect_firebase(self):
        """(Re)initialize Firebase client when offline or connection is stale."""
        db = self.parent.db
        if not hasattr(db, 'reconnect_firebase'):
            QMessageBox.information(
                self, "Not available",
                "This database mode does not support Firebase reconnect."
            )
            return
        try:
            ok, msg = db.reconnect_firebase()
            self.update_sync_status()
            if ok:
                QMessageBox.information(self, "Firebase", msg)
            else:
                QMessageBox.warning(self, "Firebase", msg)
        except Exception as e:
            QMessageBox.critical(self, "Firebase", str(e))
    
    def check_for_updates(self):
        """Check for application updates"""
        try:
            # Don't leave the classroom keyboard covering update dialogs
            if hasattr(self, "keyboard") and self.keyboard:
                self.keyboard.hide()
            focused = QApplication.focusWidget()
            if focused is not None:
                focused.clearFocus()

            if hasattr(self.parent, 'update_manager') and self.parent.update_manager:
                sender = self.sender()
                if sender:
                    sender.setEnabled(False)
                    sender.setText("Checking…")

                self.parent.update_manager.check_for_updates(show_message=True)
                QTimer.singleShot(3000, lambda: self.restore_update_button(sender))
            else:
                QMessageBox.warning(self, "Update Check", "Update manager is not available.")
        except Exception as e:
            QMessageBox.critical(self, "Update Check Error", f"Error checking for updates: {str(e)}")

    def restore_update_button(self, button):
        """Restore the update button to its original state"""
        if button:
            button.setEnabled(True)
            button.setText("Updates")
    
    def update_version_display(self):
        """Update the current version display"""
        try:
            if hasattr(self.parent, 'update_manager') and self.parent.update_manager:
                version = self.parent.update_manager.current_version
                self.current_version_label.setText(f"App version: {version}")
            else:
                self.current_version_label.setText("App version: unknown")
        except Exception as e:
            self.current_version_label.setText("App version: error")
    
    def update_sync_status(self):
        """Update the sync status display"""
        try:
            status = self.parent.db.get_sync_status()
            
            last_sync_text = "Never"
            if status['last_sync']:
                last_sync_text = status['last_sync'].strftime("%H:%M:%S")
            
            fs = "Connected" if status["firebase_connected"] else "Disconnected"
            status_text = (
                f"Firestore: {fs}\n"
                f"Last sync: {last_sync_text} · Pending: {status['pending_changes']}\n"
                f"Check interval: {status['sync_interval_minutes']} min"
            )

            self.sync_status_label.setText(status_text)

            if status["firebase_connected"]:
                color = "#27ae60" if status["pending_changes"] == 0 else "#f39c12"
            else:
                color = "#e74c3c"

            self.sync_status_label.setStyleSheet(f"color: {color}; font-size: 14px; margin: 2px 0;")

        except Exception as e:
            self.sync_status_label.setText(f"Sync status error: {str(e)}")
            self.sync_status_label.setStyleSheet("color: #e74c3c; font-size: 14px; margin: 2px 0;")

    def update_wifi_status(self):
        """Show Wi-Fi device / SSID / signal (nmcli on Raspberry Pi OS)."""
        try:
            info = get_wifi_info()
        except Exception as e:
            self.wifi_status_label.setText(f"Could not read Wi-Fi status: {e}")
            self.wifi_status_label.setStyleSheet("color: #e74c3c; font-size: 14px; margin: 5px 0;")
            return

        dev = info.get("wifi_device") or "—"
        nm = "available" if info.get("nmcli_available") else "not found"
        lines = [f"nmcli: {nm} · interface: {dev}"]

        if info.get("connected"):
            ssid = info.get("ssid") or "?"
            sig = info.get("signal_percent")
            sig_txt = f"{sig}%" if sig is not None else "n/a"
            lines.append(f"Connected · SSID: {ssid} · signal: {sig_txt}")
            color = "#27ae60"
        else:
            st = info.get("state") or "unknown"
            lines.append(f"Not connected · state: {st}")
            color = "#e67e22"

        det = (info.get("detail") or "").strip()
        if det:
            lines.append(det)

        self.wifi_status_label.setText("\n".join(lines))
        self.wifi_status_label.setStyleSheet(f"color: {color}; font-size: 14px; margin: 5px 0;")

    def retry_wifi_now(self):
        """Ask NetworkManager to turn Wi-Fi on and reconnect the interface."""
        try:
            ok, log = try_wifi_reconnect()
            print(f"[SETTINGS] Wi-Fi retry:\n{log}")
            self.update_wifi_status()
            if hasattr(self.parent, "db") and hasattr(self.parent.db, "check_internet_connection"):
                if self.parent.db.check_internet_connection(timeout=5):
                    QMessageBox.information(
                        self,
                        "Wi-Fi",
                        "Internet connectivity detected after retry.\n"
                        "Database sync should follow within a few seconds.",
                    )
                    self.update_sync_status()
                    return
            QMessageBox.information(
                self,
                "Wi-Fi retry",
                "Commands completed. Check the status lines above.\n\n"
                "If nothing improves, confirm NetworkManager is running and this user "
                "may run nmcli (or configure Polkit). Details were printed to the console.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Wi-Fi", str(e))
    
    def update_active_breaks_status(self):
        """Update the active breaks status display"""
        try:
            outings = self.get_active_breaks_info()
            
            if not outings:
                self.active_breaks_label.setText("No active breaks or visits")
                self.active_breaks_label.setStyleSheet("color: #27ae60; font-size: 14px; margin: 5px 0;")
            else:
                self.active_breaks_label.setText(f"Active: {len(outings)} student(s) out")
                self.active_breaks_label.setStyleSheet("color: #e67e22; font-size: 14px; margin: 5px 0;")
                
        except Exception as e:
            self.active_breaks_label.setText(f"Error checking active breaks: {str(e)}")
            self.active_breaks_label.setStyleSheet("color: #e74c3c; font-size: 14px; margin: 5px 0;")
    
    def get_active_breaks_info(self):
        """Get active outings via OnlineFirstDatabase (uses snapshot listeners when online -- zero Firestore reads)."""
        try:
            return self.parent.db.get_active_outings()
        except Exception as e:
            print(f"Error getting active breaks info: {e}")
            return []
    
    def end_all_active_breaks(self):
        """End all active bathroom breaks, nurse visits, and water visits"""
        try:
            outings = self.get_active_breaks_info()

            if not outings:
                QMessageBox.information(self, "No Active Breaks", "There are currently no active bathroom breaks, nurse visits, or water visits.")
                return

            type_labels = {"Bathroom": "bathroom break", "Nurse": "nurse visit", "Water": "water visit"}
            break_list = [f"• {o['student_name']} ({type_labels.get(o['type'], o['type'])})" for o in outings]
            break_text = "\n".join(break_list)

            reply = QMessageBox.question(
                self,
                "End Active Breaks",
                f"Are you sure you want to end all active breaks and visits?\n\n{break_text}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )

            if reply == QMessageBox.Yes:
                ended_count = 0
                errors = []

                for outing in outings:
                    uid = outing.get("student_uid", "")
                    name = outing["student_name"]
                    otype = outing["type"]
                    try:
                        if otype == "Bathroom":
                            success, message = self.parent.db.end_bathroom_break(uid)
                        elif otype == "Nurse":
                            success, message = self.parent.db.end_nurse_visit(nfc_uid=uid)
                        elif otype == "Water":
                            success, message = self.parent.db.end_water_visit(nfc_uid=uid)
                        else:
                            success, message = False, f"Unknown type: {otype}"
                        if success:
                            ended_count += 1
                        else:
                            errors.append(f"{name} ({otype}): {message}")
                    except Exception as e:
                        error_msg = f"{name} ({otype}): {e}"
                        print(f"Error ending break for {error_msg}")
                        errors.append(error_msg)

                self.update_active_breaks_status()
                self.parent.update_gpio_led_status()

                if errors:
                    error_text = "\n".join(errors[:5])
                    if len(errors) > 5:
                        error_text += f"\n... and {len(errors) - 5} more errors"
                    QMessageBox.warning(
                        self,
                        "Breaks Ended with Errors",
                        f"Successfully ended {ended_count} active break(s).\n\nErrors:\n{error_text}",
                    )
                else:
                    QMessageBox.information(self, "Breaks Ended", f"Successfully ended {ended_count} active break(s).")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error ending active breaks: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def run_printer_test(self):
        """Send a short test print and show whether the thermal printer responded."""
        printer = getattr(self.parent, "printer", None)
        if printer is None:
            QMessageBox.warning(
                self,
                "Printer Test",
                "Printer is not available in this build.",
            )
            return
        if getattr(self, "_printer_test_busy", False):
            return

        self._printer_test_busy = True
        if hasattr(self, "test_printer_btn"):
            self.test_printer_btn.setEnabled(False)
            self.test_printer_btn.setText("Testing…")

        self._apply_selected_printer(connect=False)

        def work():
            err = None
            ok = False
            try:
                from printer import ESCPOS_AVAILABLE, ensure_printer_packages
                if not ESCPOS_AVAILABLE:
                    if hasattr(self, "test_printer_btn"):
                        # status text via finished handler; keep console trail
                        print("[PRINTER] python-escpos missing — installing…")
                    pkg_ok, pkg_msg = ensure_printer_packages()
                    if not pkg_ok:
                        self.printer_test_finished.emit(False, f"python-escpos install failed:\n{pkg_msg}")
                        return
                ok = printer.test_print()
                if not ok:
                    err = getattr(printer, "last_error", None) or "Could not connect or print."
            except Exception as e:
                err = e
            self.printer_test_finished.emit(ok, err)

        threading.Thread(target=work, daemon=True).start()

    def _printer_test_finished(self, ok, err):
        self._printer_test_busy = False
        if hasattr(self, "test_printer_btn"):
            self.test_printer_btn.setEnabled(True)
            self.test_printer_btn.setText("Test printer")
        if err is not None:
            QMessageBox.critical(self, "Printer Test", f"Error: {err}")
            return
        if ok:
            QMessageBox.information(
                self,
                "Printer Test",
                "Test page was sent. Check the printer for output.",
            )
        else:
            detail = err or "Could not connect or print."
            QMessageBox.warning(
                self,
                "Printer Test",
                f"{detail}\n\n"
                "Pick the serial entry marked ← try this (often ttyUSB0 / CH340 / CP210x), "
                "not necessarily 0416:5011. Power the printer ON first, then Refresh and Test again.",
            )

    def run_printer_diagnostics(self):
        """Run printer path checks and show the report on-screen (no keyboard needed)."""
        if getattr(self, "_printer_diag_busy", False):
            return

        self._printer_diag_busy = True
        if hasattr(self, "diagnose_printer_btn"):
            self.diagnose_printer_btn.setEnabled(False)
            self.diagnose_printer_btn.setText("Diagnosing…")
        if hasattr(self, "printer_status_label"):
            self.printer_status_label.setText("Running printer diagnostics… this can take ~20 seconds.")

        def work():
            try:
                from diagnose_printer import run_diagnostics
                report, results = run_diagnostics()
                self.printer_diag_finished.emit(report, results)
            except Exception as e:
                self.printer_diag_finished.emit(None, e)

        threading.Thread(target=work, daemon=True).start()

    def _printer_diag_finished(self, report, extra):
        # Reused as a general UI-thread callback for printer background work
        if report == "__install__":
            self._handle_printer_install_finished(extra)
            return

        self._printer_diag_busy = False
        if hasattr(self, "diagnose_printer_btn"):
            self.diagnose_printer_btn.setEnabled(True)
            self.diagnose_printer_btn.setText("Diagnose printer")

        if report is None:
            if hasattr(self, "printer_status_label"):
                self.printer_status_label.setText(f"Diagnostics failed: {extra}")
            QMessageBox.critical(self, "Printer Diagnose", f"Diagnostics failed:\n{extra}")
            return

        results = extra if isinstance(extra, dict) else {}
        works = [
            name for name, ok in results.items()
            if ok and name in ("/dev/usb/lp*", "serial", "pyusb bulk")
        ]
        if hasattr(self, "printer_status_label"):
            if works:
                self.printer_status_label.setText("Diagnostics: " + ", ".join(works) + " WORKS.")
            else:
                self.printer_status_label.setText("Diagnostics: no write path succeeded. See the report.")

        # Auto-bind the working serial port so Test printer / hall passes use it
        # (portable printers often need ttyACM0 / ttyUSB0, not raw pyusb).
        if results.get("serial") and results.get("serial_devfile"):
            self._apply_serial_printer(
                results["serial_devfile"],
                baud=results.get("serial_baud") or 9600,
            )
            if hasattr(self, "printer_status_label"):
                self.printer_status_label.setText(
                    f"Using serial {results['serial_devfile']} "
                    f"@ {results.get('serial_baud') or 9600}. Tap Test printer to confirm."
                )
            self.refresh_printer_devices()

        saved = self._save_printer_diag_report(report)
        if saved:
            report = report.rstrip() + f"\n\nReport also saved to:\n{saved}\n"
        self._show_printer_diag_dialog(report)

    def _apply_serial_printer(self, devfile, baud=9600):
        """Configure ThermalPrinter for a known-good serial path and persist it."""
        from device_config import update_device_config

        printer = getattr(self.parent, "printer", None)
        if printer is None or not devfile:
            return
        printer.backend_kind = "serial"
        printer.devfile = devfile
        printer.baudrate = int(baud) if baud else 9600
        printer.bus = None
        printer.address = None
        update_device_config(
            printer_backend="serial",
            printer_devfile=devfile,
            printer_baudrate=str(int(baud) if baud else 9600),
            printer_bus="",
            printer_address="",
        )

    def _save_printer_diag_report(self, report):
        here = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(here, "..", "printer_diag.txt"),
            os.path.join(here, "printer_diag.txt"),
        ]
        for path in candidates:
            path = os.path.normpath(path)
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(report)
                return path
            except Exception:
                continue
        return None

    def _show_printer_diag_dialog(self, report):
        dlg = QDialog(self)
        dlg.setWindowTitle("Printer diagnostics")
        dlg.setModal(True)
        parent = self.parent if isinstance(self.parent, QWidget) else self
        if parent is not None:
            geo = parent.geometry()
            dlg.resize(max(360, geo.width() - 24), max(280, geo.height() - 24))
        else:
            dlg.resize(760, 440)
        dlg.setStyleSheet("QDialog { background: #ffffff; color: #23405a; }")

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        hint = QLabel("Scroll the report, then tap Close. A successful path will also print a short test slip.")
        hint.setWordWrap(True)
        hint.setFont(QFont("Arial", 13))
        hint.setStyleSheet("color: #23405a;")
        layout.addWidget(hint)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(report)
        text.setFont(QFont("Monospace", 11))
        text.setStyleSheet(
            "QTextEdit { background: #f4f6f8; color: #1a1a1a; border: 1px solid #c5d0da; "
            "border-radius: 6px; padding: 8px; }"
        )
        QScroller.grabGesture(text.viewport(), QScroller.LeftMouseButtonGesture)
        layout.addWidget(text, 1)

        close_btn = QPushButton("Close")
        close_btn.setMinimumHeight(52)
        close_btn.setFont(QFont("Arial", 16, QFont.Bold))
        close_btn.setStyleSheet(
            "QPushButton { background: #2bb3a3; color: white; border: none; border-radius: 8px; } "
            "QPushButton:pressed { background: #1e857a; }"
        )
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(close_btn)

        dlg.exec_()

    def _printer_setup_script_path(self):
        """Locate install_printer.sh in OTA (main/setup) or repo-root (setup/) layouts."""
        here = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(here, "setup", "install_printer.sh"),
            os.path.join(here, "install_printer.sh"),
            os.path.join(here, "..", "setup", "install_printer.sh"),
        ]
        for path in candidates:
            path = os.path.normpath(path)
            if os.path.isfile(path):
                return path
        return os.path.normpath(candidates[0])

    def install_printer_rule(self):
        """Install printer Python packages + udev rule so the printer works without root."""
        if getattr(self, "_printer_install_busy", False):
            return
        self._printer_install_busy = True

        def work():
            messages = []
            try:
                from printer import ensure_printer_packages
                ok, msg = ensure_printer_packages()
                messages.append(("packages", ok, msg))
            except Exception as e:
                messages.append(("packages", False, str(e)))

            script = self._printer_setup_script_path()
            if not os.path.isfile(script):
                messages.append(("udev", False, f"Setup script not found:\n{script}"))
            else:
                try:
                    result = subprocess.run(
                        ["sudo", "bash", script],
                        capture_output=True, text=True, timeout=180,
                    )
                    detail = (result.stdout or result.stderr or "").strip()
                    messages.append(("udev", result.returncode == 0, detail or f"exit {result.returncode}"))
                except subprocess.TimeoutExpired:
                    messages.append(("udev", False, "The install script timed out."))
                except Exception as e:
                    messages.append(("udev", False, str(e)))

            # marshal back to UI thread via existing pattern
            self.printer_diag_finished.emit("__install__", messages)

        if hasattr(self, "printer_status_label"):
            self.printer_status_label.setText("Installing printer packages (python-escpos)…")
        threading.Thread(target=work, daemon=True).start()

    def _handle_printer_install_finished(self, messages):
        self._printer_install_busy = False
        lines = []
        all_ok = True
        for name, ok, msg in messages:
            all_ok = all_ok and ok
            lines.append(f"{name}: {'OK' if ok else 'FAILED'}\n{msg}")
        text = "\n\n".join(lines)
        if hasattr(self, "printer_status_label"):
            self.printer_status_label.setText(
                "Printer install finished." if all_ok else "Printer install had errors — see message."
            )
        if all_ok:
            QMessageBox.information(
                self,
                "Install Printer",
                "Printer packages installed.\n\n"
                "1. Power the mini printer ON\n"
                "2. Unplug and re-plug the USB cable\n"
                "3. Tap Refresh — look for ttyACM0 or ttyUSB0 (not ttyAMA0)\n"
                "4. Tap Test printer\n\n"
                f"{text}",
            )
            self.refresh_printer_devices()
        else:
            QMessageBox.warning(self, "Install Printer", text)

    def reprint_last_pass(self):
        """Reprint the most recently printed hall pass."""
        printer = getattr(self.parent, "printer", None)
        if printer is None:
            QMessageBox.warning(self, "Reprint", "Printer is not available in this build.")
            return
        result, msg = printer.reprint_last_pass()
        if msg:
            QMessageBox.information(self, "Reprint", msg)
        elif result:
            QMessageBox.information(self, "Reprint", "Last hall pass reprinted successfully.")
        else:
            QMessageBox.warning(self, "Reprint", "Failed to reprint. Check the printer connection.")

    def change_settings_pin(self):
        """Two-step flow: enter new PIN, confirm it, then persist."""
        from device_config import update_device_config

        self._pin_change_overlay = PasswordOverlay(self)

        def _step_enter(pin):
            if len(pin) < 4:
                self._pin_change_overlay._error_label.setText("PIN must be at least 4 digits")
                self._pin_change_overlay._pin = ""
                self._pin_change_overlay._update_dots()
                return False
            self._pending_new_pin = pin
            self._pin_change_overlay.show_overlay(
                title="Confirm New PIN",
                submit_label="Confirm",
                on_submit=_step_confirm,
            )
            return False

        def _step_confirm(pin):
            if pin == self._pending_new_pin:
                update_device_config(settings_pin=pin)
                QMessageBox.information(self, "PIN Changed", "Settings PIN has been updated.")
                return True
            self._pin_change_overlay._error_label.setText("PINs did not match — try again")
            self._pin_change_overlay._pin = ""
            self._pin_change_overlay._update_dots()
            return False

        self._pin_change_overlay.show_overlay(
            title="Enter New PIN",
            submit_label="Set PIN",
            on_submit=_step_enter,
        )

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
        self.update_wifi_status()
        self.update_sync_status()
        self.update_active_breaks_status()
        self.update_version_display()
        if hasattr(self, "_wifi_refresh_timer"):
            self._wifi_refresh_timer.start()

    def hideEvent(self, event):
        if hasattr(self, "_wifi_refresh_timer"):
            self._wifi_refresh_timer.stop()
        if hasattr(self, 'keyboard') and self.keyboard:
            self.keyboard.hide()
        super().hideEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # self.parent is the main window (see __init__); do not call self.parent() —
        # that name shadows QWidget.parent().
        p = self.parent
        if p is not None:
            self.setGeometry(p.rect())

    def mousePressEvent(self, event):
        # Dismiss if click outside the white panel (header + scroll)
        for child in self.children():
            if isinstance(child, QWidget) and child.geometry().contains(event.pos()):
                return
        self.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()


class VisitOverlay(QWidget):
    """Base overlay for visit types (bathroom, nurse, water).

    Subclasses set TITLE, ACCENT_COLOR, and ENTRY_METHOD to customise
    appearance and which parent handler is called on card tap / keypad OK.
    """

    TITLE = ""
    END_TITLE = ""
    VISIT_TYPE = ""
    ACCENT_COLOR = "#23405a"
    ENTRY_METHOD = ""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: rgba(0,0,0,0.7);")
        self.setWindowFlags(Qt.Widget | Qt.FramelessWindowHint)
        self.setVisible(False)
        self.setGeometry(parent.rect())
        self.parent = parent

        accent = self.ACCENT_COLOR

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Left side: Keypad
        keypad_container = QWidget()
        keypad_container.setStyleSheet("background: white; border-top-left-radius: 24px; border-bottom-left-radius: 24px;")
        keypad_container.setFixedWidth(400)
        keypad_layout = QVBoxLayout(keypad_container)
        keypad_layout.setContentsMargins(24, 24, 24, 24)
        keypad_layout.setSpacing(16)

        keypad_title = QLabel("Enter ID Number")
        keypad_title.setAlignment(Qt.AlignCenter)
        keypad_title.setFont(QFont('Arial', 20, QFont.Bold))
        keypad_title.setStyleSheet("color: #23405a; margin-bottom: 16px;")
        keypad_layout.addWidget(keypad_title)

        self.input = QLineEdit()
        self.input.setAlignment(Qt.AlignCenter)
        self.input.setFont(QFont('Arial', 24, QFont.Bold))
        self.input.setReadOnly(True)
        self.input.setStyleSheet(
            "QLineEdit { background: #fff; color: #23405a; border: 2px solid #23405a; border-radius: 12px; padding: 12px; margin-bottom: 16px; }"
        )
        keypad_layout.addWidget(self.input)

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
                    f"QPushButton {{ background: {accent}; color: white; border-radius: 16px; border: 2px solid {accent}; }}"
                    f"QPushButton:hover {{ background: {accent}; }}"
                    f"QPushButton:pressed {{ background: {accent}; }}"
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

        # Right side: Title, instructions, status, cancel
        text_container = QWidget()
        text_container.setStyleSheet("background: white; border-top-right-radius: 24px; border-bottom-right-radius: 24px;")
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(40, 40, 40, 40)
        text_layout.setSpacing(24)

        self.main_title = QLabel(self.TITLE)
        self.main_title.setAlignment(Qt.AlignCenter)
        self.main_title.setFont(QFont('Arial', 24, QFont.Bold))
        self.main_title.setStyleSheet("color: #23405a; margin-bottom: 32px;")
        text_layout.addWidget(self.main_title)

        instructions = QLabel("Scan your ID card or enter your ID number using the keypad on the left.")
        instructions.setAlignment(Qt.AlignCenter)
        instructions.setWordWrap(True)
        instructions.setFont(QFont('Arial', 18))
        instructions.setStyleSheet("color: #23405a; line-height: 1.4; margin-bottom: 32px;")
        text_layout.addWidget(instructions)

        self.status_label = QLabel("Ready to scan")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont('Arial', 20, QFont.Bold))
        self.status_label.setStyleSheet(f"color: {accent}; margin-bottom: 32px;")
        text_layout.addWidget(self.status_label)

        self.message_label = QLabel("")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.setFont(QFont('Arial', 16))
        self.message_label.setStyleSheet("color: #b71c1c; margin-bottom: 32px;")
        self.message_label.hide()
        text_layout.addWidget(self.message_label)

        text_layout.addStretch()

        cancel_btn = QPushButton('Cancel')
        cancel_btn.setFont(QFont('Arial', 18, QFont.Bold))
        cancel_btn.setStyleSheet(
            "QPushButton { background: #e0e0e0; color: #23405a; border-radius: 16px; padding: 16px 0; border: 2px solid #b0b0b0; } "
            "QPushButton:hover { background: #cccccc; } "
            "QPushButton:pressed { background: #bbbbbb; }"
        )
        cancel_btn.clicked.connect(self.hide)
        text_layout.addWidget(cancel_btn)

        layout.addWidget(keypad_container)
        layout.addWidget(text_container)

        self._message_timer = QTimer(self)
        self._message_timer.setSingleShot(True)
        self._message_timer.timeout.connect(self.clear_message)

    def _has_active_visit_of_this_type(self):
        db = getattr(self.parent, "db", None)
        if not db or not self.VISIT_TYPE:
            return False
        try:
            outings = db.get_active_outings() or []
        except Exception:
            return False
        return any(o.get("type") == self.VISIT_TYPE for o in outings)

    def show_overlay(self):
        self.input.setText("")
        title = self.END_TITLE if (self.END_TITLE and self._has_active_visit_of_this_type()) else self.TITLE
        self.main_title.setText(title)
        self.setGeometry(self.parent.rect())
        self.setVisible(True)
        self.raise_()
        self.clear_message()
        self.status_label.setText("Ready to scan")
        self.status_label.setStyleSheet(f"color: {self.ACCENT_COLOR}; margin-bottom: 32px;")

    def show_message(self, message, duration=4000):
        self.message_label.setText(message)
        self.message_label.show()
        self._message_timer.start(duration)

    def clear_message(self):
        self.message_label.hide()
        self.message_label.setText("")

    def _call_entry(self, **kwargs):
        getattr(self.parent, self.ENTRY_METHOD)(**kwargs)

    def ok_pressed(self):
        student_id = self.input.text()
        if student_id:
            self._call_entry(student_id=student_id)
            self.hide()

    def process_card(self, nfc_uid):
        self._call_entry(nfc_uid=nfc_uid)
        self.hide()


class BathroomOverlay(VisitOverlay):
    TITLE = "Bathroom Break"
    END_TITLE = "End Bathroom Break"
    VISIT_TYPE = "Bathroom"
    ACCENT_COLOR = "#2bb3a3"
    ENTRY_METHOD = "process_bathroom_entry"


class NurseOverlay(VisitOverlay):
    TITLE = "Nurse Visit"
    END_TITLE = "End Nurse Visit"
    VISIT_TYPE = "Nurse"
    ACCENT_COLOR = "#23405a"
    ENTRY_METHOD = "process_nurse_entry"


class WaterOverlay(VisitOverlay):
    TITLE = "Water Fountain"
    END_TITLE = "End Water Visit"
    VISIT_TYPE = "Water"
    ACCENT_COLOR = "#3498db"
    ENTRY_METHOD = "process_water_entry"


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


class BreakTypePickerOverlay(QWidget):
    """Fullscreen overlay letting a student choose Bathroom, Nurse, or Water after tapping their card."""

    break_selected = pyqtSignal(str, str, str)  # break_type, nfc_uid, student_id

    _AUTO_DISMISS_MS = 10000
    _END_LABELS = {
        "Bathroom": "End bathroom break",
        "Nurse": "End nurse visit",
        "Water": "End water visit",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self._nfc_uid = ""
        self._student_id = ""

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: rgba(0,0,0,0.6);")
        self.setWindowFlags(Qt.Widget | Qt.FramelessWindowHint)
        self.setVisible(False)
        if parent:
            self.setGeometry(parent.rect())

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        container = QWidget()
        container.setStyleSheet("background: white; border-radius: 24px;")
        container.setFixedSize(480, 400)
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(32, 28, 32, 28)
        vbox.setSpacing(16)

        self.name_label = QLabel("")
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setFont(QFont("Arial", 22, QFont.Bold))
        self.name_label.setStyleSheet("color: #23405a;")
        vbox.addWidget(self.name_label)

        self.subtitle = QLabel("Where are you going?")
        self.subtitle.setAlignment(Qt.AlignCenter)
        self.subtitle.setFont(QFont("Arial", 16))
        self.subtitle.setStyleSheet("color: #666;")
        vbox.addWidget(self.subtitle)

        vbox.addSpacing(8)

        btn_data = [
            ("Bathroom", "#2bb3a3", "#249e90"),
            ("Nurse", "#23405a", "#1a3048"),
            ("Water", "#3498db", "#2980b9"),
        ]
        self._type_buttons = {}
        for label, bg, bg_pressed in btn_data:
            btn = QPushButton(label)
            btn.setFont(QFont("Arial", 20, QFont.Bold))
            btn.setMinimumHeight(64)
            btn.setStyleSheet(
                f"QPushButton {{ background: {bg}; color: white; border-radius: 16px; padding: 12px 0; }} "
                f"QPushButton:hover {{ background: {bg_pressed}; }} "
                f"QPushButton:pressed {{ background: {bg_pressed}; }}"
            )
            btn.clicked.connect(lambda _, t=label: self._on_selected(t))
            self._type_buttons[label] = btn
            vbox.addWidget(btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFont(QFont("Arial", 14))
        cancel_btn.setMinimumHeight(40)
        cancel_btn.setStyleSheet(
            "QPushButton { background: #e0e0e0; color: #23405a; border-radius: 12px; } "
            "QPushButton:hover { background: #ccc; } QPushButton:pressed { background: #bbb; }"
        )
        cancel_btn.clicked.connect(self.hide)
        vbox.addWidget(cancel_btn)

        layout.addWidget(container)

        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self.hide)

    def _active_visit_type(self, nfc_uid, student_id):
        db = getattr(self.parent, "db", None)
        identifier = nfc_uid or student_id
        if not db or not identifier:
            return None
        try:
            if db.is_on_break(identifier):
                return "Bathroom"
            if db.is_at_nurse(identifier):
                return "Nurse"
            if db.is_at_water(identifier):
                return "Water"
        except Exception as e:
            print(f"[PICKER] Could not check active visit: {e}")
        return None

    def show_for_student(self, student_name: str, nfc_uid: str = "", student_id: str = ""):
        """Show the picker for a specific student."""
        self._nfc_uid = nfc_uid
        self._student_id = student_id
        self.name_label.setText(student_name or "Student")
        active = self._active_visit_type(nfc_uid, student_id)
        if active:
            self.subtitle.setText("Tap to end your visit")
            for visit_type, btn in self._type_buttons.items():
                if visit_type == active:
                    btn.setText(self._END_LABELS.get(visit_type, f"End {visit_type}"))
                    btn.setVisible(True)
                else:
                    btn.setVisible(False)
        else:
            self.subtitle.setText("Where are you going?")
            for visit_type, btn in self._type_buttons.items():
                btn.setText(visit_type)
                btn.setVisible(True)
        if self.parent:
            self.setGeometry(self.parent.rect())
        self.setVisible(True)
        self.raise_()
        self._dismiss_timer.start(self._AUTO_DISMISS_MS)

    def _on_selected(self, break_type: str):
        self._dismiss_timer.stop()
        self.hide()
        self.break_selected.emit(break_type, self._nfc_uid, self._student_id)

    def mousePressEvent(self, event):
        for child in self.children():
            if isinstance(child, QWidget) and child.geometry().contains(event.pos()):
                return
        self.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
