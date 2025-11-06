#!/bin/bash

SERVICE_NAME="nfc-reader"
SCRIPT_PATH="/home/jdrevnyak/id/autostart_nfc.sh"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "=== NFC Reader Service Setup ==="

# Make sure the script exists
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "ERROR: $SCRIPT_PATH not found."
    exit 1
fi

# Fix ownership and permissions
echo "Setting ownership and permissions..."
sudo chown jdrevnyak:jdrevnyak "$SCRIPT_PATH"
sudo chmod 755 "$SCRIPT_PATH"

# Create the systemd service file
echo "Creating systemd service at $SERVICE_FILE..."
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=NFC Reader Autostart
After=network.target graphical.target

[Service]
Type=simple
User=jdrevnyak
WorkingDirectory=/home/jdrevnyak/id
ExecStart=/usr/bin/env bash $SCRIPT_PATH
Restart=always
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/jdrevnyak/.Xauthority

[Install]
WantedBy=graphical.target
EOF

# Reload systemd and enable service
echo "Reloading systemd..."
sudo systemctl daemon-reload

echo "Enabling $SERVICE_NAME service..."
sudo systemctl enable "$SERVICE_NAME"

echo "Starting $SERVICE_NAME service..."
sudo systemctl start "$SERVICE_NAME"

echo "Done! Check status with: sudo systemctl status $SERVICE_NAME"
