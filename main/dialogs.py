"""
Dialog classes for the NFC Reader GUI application.
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QPushButton, QFormLayout, QFileDialog)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class AddStudentDialog(QDialog):
    """Dialog for adding a new student."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Student")
        self.setModal(True)
        
        layout = QFormLayout(self)
        
        self.student_id = QLineEdit()
        self.student_name = QLineEdit()
        
        layout.addRow("Student ID:", self.student_id)
        layout.addRow("Student Name:", self.student_name)
        
        buttons = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
        buttons.addWidget(self.ok_button)
        buttons.addWidget(self.cancel_button)
        layout.addRow(buttons)


class ImportDialog(QDialog):
    """Dialog for importing students from a file."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Students")
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # File selection
        file_layout = QHBoxLayout()
        self.file_path = QLineEdit()
        self.file_path.setReadOnly(True)
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse_file)
        file_layout.addWidget(QLabel("File:"))
        file_layout.addWidget(self.file_path)
        file_layout.addWidget(self.browse_button)
        layout.addLayout(file_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.import_button = QPushButton("Import")
        self.cancel_button = QPushButton("Cancel")
        
        self.import_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.import_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
    
    def browse_file(self):
        """Open file browser to select import file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File",
            "",
            "CSV Files (*.csv);;JSON Files (*.json)"
        )
        if file_path:
            self.file_path.setText(file_path)
