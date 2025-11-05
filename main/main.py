#!/usr/bin/env python3
"""
Main entry point for the ID Pass NFC Reader Application
This file is used by the OTA update system to launch the application.
"""

import sys
import os

# Add the main directory to the Python path so imports work correctly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the main application
from nfc_reader_gui import main

if __name__ == '__main__':
    main()
