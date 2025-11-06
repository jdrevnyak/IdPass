#!/usr/bin/env python3
"""
Release Preparation Script for IdPass Project

This script helps prepare releases by:
1. Updating version numbers
2. Creating release notes
3. Preparing files for GitHub release
"""

import os
import sys
import re
from datetime import datetime
from pathlib import Path

def get_current_version():
    """Get current version from nfc_reader_gui.py"""
    try:
        with open('nfc_reader_gui.py', 'r') as f:
            content = f.read()
            match = re.search(r'current_version="([^"]+)"', content)
            if match:
                return match.group(1)
    except FileNotFoundError:
        print("Error: nfc_reader_gui.py not found")
    return "1.0.0"

def update_version(new_version):
    """Update version in nfc_reader_gui.py"""
    try:
        with open('nfc_reader_gui.py', 'r') as f:
            content = f.read()
        
        # Update version
        content = re.sub(
            r'current_version="[^"]+"',
            f'current_version="{new_version}"',
            content
        )
        
        with open('nfc_reader_gui.py', 'w') as f:
            f.write(content)
        
        print(f"✅ Updated version to {new_version}")
        return True
    except Exception as e:
        print(f"❌ Error updating version: {e}")
        return False

def create_release_notes(version, changes):
    """Create release notes template"""
    release_date = datetime.now().strftime("%Y-%m-%d")
    
    notes = f"""# Release Notes for v{version}

**Release Date:** {release_date}

## What's New

### 🐛 Bug Fixes
- {changes.get('bugs', 'Various bug fixes and improvements')}

### ✨ New Features
- {changes.get('features', 'Enhanced functionality')}

### 🔧 Improvements
- {changes.get('improvements', 'Performance and stability improvements')}

### 📝 Documentation
- Updated setup and configuration guides
- Improved code documentation

## Installation
This update will be automatically downloaded and installed when you restart the application.

## Breaking Changes
None in this release.

## Known Issues
- None currently known

---
*This release was prepared using the IdPass release preparation script.*
"""
    
    # Save to file
    with open(f'RELEASE_NOTES_v{version}.md', 'w') as f:
        f.write(notes)
    
    print(f"✅ Created release notes: RELEASE_NOTES_v{version}.md")
    return notes

def main():
    print("🚀 IdPass Release Preparation Script")
    print("=" * 40)
    
    # Get current version
    current_version = get_current_version()
    print(f"Current version: {current_version}")
    
    # Get new version
    print("\nEnter new version number (e.g., 1.0.1, 1.1.0, 2.0.0):")
    new_version = input("New version: ").strip()
    
    if not new_version:
        print("❌ No version entered")
        return
    
    # Validate version format
    if not re.match(r'^\d+\.\d+\.\d+$', new_version):
        print("❌ Invalid version format. Use semantic versioning (e.g., 1.0.1)")
        return
    
    # Get changes
    print("\nEnter changes for this release:")
    changes = {}
    changes['bugs'] = input("Bug fixes (optional): ").strip() or "Various bug fixes and improvements"
    changes['features'] = input("New features (optional): ").strip() or "Enhanced functionality"
    changes['improvements'] = input("Improvements (optional): ").strip() or "Performance and stability improvements"
    
    # Update version
    if update_version(new_version):
        # Create release notes
        release_notes = create_release_notes(new_version, changes)
        
        print(f"\n✅ Release preparation complete!")
        print(f"📝 Version updated to: {new_version}")
        print(f"📄 Release notes created: RELEASE_NOTES_v{new_version}.md")
        
        print(f"\n📋 Next steps:")
        print(f"1. Review the updated nfc_reader_gui.py")
        print(f"2. Review RELEASE_NOTES_v{new_version}.md")
        print(f"3. Commit changes: git add . && git commit -m 'Version {new_version}'")
        print(f"4. Push to GitHub: git push origin main")
        print(f"5. Create release on GitHub:")
        print(f"   - Go to: https://github.com/jdrevnyak/IdPass/releases")
        print(f"   - Click 'Create a new release'")
        print(f"   - Tag: v{new_version}")
        print(f"   - Title: Version {new_version}")
        print(f"   - Copy content from RELEASE_NOTES_v{new_version}.md")
        print(f"   - Click 'Publish release'")
        
        print(f"\n🧪 Test the release:")
        print(f"1. Run: python3 nfc_reader_gui.py")
        print(f"2. Check if update notification appears")
        print(f"3. Test the update process")
        
    else:
        print("❌ Failed to update version")

if __name__ == "__main__":
    main()
