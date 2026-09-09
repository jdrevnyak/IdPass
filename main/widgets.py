"""
Custom widgets for the NFC Reader GUI application.
"""

from PyQt5.QtWidgets import (QWidget, QFrame, QAbstractButton, QSizePolicy,
                             QVBoxLayout, QHBoxLayout, QLabel)
from PyQt5.QtCore import QTimer, QTime, Qt, QRect, QRectF, QSize, QPointF
from PyQt5.QtGui import (QFont, QColor, QPainter, QPen, QBrush, QLinearGradient,
                         QPainterPath, QPolygonF, QFontMetrics)


# Kiosk colour palette, sampled from the approved UI mock-ups.
THEME = {
    "page_bg": "#0f1420",
    "panel_bg": "#1a2032",
    "topbar_bg": "#232a3d",
    "topbar_text": "#ffffff",
    "card_bg": "#ffffff",
    "pill_bg": "#f8fafc",
    "pill_border": "#e2e8f0",
    "pill_text": "#334155",
    "ok": "#22c55e",
    "ok_text": "#16a34a",
    "warn": "#f59e0b",
    "warn_text": "#b45309",
    "busy": "#ef4444",
    "busy_text": "#dc2626",
}

# Per-destination gradients (top, bottom) plus the glyph drawn on the tile.
DESTINATION_STYLES = {
    "Bathroom": {"glyph": "bathroom", "gradient": ("#12a3dd", "#0b83c6")},
    "Nurse": {"glyph": "plus", "gradient": ("#f0455f", "#d92c50")},
    "Water": {"glyph": "droplet", "gradient": ("#2fc0ad", "#16a394")},
    "Guidance": {"glyph": "compass", "gradient": ("#a24df0", "#7b3fe4")},
}

# Shown on a tile whose visit type is currently active.
_ACTIVE_GRADIENT = ("#64748b", "#475569")


def _shift(hex_color, factor):
    """Return hex_color scaled towards black (factor < 1) or white (factor > 1)."""
    color = QColor(hex_color)
    if factor <= 1.0:
        return color.darker(int(100 / max(factor, 0.01)))
    return color.lighter(int(100 * factor))


def draw_glyph(painter, name, size, color, stroke=2.0):
    """Draw a line-art glyph in a size x size box whose top-left is the painter origin.

    Glyph geometry is authored in a 24x24 space so the stroke weight scales with
    the icon; callers only translate to the desired position."""
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    painter.scale(size / 24.0, size / 24.0)
    pen = QPen(QColor(color), stroke, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)

    if name == "wifi":
        for radius in (12.5, 8.0, 3.5):
            painter.drawArc(QRectF(12 - radius, 19 - radius, radius * 2, radius * 2),
                            40 * 16, 100 * 16)
        painter.setBrush(QBrush(QColor(color)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(12, 19), 1.4, 1.4)
    elif name == "cap":
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(color)))
        painter.drawPolygon(QPolygonF([
            QPointF(12, 4.5), QPointF(22.5, 9.5), QPointF(12, 14.5), QPointF(1.5, 9.5),
        ]))
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        body = QPainterPath()
        body.moveTo(5.5, 11.4)
        body.lineTo(5.5, 15.2)
        body.cubicTo(8.0, 18.4, 16.0, 18.4, 18.5, 15.2)
        body.lineTo(18.5, 11.4)
        painter.drawPath(body)
    elif name == "bathroom":
        painter.drawRoundedRect(QRectF(3, 5.5, 18, 13), 2.5, 2.5)
        painter.drawLine(QPointF(9.5, 5.5), QPointF(9.5, 18.5))
        painter.drawLine(QPointF(13.5, 9.5), QPointF(13.5, 14.5))
        painter.drawLine(QPointF(17.3, 9.5), QPointF(17.3, 14.5))
    elif name == "plus":
        painter.setPen(QPen(QColor(color), stroke * 1.6, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(QPointF(4.5, 12), QPointF(19.5, 12))
        painter.drawLine(QPointF(12, 4.5), QPointF(12, 19.5))
    elif name == "droplet":
        painter.drawEllipse(QPointF(12, 12), 7.5, 7.5)
    elif name == "compass":
        painter.drawEllipse(QPointF(12, 12), 7.5, 7.5)
        painter.drawLine(QPointF(8.8, 15.2), QPointF(15.2, 8.8))
    elif name == "lock":
        painter.drawRoundedRect(QRectF(5, 10.5, 14, 9), 2.0, 2.0)
        arc = QPainterPath()
        arc.moveTo(8.2, 10.5)
        arc.lineTo(8.2, 8.2)
        arc.cubicTo(8.2, 4.4, 15.8, 4.4, 15.8, 8.2)
        arc.lineTo(15.8, 10.5)
        painter.drawPath(arc)
    elif name == "backspace":
        path = QPainterPath()
        path.moveTo(21, 6.5)
        path.lineTo(9.5, 6.5)
        path.lineTo(3.5, 12)
        path.lineTo(9.5, 17.5)
        path.lineTo(21, 17.5)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(QPointF(12.2, 9.2), QPointF(17.8, 14.8))
        painter.drawLine(QPointF(17.8, 9.2), QPointF(12.2, 14.8))
    elif name == "gear":
        painter.drawEllipse(QPointF(12, 12), 3.6, 3.6)
        painter.drawEllipse(QPointF(12, 12), 6.6, 6.6)
        for i in range(6):
            painter.save()
            painter.translate(12, 12)
            painter.rotate(i * 60)
            painter.drawRoundedRect(QRectF(-1.7, -11.4, 3.4, 3.8), 0.8, 0.8)
            painter.restore()

    painter.restore()


class GlyphIcon(QWidget):
    """A fixed-size widget rendering one of the painter-drawn glyphs."""

    def __init__(self, name, size=20, color="#ffffff", stroke=2.0, parent=None):
        super().__init__(parent)
        self._name = name
        self._color = color
        self._stroke = stroke
        self.setFixedSize(size, size)

    def set_color(self, color):
        """Recolour the glyph (used to reflect Wi-Fi / connection state)."""
        if color != self._color:
            self._color = color
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        draw_glyph(painter, self._name, min(self.width(), self.height()),
                   self._color, self._stroke)


class GlyphButton(QAbstractButton):
    """Clickable glyph with a generous touch target for the kiosk top bar."""

    def __init__(self, name, size=22, color="#e2e8f0", stroke=1.8, parent=None):
        super().__init__(parent)
        self._name = name
        self._color = color
        self._stroke = stroke
        self._icon_size = size
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(max(40, size + 16), max(40, size + 16))
        self.setFocusPolicy(Qt.NoFocus)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self.isDown():
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 28)))
            painter.drawEllipse(QRectF(self.rect()).adjusted(2, 2, -2, -2))
        size = float(self._icon_size)
        painter.translate((self.width() - size) / 2.0, (self.height() - size) / 2.0)
        draw_glyph(painter, self._name, size, self._color, self._stroke)


class DestinationTile(QAbstractButton):
    """A gradient hall-pass destination tile: glyph above an uppercase label."""

    _RADIUS = 14

    def __init__(self, destination, parent=None):
        super().__init__(parent)
        style = DESTINATION_STYLES[destination]
        self.destination = destination
        self._glyph = style["glyph"]
        self._gradient = style["gradient"]
        self._active = False
        self.setText(destination)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(90, 90)

    def set_active(self, active):
        """Switch between 'go here' and 'end your visit' presentation."""
        active = bool(active)
        if active != self._active:
            self._active = active
            self.update()

    def is_active(self):
        return self._active

    def sizeHint(self):
        return QSize(166, 180)

    def _label(self):
        return f"END {self.destination}".upper() if self._active else self.destination.upper()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        top, bottom = _ACTIVE_GRADIENT if self._active else self._gradient
        if self.isDown():
            top, bottom = _shift(top, 0.88).name(), _shift(bottom, 0.88).name()

        gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        gradient.setColorAt(0.0, QColor(top))
        gradient.setColorAt(1.0, QColor(bottom))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawRoundedRect(rect, self._RADIUS, self._RADIUS)

        icon_size = min(54.0, max(24.0, min(rect.width(), rect.height()) * 0.26))
        painter.save()
        painter.translate(rect.center().x() - icon_size / 2,
                          rect.top() + rect.height() * 0.40 - icon_size / 2)
        draw_glyph(painter, self._glyph, icon_size, "#ffffff", 2.2)
        painter.restore()

        label = self._label()
        point_size = min(19, max(10, int(rect.width() * 0.072)))
        font = QFont("Arial", point_size, QFont.Bold)
        text_rect = QRectF(rect.left() + 6, rect.top() + rect.height() * 0.60,
                           rect.width() - 12, rect.height() * 0.32)
        # Long "END ..." labels must not overflow the tile, so shrink until they fit.
        while point_size > 8 and QFontMetrics(font).width(label) > text_rect.width():
            point_size -= 1
            font = QFont("Arial", point_size, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QPen(QColor("#ffffff")))
        painter.drawText(text_rect, Qt.AlignHCenter | Qt.AlignTop, label)


class StatusPill(QWidget):
    """Rounded pill with a coloured status dot, e.g. a green 'System Ready'."""

    _STATES = {
        "ok": (THEME["ok"], THEME["ok_text"]),
        "warn": (THEME["warn"], THEME["warn_text"]),
        "busy": (THEME["busy"], THEME["busy_text"]),
    }

    def __init__(self, text="System Ready", state="ok", parent=None):
        super().__init__(parent)
        self._text = text
        self._state = state if state in self._STATES else "ok"
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.setMinimumHeight(46)

    def set_state(self, state, text=None):
        """Update dot colour and, optionally, the label."""
        if state in self._STATES:
            self._state = state
        if text is not None:
            self._text = text
        self.updateGeometry()
        self.update()

    def _font(self):
        return QFont("Arial", 13, QFont.Bold)

    def sizeHint(self):
        return QSize(QFontMetrics(self._font()).width(self._text) + 62, 46)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = rect.height() / 2

        painter.setPen(QPen(QColor(THEME["pill_border"]), 1))
        painter.setBrush(QBrush(QColor(THEME["pill_bg"])))
        painter.drawRoundedRect(rect, radius, radius)

        dot_color, text_color = self._STATES[self._state]
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(dot_color)))
        painter.drawEllipse(QPointF(rect.left() + 22, rect.center().y()), 5, 5)

        painter.setPen(QPen(QColor(text_color)))
        painter.setFont(self._font())
        painter.drawText(rect.adjusted(38, 0, -16, 0), Qt.AlignLeft | Qt.AlignVCenter, self._text)


class HomeScreen(QWidget):
    """Kiosk home screen: dark top bar over a white card of destination tiles.

    Pure presentation -- the application wires up behaviour by connecting to
    ``tiles``, ``prompt``, ``top_bar`` and ``system_pill``."""

    DESTINATIONS = ("Bathroom", "Nurse", "Water", "Guidance")

    # Tight padding so the card fills an 800x480 kiosk without a dark band.
    _BODY_MARGINS = (10, 8, 10, 8)
    _CARD_PAD = 12
    _GAP = 10
    _STATUS_H = 44

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"background: {THEME['page_bg']};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- Top bar -------------------------------------------------------
        self.top_bar = QFrame()
        self.top_bar.setAttribute(Qt.WA_StyledBackground, True)
        self.top_bar.setFixedHeight(40)
        self.top_bar.setStyleSheet(f"background: {THEME['topbar_bg']};")
        bar = QHBoxLayout(self.top_bar)
        bar.setContentsMargins(20, 0, 12, 0)
        bar.setSpacing(14)

        self.wifi_icon = GlyphIcon("wifi", 19, "#e2e8f0", 1.8)
        self.classroom_icon = GlyphIcon("cap", 20, "#e2e8f0", 1.8)
        bar.addWidget(self.wifi_icon)
        bar.addWidget(self.classroom_icon)

        self.classroom_label = QLabel("")
        self.classroom_label.setFont(QFont("Arial", 12))
        self.classroom_label.setStyleSheet("color: #94a3b8;")
        bar.addWidget(self.classroom_label)
        bar.addStretch(1)

        self.datetime_label = QLabel("")
        self.datetime_label.setFont(QFont("Arial", 13, QFont.Bold))
        self.datetime_label.setStyleSheet(f"color: {THEME['topbar_text']};")
        bar.addWidget(self.datetime_label)

        self.settings_button = GlyphButton("gear", 20, "#e2e8f0", 1.8)
        self.settings_button.setToolTip("Settings")
        bar.addWidget(self.settings_button)
        root.addWidget(self.top_bar)

        # --- Body ----------------------------------------------------------
        self._body = QWidget()
        body_layout = QVBoxLayout(self._body)
        body_layout.setContentsMargins(*self._BODY_MARGINS)
        body_layout.setSpacing(0)

        card = QFrame()
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setStyleSheet(f"background: {THEME['card_bg']}; border-radius: 16px;")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(*([self._CARD_PAD] * 4))
        card_layout.setSpacing(self._GAP)

        self._tile_host = QWidget()
        tile_row = QHBoxLayout(self._tile_host)
        tile_row.setContentsMargins(0, 0, 0, 0)
        tile_row.setSpacing(self._GAP)
        self.tiles = {}
        for destination in self.DESTINATIONS:
            tile = DestinationTile(destination)
            self.tiles[destination] = tile
            tile_row.addWidget(tile, 1)
        self._tile_host.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        card_layout.addWidget(self._tile_host, 1)

        status_row = QHBoxLayout()
        status_row.setSpacing(12)

        self.prompt = QLabel("Select your hall pass destination")
        self.prompt.setAlignment(Qt.AlignCenter)
        self.prompt.setWordWrap(True)
        self.prompt.setFont(QFont("Arial", 13))
        self.prompt.setFixedHeight(self._STATUS_H)
        self.prompt.setCursor(Qt.PointingHandCursor)
        self.prompt.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.prompt.setStyleSheet(
            f"background: {THEME['pill_bg']}; color: {THEME['pill_text']};"
            f" border: 1px solid {THEME['pill_border']}; border-radius: 12px; padding: 6px 14px;"
        )
        status_row.addWidget(self.prompt, 1)

        self.system_pill = StatusPill("System Ready")
        self.system_pill.setFixedHeight(self._STATUS_H)
        status_row.addWidget(self.system_pill, 0)
        card_layout.addLayout(status_row, 0)

        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        body_layout.addWidget(card, 1)
        root.addWidget(self._body, 1)

    def set_datetime_text(self, text):
        self.datetime_label.setText(text)

    def set_wifi_connected(self, connected):
        self.wifi_icon.set_color("#e2e8f0" if connected else "#ef4444")


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
