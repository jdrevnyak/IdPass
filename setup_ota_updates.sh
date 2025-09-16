#!/bin/bash

# Setup OTA Updates for ID Project (Raspberry Pi Only)
# This script configures the system for over-the-air updates of the Python application

echo "Setting up OTA Updates for ID Project (Raspberry Pi)..."

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo; then
    echo "Warning: This script is designed for Raspberry Pi"
fi

# Install required Python packages for OTA updates
echo "Installing required Python packages..."
pip3 install requests

# Create update configuration file
echo "Creating update configuration..."
cat > /home/jdrevnyak/id/update_config.json << EOF
{
    "current_version": "1.0.0",
    "repo_owner": "jdrevnyak",
    "repo_name": "IdPass",
    "auto_check_interval_hours": 24,
    "backup_enabled": true,
    "preserve_files": [
        "student_attendance.db",
        "bussed-2e3ff-926b7f131529.json",
        "requirements.txt"
    ]
}
EOF

# Create update log directory
mkdir -p /home/jdrevnyak/id/logs

# Create systemd service for automatic updates (optional)
echo "Creating systemd service for update management..."
sudo tee /etc/systemd/system/id-updater.service > /dev/null << EOF
[Unit]
Description=ID Project Update Manager
After=network.target

[Service]
Type=simple
User=jdrevnyak
WorkingDirectory=/home/jdrevnyak/id
ExecStart=/usr/bin/python3 /home/jdrevnyak/id/updater.py --daemon
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable the service (commented out by default)
# sudo systemctl enable id-updater.service
# sudo systemctl start id-updater.service

echo "OTA Update setup complete!"
echo ""
echo "Next steps:"
echo "1. Update the GitHub repository information in update_config.json"
echo "2. Update the version number in nfc_reader_gui.py"
echo "3. Create a GitHub repository and upload your code"
echo "4. Create releases on GitHub to distribute updates"
echo ""
echo "Manual update check:"
echo "python3 /home/jdrevnyak/id/updater.py --check"
