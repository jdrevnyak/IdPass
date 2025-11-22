#!/bin/bash
# Cleanup Script - Remove duplicate application files from root
# These files should only exist in main/ directory

echo "============================================"
echo "Cleaning up duplicate files from root"
echo "============================================"
echo ""

cd /home/jdrevnyak/id

# Application files that should ONLY be in main/
APP_FILES=(
    "nfc_reader_gui.py"
    "dialogs.py"
    "widgets.py"
    "overlays.py"
    "student_db.py"
    "firebase_db.py"
    "hybrid_db.py"
    "import_students_csv.py"
    "test.py"
    "updater.py"
)

echo "The following application files will be REMOVED from root:"
echo "(They will remain in main/ directory)"
echo ""

for file in "${APP_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  - $file"
    fi
done

echo ""
echo "Files that will STAY at root (infrastructure):"
echo "  - ota-update.py (OTA manager)"
echo "  - diagnose_ota.py (diagnostic tool)"
echo "  - prepare_release.py (release tool)"
echo "  - test_updater.py (OTA testing)"
echo "  - venv/ (virtual environment)"
echo "  - webapp/ (web interface)"
echo "  - All setup scripts and config files"
echo ""

# Create backup before removing
BACKUP_DIR="backup_root_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Creating backup in: $BACKUP_DIR"
echo ""

for file in "${APP_FILES[@]}"; do
    if [ -f "$file" ]; then
        cp "$file" "$BACKUP_DIR/"
        echo "Backed up: $file"
    fi
done

echo ""
read -p "Do you want to proceed with cleanup? (yes/no): " confirm

if [ "$confirm" = "yes" ]; then
    echo ""
    echo "Removing duplicate files from root..."
    for file in "${APP_FILES[@]}"; do
        if [ -f "$file" ]; then
            rm "$file"
            echo "  ✓ Removed: $file"
        fi
    done
    echo ""
    echo "✓ Cleanup complete!"
    echo "✓ Backup saved in: $BACKUP_DIR"
    echo ""
    echo "Your application files are now only in main/"
    echo "Run the app using: python ota-update.py"
else
    echo ""
    echo "Cleanup cancelled."
fi

echo ""
echo "============================================"

