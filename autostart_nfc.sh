#!/bin/bash

# Enhanced NFC Reader startup script with better logging
LOG_FILE="/tmp/nfc_reader.log"

echo "=== NFC Reader Autostart Script ===" >> $LOG_FILE
echo "Script started at: $(date)" >> $LOG_FILE

# Wait for system to be ready
echo "Waiting 30 seconds for desktop environment to be ready..." >> $LOG_FILE
sleep 30

# Set display environment
export DISPLAY=:0
export XAUTHORITY=/home/jdrevnyak/.Xauthority
export XDG_RUNTIME_DIR=/run/user/1000
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus
echo "Display environment set: DISPLAY=$DISPLAY" >> $LOG_FILE
echo "XDG_RUNTIME_DIR set: $XDG_RUNTIME_DIR" >> $LOG_FILE

# Navigate to the application directory
cd /home/jdrevnyak/id
echo "Working directory: $(pwd)" >> $LOG_FILE

# Check for and apply pending updates
if [ -f "pending_update/apply_update.py" ]; then
    echo "Applying pending update..." >> $LOG_FILE
    python3 pending_update/apply_update.py >> $LOG_FILE 2>&1
    echo "Update applied successfully" >> $LOG_FILE
fi




# Add system site-packages to Python path for PyQt5
export PYTHONPATH="/usr/lib/python3/dist-packages:$PYTHONPATH"

echo "Python version: $(python --version)" >> $LOG_FILE
echo "Python path: $(which python)" >> $LOG_FILE
echo "PYTHONPATH: $PYTHONPATH" >> $LOG_FILE

# Test package imports
echo "Testing package imports..." >> $LOG_FILE
python -c "import gspread; print('✓ gspread available')" >> $LOG_FILE 2>&1
python -c "import PyQt5; print('✓ PyQt5 available')" >> $LOG_FILE 2>&1

# Check if display is available
echo "Checking if display is available..." >> $LOG_FILE
if xset q &>/dev/null; then
    echo "✅ Display is available" >> $LOG_FILE
else
    echo "❌ Display not available, waiting 10 more seconds..." >> $LOG_FILE
    sleep 10
    if ! xset q &>/dev/null; then
        echo "❌ Display still not available, exiting..." >> $LOG_FILE
        exit 1
    fi
fi

echo "Starting NFC Reader application at: $(date)" >> $LOG_FILE
python nfc_reader_gui.py >> $LOG_FILE 2>&1 