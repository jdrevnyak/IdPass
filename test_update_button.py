#!/usr/bin/env python3
"""
Test script to verify the update button functionality in the settings overlay
"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

# Import the main application
from nfc_reader_gui import NFCReaderGUI

def test_update_button():
    """Test the update button functionality"""
    app = QApplication(sys.argv)
    
    # Create the main window
    window = NFCReaderGUI()
    
    # Show the settings overlay
    window.settings_overlay.show_overlay()
    
    print("✅ Settings overlay opened")
    print("✅ Update button should be visible in the Database Sync Status section")
    print("✅ Current version should be displayed")
    print("✅ Click 'Check for Updates' to test the functionality")
    
    # Show the window
    window.show()
    
    # Run the application
    sys.exit(app.exec_())

if __name__ == "__main__":
    test_update_button()

