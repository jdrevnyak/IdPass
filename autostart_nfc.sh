#!/bin/bash

# Enhanced NFC Reader startup script with better logging
LOG_FILE="/tmp/nfc_reader.log"

echo "=== NFC Reader Autostart Script ===" >> $LOG_FILE
echo "Script started at: $(date)" >> $LOG_FILE

# Wait for system to be ready (reduced from 30 to 10 seconds)
echo "Waiting 10 seconds for system to be ready..." >> $LOG_FILE
sleep 10

# Set display environment
export DISPLAY=:0
export XAUTHORITY=/home/jdrevnyak/.Xauthority
echo "Display environment set: DISPLAY=$DISPLAY" >> $LOG_FILE

# Navigate to the application directory
cd /home/jdrevnyak/id
echo "Working directory: $(pwd)" >> $LOG_FILE




# Add system site-packages to Python path for PyQt5
export PYTHONPATH="/usr/lib/python3/dist-packages:$PYTHONPATH"

echo "Python version: $(python --version)" >> $LOG_FILE
echo "Python path: $(which python)" >> $LOG_FILE
echo "PYTHONPATH: $PYTHONPATH" >> $LOG_FILE

# Test package imports
echo "Testing package imports..." >> $LOG_FILE
python -c "import gspread; print('✓ gspread available')" >> $LOG_FILE 2>&1
python -c "import PyQt5; print('✓ PyQt5 available')" >> $LOG_FILE 2>&1

echo "Starting NFC Reader application at: $(date)" >> $LOG_FILE
python nfc_reader_gui.py >> $LOG_FILE 2>&1 