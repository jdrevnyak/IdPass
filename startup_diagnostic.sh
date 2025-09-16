#!/bin/bash

# NFC Reader Startup Diagnostic Script
LOG_FILE="/tmp/nfc_startup_diagnostic.log"

echo "=== NFC Reader Startup Diagnostic ===" > $LOG_FILE
echo "Started at: $(date)" >> $LOG_FILE
echo "" >> $LOG_FILE

# Check if we're in the right directory
echo "Current directory: $(pwd)" >> $LOG_FILE
echo "Directory contents:" >> $LOG_FILE
ls -la >> $LOG_FILE 2>&1
echo "" >> $LOG_FILE

# Check if virtual environment exists
echo "Checking virtual environment..." >> $LOG_FILE
if [ -f "venv/bin/activate" ]; then
    echo "✓ Virtual environment found" >> $LOG_FILE
    echo "Python in venv: $(venv/bin/python --version)" >> $LOG_FILE 2>&1
else
    echo "✗ Virtual environment not found!" >> $LOG_FILE
    echo "Looking for Python installations:" >> $LOG_FILE
    which python3 >> $LOG_FILE 2>&1
    python3 --version >> $LOG_FILE 2>&1
fi
echo "" >> $LOG_FILE

# Check display environment
echo "Display environment:" >> $LOG_FILE
echo "DISPLAY=$DISPLAY" >> $LOG_FILE
echo "XAUTHORITY=$XAUTHORITY" >> $LOG_FILE
echo "USER=$USER" >> $LOG_FILE
echo "HOME=$HOME" >> $LOG_FILE
echo "" >> $LOG_FILE

# Check if GUI is available
echo "Testing X11 display..." >> $LOG_FILE
if command -v xset >/dev/null 2>&1; then
    xset q >> $LOG_FILE 2>&1
    if [ $? -eq 0 ]; then
        echo "✓ X11 display is accessible" >> $LOG_FILE
    else
        echo "✗ X11 display is not accessible" >> $LOG_FILE
    fi
else
    echo "xset not available" >> $LOG_FILE
fi
echo "" >> $LOG_FILE

# Check network connectivity
echo "Testing network connectivity..." >> $LOG_FILE
if ping -c 1 google.com >/dev/null 2>&1; then
    echo "✓ Network connectivity OK" >> $LOG_FILE
else
    echo "✗ Network connectivity failed" >> $LOG_FILE
fi
echo "" >> $LOG_FILE

# Check if NFC app is already running
echo "Checking for existing NFC app processes..." >> $LOG_FILE
ps aux | grep nfc_reader_gui.py | grep -v grep >> $LOG_FILE
if [ $? -eq 0 ]; then
    echo "⚠ NFC app is already running!" >> $LOG_FILE
else
    echo "✓ No existing NFC app processes found" >> $LOG_FILE
fi
echo "" >> $LOG_FILE

# Try to start the application with timing
echo "Starting NFC Reader application..." >> $LOG_FILE
echo "Start time: $(date)" >> $LOG_FILE

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "Virtual environment activated" >> $LOG_FILE
    echo "Python path: $(which python)" >> $LOG_FILE
    echo "PyQt5 check:" >> $LOG_FILE
    python -c "import PyQt5; print('PyQt5 available')" >> $LOG_FILE 2>&1
    
    echo "Attempting to start application..." >> $LOG_FILE
    python nfc_reader_gui.py >> $LOG_FILE 2>&1 &
    APP_PID=$!
    echo "Application started with PID: $APP_PID" >> $LOG_FILE
    
    # Wait a bit and check if it's still running
    sleep 5
    if kill -0 $APP_PID 2>/dev/null; then
        echo "✓ Application is running after 5 seconds" >> $LOG_FILE
    else
        echo "✗ Application stopped or failed to start" >> $LOG_FILE
    fi
else
    echo "✗ Cannot activate virtual environment" >> $LOG_FILE
fi

echo "Diagnostic completed at: $(date)" >> $LOG_FILE
echo "=== End Diagnostic ===" >> $LOG_FILE


