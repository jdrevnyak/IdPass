# GitHub Repository Structure Cleanup Guide

## Problem Overview

Your OTA update system was creating a nested `main/main/` directory because your GitHub repository contained both:
- Application files at the ROOT level (correct)
- A `main/` subdirectory with duplicate files (incorrect)

This guide will help you verify and fix your GitHub repository structure.

---

## Step 1: Verify Your GitHub Repository Structure

1. **Visit your GitHub repository:**
   ```
   https://github.com/jdrevnyak/IdPass
   ```

2. **Check the root directory:**
   - You should see files like: `nfc_reader_gui.py`, `ota-update.py`, `requirements.txt`, etc.
   - You should NOT see a `main/` subdirectory

3. **If you see a `main/` folder in the GitHub repository:**
   - This is causing the nesting issue
   - Follow the cleanup steps below

---

## Step 2: Clean Up GitHub Repository (Remove main/ folder)

### Option A: Using GitHub Web Interface (Easiest)

1. Go to your repository: https://github.com/jdrevnyak/IdPass

2. Navigate into the `main/` folder (if it exists)

3. For each file in the `main/` folder:
   - Click on the file
   - Click the trash icon (Delete this file)
   - Add commit message: "Remove duplicate file from main/ folder"
   - Click "Commit changes"

4. After all files are deleted, the `main/` folder will be automatically removed

### Option B: Using Git Command Line (Recommended)

```bash
# Navigate to your project directory
cd /home/jdrevnyak/id

# Make sure you're on the main branch
git checkout main

# Pull latest changes
git pull origin main

# Remove the main/ directory from Git (but keep it locally)
git rm -r --cached main/

# Commit the change
git commit -m "Remove main/ directory from repository (OTA runtime folder)"

# Push to GitHub
git push origin main
```

**Important:** The `--cached` flag removes the folder from Git tracking but keeps it on your local system, which is what you want since the OTA system needs the local `main/` folder to run.

---

## Step 3: Update Your Local Repository

The `.gitignore` file has been updated to prevent the `main/` folder from being committed again. The following directories are now ignored:

```gitignore
# OTA Update System - Runtime Directories
main/
deposit/
logs/
```

---

## Step 4: Verify the Fix

1. **Check Git status:**
   ```bash
   cd /home/jdrevnyak/id
   git status
   ```
   
   You should NOT see `main/` listed in changes to be committed.

2. **Check GitHub repository:**
   - Visit https://github.com/jdrevnyak/IdPass
   - Verify that the `main/` folder is no longer visible
   - Verify that your application files are still at the root level

3. **Create a test release:**
   ```bash
   # Create a git tag
   git tag -a v1.0.9-test -m "Test release after cleanup"
   git push origin v1.0.9-test
   ```

4. **Test the OTA update:**
   - The OTA system should now download updates correctly
   - No more nested `main/main/` directories should be created
   - Check the logs in `/home/jdrevnyak/id/logs/` for verification

---

## Step 5: Best Practices for Future Updates

### What TO Commit to GitHub:
✅ Application source files (`nfc_reader_gui.py`, `dialogs.py`, etc.)
✅ Configuration files (`requirements.txt`, `update_config.json`)
✅ Documentation files (`*.md`)
✅ Setup scripts (`setup_ota_updates.sh`, `autostart_nfc.sh`)
✅ OTA update script (`ota-update.py` - root level only)

### What NOT to Commit to GitHub:
❌ `main/` directory (runtime directory created by OTA system)
❌ `deposit/` directory (temporary OTA download folder)
❌ `logs/` directory (runtime logs)
❌ `venv/` directory (Python virtual environment)
❌ `*.db` files (local databases)
❌ `*-service-account.json` files (sensitive credentials)
❌ `__pycache__/` directories (Python cache)

All of these are now automatically ignored by the `.gitignore` file.

---

## How the OTA System Works (Corrected)

### Expected Directory Structure:

**GitHub Repository (jdrevnyak/IdPass):**
```
IdPass/
├── nfc_reader_gui.py
├── ota-update.py
├── dialogs.py
├── requirements.txt
└── ... (other application files)
```

**Local Raspberry Pi (/home/jdrevnyak/id):**
```
/home/jdrevnyak/id/
├── ota-update.py          # Update manager script
├── deposit/               # Temporary download folder (ignored by Git)
├── main/                  # Runtime application folder (ignored by Git)
│   ├── main.py           # Application launcher
│   ├── nfc_reader_gui.py
│   ├── dialogs.py
│   └── ... (application files)
└── logs/                  # Runtime logs (ignored by Git)
```

### Update Flow:

1. **Download:** OTA downloads release from GitHub → extracts to `deposit/`
2. **Validation:** OTA skips any `main/` folders found in the download
3. **Apply:** OTA copies files from `deposit/` → `main/`
4. **Cleanup:** OTA clears `deposit/` folder
5. **Restart:** Application restarts with updated files

---

## Troubleshooting

### Issue: `main/` folder still appears in `git status`

**Solution:**
```bash
# Make sure .gitignore is committed
git add .gitignore
git commit -m "Add .gitignore to prevent runtime folders from being committed"
git push origin main

# Remove main/ from Git tracking
git rm -r --cached main/
git commit -m "Remove main/ from Git tracking"
git push origin main
```

### Issue: After cleanup, OTA updates create `main/main/` again

**Possible causes:**
1. The updated `ota-update.py` files haven't been deployed to GitHub yet
2. You need to create a new release with the fixed code

**Solution:**
```bash
# Make sure the updated ota-update.py is committed
git add ota-update.py .gitignore
git commit -m "Fix OTA update nesting issue"
git push origin main

# Create a new release with the fix
git tag -a v1.0.10 -m "Fix OTA update main folder nesting"
git push origin v1.0.10

# Create the GitHub release via web interface
```

### Issue: Update shows warnings about main/ subdirectory in logs

This is expected if your GitHub repository still has the `main/` folder. The updated OTA system will now:
- **Log warnings** when it detects a `main/` folder in the download
- **Skip the main/ folder** automatically
- **Continue with the update** using root-level files

After you clean up the GitHub repository, these warnings will disappear.

---

## Verification Checklist

- [ ] GitHub repository has files at ROOT level only (no `main/` folder)
- [ ] `.gitignore` file exists and includes `main/`, `deposit/`, `logs/`
- [ ] `git status` does NOT show `main/` folder as changed
- [ ] Created a test release after cleanup
- [ ] Tested OTA update successfully
- [ ] No `main/main/` nested directories created
- [ ] OTA logs show no warnings about main/ subdirectory

---

## Need Help?

If you continue to experience issues:

1. Check the OTA logs: `ls -la /home/jdrevnyak/id/logs/`
2. Run the diagnostic script: `python3 diagnose_ota.py`
3. Verify your repository structure on GitHub
4. Ensure you've pushed all changes including `.gitignore`

---

**Last Updated:** Fix implemented - OTA update nesting issue resolved

