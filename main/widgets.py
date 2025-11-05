"""
Custom widgets for the NFC Reader GUI application.
"""

from PyQt5.QtWidgets import QWidget, QFrame
from PyQt5.QtCore import QTimer, QTime, Qt, QRect
from PyQt5.QtGui import QFont, QColor, QPainter, QPen


class StatusIndicator(QFrame):
    """A visual indicator showing bathroom break status."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 50)  # Size of the square
        self.setFrameShape(QFrame.Box)
        self.setFrameShadow(QFrame.Raised)
        self.setLineWidth(2)
        self.set_status(False)  # Start with green (no active breaks)
    
    def set_status(self, has_active_breaks):
        """Set the color based on bathroom break status"""
        if has_active_breaks:
            self.setStyleSheet("background-color: #ff4444;")  # Red
        else:
            self.setStyleSheet("background-color: #44ff44;")  # Green


class AnalogClock(QWidget):
    """A custom analog clock widget."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 220)
        self._overlay_text = ""
        timer = QTimer(self)
        timer.timeout.connect(self.update)
        timer.start(1000)

    def set_overlay_text(self, text: str):
        """Set small text to render inside the clock near the bottom."""
        self._overlay_text = text or ""
        self.update()

    def paintEvent(self, event):
        side = min(self.width(), self.height())
        time = QTime.currentTime()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(side / 200.0, side / 200.0)

        # Draw clock face
        painter.setPen(QPen(QColor("#2bb3a3"), 8))
        painter.drawEllipse(-90, -90, 180, 180)

        # Draw hour ticks
        painter.setPen(QPen(Qt.black, 4))
        for i in range(12):
            painter.save()
            painter.rotate(i * 30)
            painter.drawLine(0, -80, 0, -90)
            painter.restore()

        # Draw minute ticks
        painter.setPen(QPen(Qt.black, 1))
        for i in range(60):
            if i % 5 != 0:
                painter.save()
                painter.rotate(i * 6)
                painter.drawLine(0, -85, 0, -90)
                painter.restore()

        # Draw hour hand
        painter.setPen(QPen(Qt.black, 8, Qt.SolidLine, Qt.RoundCap))
        hour_angle = 30 * ((time.hour() % 12) + time.minute() / 60.0)
        painter.save()
        painter.rotate(hour_angle)
        painter.drawLine(0, 0, 0, -45)
        painter.restore()

        # Draw minute hand
        painter.setPen(QPen(Qt.black, 4, Qt.SolidLine, Qt.RoundCap))
        minute_angle = 6 * (time.minute() + time.second() / 60.0)
        painter.save()
        painter.rotate(minute_angle)
        painter.drawLine(0, 0, 0, -70)
        painter.restore()

        # Draw second hand (red)
        painter.setPen(QPen(Qt.red, 2, Qt.SolidLine, Qt.RoundCap))
        second_angle = 6 * time.second()
        painter.save()
        painter.rotate(second_angle)
        painter.drawLine(0, 10, 0, -75)
        painter.restore()

        # Draw center dot
        painter.setBrush(Qt.black)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(-6, -6, 12, 12)

        # Draw overlay text near bottom (inside clock)
        if self._overlay_text:
            painter.setPen(QPen(Qt.black))
            painter.setFont(QFont('Arial', 14, QFont.Bold))
            # Rect spanning lower portion of the dial
            text_rect = QRect(-80, 30, 160, 35)
            painter.drawText(text_rect, Qt.AlignCenter, self._overlay_text)
