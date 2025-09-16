#!/bin/bash

# Test script to verify NFC Reader will start on reboot

echo "🔄 Testing NFC Reader Reboot Startup"
echo "===================================="

# Check current service status
echo "1. Current service status:"
systemctl status nfc-reader.service --no-pager -l

echo ""
echo "2. Service dependencies:"
systemctl list-dependencies nfc-reader.service --no-pager

echo ""
echo "3. Service is enabled for:"
systemctl is-enabled nfc-reader.service

echo ""
echo "4. Checking if service will start after graphical-session.target:"
if systemctl list-dependencies graphical-session.target | grep -q "nfc-reader.service"; then
    echo "✅ Service is configured to start after graphical-session.target"
else
    echo "❌ Service is NOT configured to start after graphical-session.target"
fi

echo ""
echo "5. Testing startup script manually:"
echo "   Running startup script in background..."
nohup /home/jdrevnyak/id/autostart_nfc.sh > /tmp/test_startup.log 2>&1 &
STARTUP_PID=$!

echo "   Startup script PID: $STARTUP_PID"
echo "   Waiting 45 seconds for startup to complete..."

sleep 45

echo ""
echo "6. Checking if application started:"
if pgrep -f "nfc_reader_gui.py" > /dev/null; then
    echo "✅ Application is running"
    echo "   PID: $(pgrep -f 'nfc_reader_gui.py')"
else
    echo "❌ Application is not running"
    echo "   Checking startup log..."
    if [ -f "/tmp/test_startup.log" ]; then
        echo "   Last 10 lines of startup log:"
        tail -10 /tmp/test_startup.log
    fi
fi

echo ""
echo "7. Cleanup:"
kill $STARTUP_PID 2>/dev/null
rm -f /tmp/test_startup.log

echo ""
echo "📋 Summary:"
echo "==========="
if systemctl is-enabled nfc-reader.service > /dev/null; then
    echo "✅ Service is enabled for startup"
else
    echo "❌ Service is NOT enabled"
fi

if pgrep -f "nfc_reader_gui.py" > /dev/null; then
    echo "✅ Application is currently running"
else
    echo "❌ Application is not running"
fi

echo ""
echo "🚀 To test actual reboot startup:"
echo "1. Run: sudo reboot"
echo "2. Wait for system to fully boot (2-3 minutes)"
echo "3. Check: ps aux | grep nfc_reader_gui"
echo "4. Check: systemctl status nfc-reader.service"
echo "5. Check logs: tail -f /tmp/nfc_reader.log"


