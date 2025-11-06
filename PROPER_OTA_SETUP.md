# Proper OTA System Setup Guide

## Understanding the Architecture

Your system uses a **two-directory architecture** for safe OTA updates:

```
/home/jdrevnyak/id/
├── ota-update.py           # OTA Manager (infrastructure)
├── diagnose_ota.py         # Diagnostic tools
├── prepare_release.py      # Release tools
├── venv/                   # Python virtual environment
├── webapp/                 # Web interface (if separate)
├── deposit/                # Temporary OTA downloads
├── logs/                   # OTA logs
└── main/                   # Application runtime directory
    ├── main.py             # Application launcher
    ├── nfc_reader_gui.py   # Your main application
    ├── dialogs.py          # Application modules
    ├── widgets.py
    ├── overlays.py
    ├── student_db.py
    ├── firebase_db.py
    ├── hybrid_db.py
    └── ...                 # All other app files
```

## Why This Architecture?

1. **Clean separation** - OTA system is separate from application
2. **Safe updates** - Application can be updated without touching the updater
3. **Automatic management** - OTA monitors, downloads, applies updates, and restarts the app
4. **Rollback capability** - Can preserve files during updates

## Current Problem

You have **duplicate files** in both root and `main/` directories. This happened because:
1. OTA downloads created files in both locations
2. Files were committed to GitHub from root level
3. GitHub releases included duplicates

## How to Fix It

### Step 1: Clean Up Duplicates

Run the cleanup script:

```bash
cd /home/jdrevnyak/id
./cleanup_duplicates.sh
```

This will:
- ✅ Backup duplicate files (just in case)
- ✅ Remove application files from root
- ✅ Keep them only in `main/`
- ✅ Preserve infrastructure files at root

### Step 2: How to Run Your Application

**❌ DON'T run directly:**
```bash
python nfc_reader_gui.py  # This won't work after cleanup
```

**✅ DO run through OTA system:**
```bash
python ota-update.py      # This manages the app lifecycle
```

Or let your service handle it (already configured correctly):
```bash
sudo systemctl start nfc_reader.service
```

### Step 3: Clean Up GitHub Repository

Follow the steps in `GITHUB_REPO_CLEANUP.md`:

```bash
# Remove main/ from GitHub
git rm -r --cached main/

# Add .gitignore
git add .gitignore

# Commit changes
git commit -m "Remove main/ directory and duplicates from repository"

# Push to GitHub
git push origin main
```

## How OTA Updates Work

### Normal Operation:

1. **Startup:**
   ```bash
   python ota-update.py
   ```

2. **OTA Manager:**
   - Checks if updates are in `deposit/`
   - Applies any pending updates to `main/`
   - Launches `main/main.py` → runs `main/nfc_reader_gui.py`
   - Monitors for new updates every hour

3. **When Update Available:**
   - Downloads from GitHub → `deposit/`
   - Waits for app to restart
   - Applies update: `deposit/` → `main/`
   - Restarts application with new version

### Update Flow Diagram:

```
GitHub Release
      ↓
   Download
      ↓
  deposit/  ← [Temporary staging area]
      ↓
   Apply
      ↓
   main/    ← [Application runs from here]
      ↓
  Restart
```

## Testing After Cleanup

### 1. Test Manual Start:

```bash
cd /home/jdrevnyak/id
source venv/bin/activate
python ota-update.py
```

You should see:
- "OTA Update Manager starting..."
- "Starting main application..."
- Your NFC reader GUI launches

### 2. Test Service Start:

```bash
sudo systemctl restart nfc_reader.service
sudo systemctl status nfc_reader.service
journalctl -u nfc_reader.service -f
```

### 3. Test Update Process:

Create a test file in deposit:
```bash
echo "test" > deposit/test_update.txt
```

Restart the OTA manager - it should:
- Detect the file in deposit
- Copy it to main/
- Clear deposit/
- Restart the app

## Development Workflow

### Making Changes Locally:

**Option 1: Edit files in main/ directly**
```bash
nano main/nfc_reader_gui.py
# Test by restarting: python ota-update.py
```

**Option 2: Edit at root, then sync to GitHub**
```bash
# Create a separate dev directory
mkdir dev
# Edit files in dev/
# When ready, create a GitHub release
# OTA will download and apply to main/
```

### Creating a New Release:

1. **Update version and files at root** (for GitHub):
   ```bash
   nano nfc_reader_gui.py  # Make changes
   python prepare_release.py
   ```

2. **Commit and push:**
   ```bash
   git add *.py *.md
   git commit -m "New features"
   git push origin main
   ```

3. **Create GitHub release:**
   ```bash
   git tag -a v1.1.0 -m "Version 1.1.0"
   git push origin v1.1.0
   # Then create release on GitHub web interface
   ```

4. **OTA will auto-update** all devices running the app

## Troubleshooting

### Application won't start after cleanup:

```bash
# Check if files are in main/
ls -la main/

# Run with verbose output
python ota-update.py

# Check logs
ls -la logs/
cat logs/logfile_*.log
```

### Import errors:

The `main/main.py` file handles Python paths automatically. If you get import errors:
```bash
cd /home/jdrevnyak/id
export PYTHONPATH="/home/jdrevnyak/id:/home/jdrevnyak/id/main:$PYTHONPATH"
python ota-update.py
```

### Still have duplicates:

```bash
# Check for duplicates
diff nfc_reader_gui.py main/nfc_reader_gui.py

# If different, check which is newer
ls -l nfc_reader_gui.py main/nfc_reader_gui.py
```

## Quick Reference

### File Locations:

| File Type | Location | Example |
|-----------|----------|---------|
| OTA Infrastructure | Root | `ota-update.py` |
| Application Code | `main/` | `main/nfc_reader_gui.py` |
| Virtual Environment | Root | `venv/` |
| Temporary Downloads | `deposit/` | Auto-managed |
| Logs | `logs/` | Auto-managed |
| Database | `main/` | `main/student_attendance.db` |
| Credentials | `main/` | `main/firebase-service-account.json` |

### Common Commands:

```bash
# Start application (normal operation)
python ota-update.py

# Start application via service
sudo systemctl start nfc_reader.service

# Check service status
sudo systemctl status nfc_reader.service

# View logs
journalctl -u nfc_reader.service -f

# Diagnose OTA system
python diagnose_ota.py

# Prepare a new release
python prepare_release.py

# Test OTA update
python test_updater.py
```

## Summary

✅ **DO:**
- Run app via `python ota-update.py` or systemd service
- Keep application files only in `main/`
- Keep infrastructure files at root
- Commit only root-level files to GitHub (not `main/`)
- Create GitHub releases for OTA updates

❌ **DON'T:**
- Run `python nfc_reader_gui.py` directly from root
- Duplicate files in both root and `main/`
- Commit `main/`, `deposit/`, `logs/` to GitHub
- Edit files in `deposit/` (it gets cleared)

---

**Questions?** Check `GITHUB_REPO_CLEANUP.md` for repository cleanup details.

