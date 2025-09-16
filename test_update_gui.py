#!/usr/bin/env python3
"""
Test script to reproduce the update issue in a GUI environment
"""

import sys
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer
from updater import UpdateManager

def test_update_gui():
    """Test the update functionality in GUI mode"""
    
    app = QApplication(sys.argv)
    
    # Create a simple window
    from PyQt5.QtWidgets import QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget
    
    class TestWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Update Test")
            self.setGeometry(100, 100, 400, 200)
            
            # Create central widget
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            layout = QVBoxLayout(central_widget)
            
            # Add label
            label = QLabel("Update Test Window")
            layout.addWidget(label)
            
            # Add test button
            test_btn = QPushButton("Test Update")
            test_btn.clicked.connect(self.test_update)
            layout.addWidget(test_btn)
            
            # Initialize update manager
            self.update_manager = UpdateManager(
                parent_window=self,
                current_version="1.0.0",  # This should trigger an update
                repo_owner="jdrevnyak",
                repo_name="IdPass"
            )
            # Disable auto-check
            self.update_manager.auto_check_timer.stop()
        
        def test_update(self):
            """Test the update process"""
            print("[TEST] Starting update test...")
            self.update_manager.check_for_updates(show_message=True)
    
    # Create and show window
    window = TestWindow()
    window.show()
    
    print("🧪 Update Test Window opened")
    print("Click 'Test Update' to test the update process")
    print("Check the console for detailed error messages")
    
    # Run the application
    sys.exit(app.exec_())

if __name__ == "__main__":
    test_update_gui()
