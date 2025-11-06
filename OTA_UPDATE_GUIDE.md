# OTA Update System Guide

## Overview

The Hall Pass System uses a two-component OTA update system:
1. **GUI Updater** (`updater.py`) - Downloads GitHub releases to `deposit/` folder
2. **OTA Manager** (`ota-update.py`) - Monitors `deposit/` and applies updates

## How It Works

### Update Flow
```
User clicks "Check for Updates" in GUI
  ↓
Downloads GitHub release to deposit/
  ↓
User restarts application
  ↓
ota-update.py detects files in deposit/
  ↓
Applies update to main/
  ↓
Restarts application with new version
```

## File Structure

```
IdPass/
├── ota-update.py          # Main OTA runner (run this!)
├── deposit/               # Updates downloaded here
├── main/                  # Running application
│   ├── main.py            # Launcher
│   ├── version.txt        # Current version
│   ├── nfc_reader_gui.py
│   └── ...
└── logs/                  # OTA logs
```

## Starting the Application

### On Raspberry Pi (Production):

**Option 1: Via OTA System (Recommended)**
```bash
cd /home/jdrevnyak/id
python3 ota-update.py
```

**Option 2: Via Systemd Service**
The service has been updated to use `ota-update.py`:
```bash
sudo systemctl start nfc_reader
```

### On Development Machine:

**From project root:**
```bash
cd /Users/jackdrevnyak/IdPass
python3 ota-update.py
```

**Direct launch (no OTA):**
```bash
cd /Users/jackdrevnyak/IdPass/main
python3 main.py
```

## Creating Updates

### GitHub Releases (Automatic)
1. Create a new release on GitHub with version tag (e.g., `v1.0.8`)
2. `ota-update.py` checks for updates every hour
3. Downloads to `deposit/` automatically
4. Applies on next restart

### Manual Updates (Deposit Folder)
1. Place updated files in `/path/to/IdPass/deposit/`
2. Restart application or wait for automatic detection
3. `ota-update.py` applies updates from `deposit/` to `main/`

## Files Preserved During Updates

These files are NEVER overwritten:
- `student_attendance.db` - Local database
- `firebase-service-account.json` - Firebase credentials
- `requirements.txt` - Python dependencies
- `main.py` - Application launcher
- `version.txt` - Version tracking

## Troubleshooting

### "Update ready" but doesn't apply on restart

**Problem**: Startup script runs `nfc_reader_gui.py` directly instead of `ota-update.py`

**Solution**: Update your startup method to use `ota-update.py`:

```bash
# Edit your service file or startup script
# Change from:
python nfc_reader_gui.py

# To:
python ota-update.py
```

### Deposit folder is empty after download

**Check**:
1. Look at console output when app starts for: `[UPDATE] Using deposit directory: /path/to/deposit`
2. Check that path actually matches `/path/to/IdPass/deposit`
3. Look for `[UPDATE] Copied file: filename` messages during download

**Common causes**:
- Download failed silently (check console for errors)
- Files already applied and deposit/ was cleared
- Wrong deposit directory being used

### Update downloads but never applies

**Solution**: The application must be started via `ota-update.py`, not directly:

```bash
# ✓ CORRECT:
python3 ota-update.py

# ✗ WRONG:
python3 nfc_reader_gui.py
python3 main/main.py
```

### Check if OTA system is running

```bash
# Check process
ps aux | grep ota-update.py

# Check logs
tail -f /path/to/IdPass/logs/logfile_*.log
```

## Verifying Updates

### Check Current Version
```bash
cat /path/to/IdPass/main/version.txt
```

### Check Deposit Folder
```bash
ls -la /path/to/IdPass/deposit/
# Should be empty if no updates pending
# Should have files if update downloaded but not applied yet
```

### Check OTA Logs
```bash
tail -100 /path/to/IdPass/logs/logfile_*.log
```

Look for:
- `Updates detected, applying...`
- `Update applied successfully!`
- `Copied file: filename`

## Update on Raspberry Pi

The startup scripts have been updated to use the OTA system:

1. **start_nfc_reader.sh** - Now runs `ota-update.py`
2. **autostart_nfc.sh** - Now runs `ota-update.py`
3. **startup_diagnostic.sh** - Now runs `ota-update.py`

After updating these files on your Raspberry Pi, the OTA system will work automatically!

## Manual Test

To manually test the update system:

```bash
# 1. Create a test file
echo "Test update v1.0.8" > /path/to/IdPass/deposit/test.txt

# 2. Check deposit
ls /path/to/IdPass/deposit/
# Should show: test.txt

# 3. Start/restart OTA system
cd /path/to/IdPass
python3 ota-update.py

# 4. Wait a few seconds, then check
ls /path/to/IdPass/main/test.txt
# File should be there!

# 5. Check deposit again
ls /path/to/IdPass/deposit/
# Should be empty (files moved to main/)
```

## Important Notes

- Updates are applied **on restart**, not immediately
- The `deposit/` folder should be **empty** during normal operation
- Files only appear in `deposit/` when an update is pending
- Check logs for detailed information about update process
- The OTA system runs continuously and monitors both `deposit/` and GitHub releases

