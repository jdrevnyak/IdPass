"""Screens for a student's place in the bathroom line, and the teacher's list."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QFrame,
    QMessageBox, QSizePolicy,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from bathroom_line import ordinal


class BathroomLinePlaceOverlay(QWidget):
    """Tells one student their place and lets them leave."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: rgba(15, 20, 32, 0.72);")
        self.setWindowFlags(Qt.Widget | Qt.FramelessWindowHint)
        self.setVisible(False)
        if parent:
            self.setGeometry(parent.rect())
        self._entry = None

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setStyleSheet("background: white; border-radius: 18px;")
        card.setFixedWidth(440)
        box = QVBoxLayout(card)
        box.setContentsMargins(28, 28, 28, 24)
        box.setSpacing(16)

        self.message = QLabel("")
        self.message.setAlignment(Qt.AlignCenter)
        self.message.setWordWrap(True)
        self.message.setFont(QFont("Arial", 20, QFont.Bold))
        self.message.setStyleSheet("color: #1e293b;")
        box.addWidget(self.message)

        leave = QPushButton("Leave")
        leave.setMinimumHeight(56)
        leave.setFont(QFont("Arial", 16, QFont.Bold))
        leave.setStyleSheet(
            "QPushButton { background: #e2e8f0; color: #334155; border: none; border-radius: 14px; }"
            "QPushButton:pressed { background: #cbd5e1; }"
        )
        leave.clicked.connect(self._leave)
        box.addWidget(leave)

        close = QPushButton("Close")
        close.setMinimumHeight(56)
        close.setFont(QFont("Arial", 16, QFont.Bold))
        close.setStyleSheet(
            "QPushButton { background: #0f766e; color: white; border: none; border-radius: 14px; }"
            "QPushButton:pressed { background: #115e59; }"
        )
        close.clicked.connect(self.hide)
        box.addWidget(close)
        layout.addWidget(card)

    def show_place(self, entry, place):
        self._entry = entry
        self.message.setText(f"You are {ordinal(place)} in the bathroom line.")
        if self.parent:
            self.setGeometry(self.parent.rect())
        self.setVisible(True)
        self.raise_()

    def _leave(self):
        entry = self._entry
        self.hide()
        if entry and self.parent:
            self.parent.leave_bathroom_line(entry)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.parent:
            self.setGeometry(self.parent.rect())


class BathroomLineManagerOverlay(QWidget):
    """Teacher view of the bathroom line: remove one student, or clear it."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: rgba(15, 20, 32, 0.72);")
        self.setWindowFlags(Qt.Widget | Qt.FramelessWindowHint)
        self.setVisible(False)
        if parent:
            self.setGeometry(parent.rect())

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 24, 40, 20)
        root.setSpacing(12)

        card = QFrame()
        card.setStyleSheet("background: white; border-radius: 16px;")
        box = QVBoxLayout(card)
        box.setContentsMargins(16, 16, 16, 16)
        box.setSpacing(10)

        title = QLabel("Bathroom line")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setStyleSheet("color: #1e293b;")
        box.addWidget(title)

        self.empty_label = QLabel("No one is waiting.")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setFont(QFont("Arial", 16))
        self.empty_label.setStyleSheet("color: #64748b;")
        box.addWidget(self.empty_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self._host = QWidget()
        self._rows = QVBoxLayout(self._host)
        self._rows.setContentsMargins(0, 0, 0, 0)
        self._rows.setSpacing(8)
        self._rows.addStretch(1)
        scroll.setWidget(self._host)
        box.addWidget(scroll, 1)
        root.addWidget(card, 1)

        buttons = QHBoxLayout()
        self.clear_btn = QPushButton("Clear line")
        self.clear_btn.setMinimumHeight(52)
        self.clear_btn.setFont(QFont("Arial", 14, QFont.Bold))
        self.clear_btn.setStyleSheet(
            "QPushButton { background: #ef4444; color: white; border: none; border-radius: 12px; }"
            "QPushButton:pressed { background: #dc2626; }"
            "QPushButton:disabled { background: #cbd5e1; color: #64748b; }"
        )
        self.clear_btn.clicked.connect(self._clear)
        buttons.addWidget(self.clear_btn, 1)

        close = QPushButton("Close")
        close.setMinimumHeight(52)
        close.setFont(QFont("Arial", 14, QFont.Bold))
        close.setStyleSheet(
            "QPushButton { background: #e2e8f0; color: #334155; border: none; border-radius: 12px; }"
            "QPushButton:pressed { background: #cbd5e1; }"
        )
        close.clicked.connect(self.hide)
        buttons.addWidget(close, 1)
        root.addLayout(buttons)

    def show_overlay(self):
        self._rebuild()
        if self.parent:
            self.setGeometry(self.parent.rect())
        self.setVisible(True)
        self.raise_()

    def _rebuild(self):
        while self._rows.count():
            item = self._rows.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        students = list(self.parent.bathroom_line.students) if self.parent else []
        self.empty_label.setVisible(not students)
        self.clear_btn.setEnabled(bool(students))
        for index, student in enumerate(students):
            row = QWidget()
            row_box = QHBoxLayout(row)
            row_box.setContentsMargins(0, 0, 0, 0)
            name = QLabel(f"{index + 1}. {student.get('name') or 'Student'}")
            name.setFont(QFont("Arial", 16, QFont.Bold))
            name.setStyleSheet("color: #1e293b;")
            name.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            row_box.addWidget(name, 1)
            remove = QPushButton("Remove")
            remove.setMinimumHeight(44)
            remove.setFont(QFont("Arial", 12, QFont.Bold))
            remove.setStyleSheet(
                "QPushButton { background: #e2e8f0; color: #334155; border: none; "
                "border-radius: 10px; padding: 0 14px; }"
                "QPushButton:pressed { background: #cbd5e1; }"
            )
            remove.clicked.connect(lambda _, i=index, n=student.get("name") or "Student": self._remove(i, n))
            row_box.addWidget(remove)
            self._rows.addWidget(row)
        self._rows.addStretch(1)

    def _remove(self, index, name):
        answer = QMessageBox.question(
            self,
            "Bathroom line",
            f"Remove {name} from the line?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.parent.remove_bathroom_line_index(index)
        self._rebuild()

    def _clear(self):
        answer = QMessageBox.question(
            self,
            "Bathroom line",
            "Clear the bathroom line?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.parent.clear_bathroom_line()
        self._rebuild()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.parent:
            self.setGeometry(self.parent.rect())
