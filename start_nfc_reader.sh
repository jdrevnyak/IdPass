#!/bin/bash

# Wait for display to be ready
sleep 15

# Set display environment
export DISPLAY=:0
export XAUTHORITY=/home/jdrevnyak/.Xauthority
export XDG_RUNTIME_DIR=/run/user/1000
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus

# Navigate to the application directory
cd /home/jdrevnyak/id

# Check if virtual environment exists
if [ ! -f "venv/bin/activate" ]; then
    echo "Virtual environment not found!"
    exit 1
fi

# Activate virtual environment and start the application
source venv/bin/activate
echo "Starting NFC Reader application..."
python nfc_reader_gui.py 