# How to Create GitHub Releases for OTA Updates

This guide walks you through creating GitHub releases for your IdPass project to enable OTA updates.

## Prerequisites

1. **GitHub Repository**: You need a GitHub repository named `IdPass` under your account `jdrevnyak`
2. **Code Uploaded**: Your project code should be uploaded to the repository
3. **Git Installed**: Make sure Git is installed on your system

## Step-by-Step Release Creation

### Method 1: Using GitHub Web Interface (Recommended)

1. **Go to your repository**: https://github.com/jdrevnyak/IdPass

2. **Navigate to Releases**:
   - Click on the "Releases" link on the right side of the repository page
   - Or go directly to: https://github.com/jdrevnyak/IdPass/releases

3. **Create a New Release**:
   - Click "Create a new release" button
   - Or click "Draft a new release" if you want to save as draft first

4. **Fill in Release Details**:
   ```
   Tag version: v1.0.1
   Release title: Version 1.0.1 - Bug Fixes and Improvements
   Description: 
   ## What's New
   - Fixed NFC card reading issues
   - Improved database sync performance
   - Added new student management features
   - Enhanced error handling
   
   ## Bug Fixes
   - Resolved serial communication timeouts
   - Fixed GPIO LED control on startup
   - Corrected time zone handling
   ```

5. **Attach Files (Optional)**:
   - You can attach additional files like documentation, installers, etc.
   - The OTA system will download the source code automatically

6. **Publish Release**:
   - Click "Publish release" to make it live
   - Or "Save draft" to save for later

### Method 2: Using Git Command Line

1. **Update Version Number**:
   ```bash
   # Edit nfc_reader_gui.py and update the version
   # Change: current_version="1.0.0" to current_version="1.0.1"
   ```

2. **Commit Changes**:
   ```bash
   git add .
   git commit -m "Version 1.0.1 - Bug fixes and improvements"
   git push origin main
   ```

3. **Create and Push Tag**:
   ```bash
   git tag -a v1.0.1 -m "Release version 1.0.1"
   git push origin v1.0.1
   ```

4. **Create Release via GitHub CLI** (if installed):
   ```bash
   gh release create v1.0.1 --title "Version 1.0.1" --notes "Bug fixes and improvements"
   ```

## Version Numbering Best Practices

Use **Semantic Versioning** (SemVer) format: `MAJOR.MINOR.PATCH`

- **MAJOR** (1.0.0 → 2.0.0): Breaking changes, incompatible API changes
- **MINOR** (1.0.0 → 1.1.0): New features, backward compatible
- **PATCH** (1.0.0 → 1.0.1): Bug fixes, backward compatible

### Examples:
- `v1.0.0` - Initial release
- `v1.0.1` - Bug fixes
- `v1.1.0` - New features
- `v1.1.1` - More bug fixes
- `v2.0.0` - Major changes

## Release Checklist

Before creating each release:

- [ ] **Update version number** in `nfc_reader_gui.py`
- [ ] **Test the application** thoroughly
- [ ] **Update release notes** with changes
- [ ] **Commit all changes** to repository
- [ ] **Create release** with proper tag
- [ ] **Test OTA update** on a development system

## Testing Your Release

1. **Create a Test Release**:
   ```
   Tag: v1.0.1-test
   Title: Test Release
   Description: Testing OTA update system
   ```

2. **Test on Raspberry Pi**:
   ```bash
   # Run the application
   python3 nfc_reader_gui.py
   
   # The system will check for updates automatically
   # Or manually trigger: self.update_manager.check_for_updates(show_message=True)
   ```

3. **Verify Update Process**:
   - Check if update notification appears
   - Verify download and installation
   - Confirm application restarts properly
   - Check that important files are preserved

## Release Notes Template

Use this template for consistent release notes:

```markdown
## What's New in v1.0.1

### 🐛 Bug Fixes
- Fixed NFC card reading timeout issues
- Resolved GPIO LED control problems
- Corrected database sync errors

### ✨ New Features
- Added student search functionality
- Improved attendance reporting
- Enhanced error logging

### 🔧 Improvements
- Better performance during peak usage
- More responsive user interface
- Improved data validation

### 📝 Documentation
- Updated setup instructions
- Added troubleshooting guide
- Improved code comments

## Installation
This update will be automatically downloaded and installed when you restart the application.

## Breaking Changes
None in this release.

## Known Issues
- None currently known
```

## Troubleshooting Release Issues

### Release Not Detected
- Verify tag format: `v1.0.1` (with 'v' prefix)
- Check repository name and owner
- Ensure release is published (not draft)
- Verify internet connection on Raspberry Pi

### Update Download Fails
- Check GitHub repository permissions
- Verify release has source code attached
- Check disk space on Raspberry Pi
- Review update logs in `/home/jdrevnyak/id/logs/`

### Installation Fails
- Check file permissions
- Verify backup creation
- Review error messages in logs
- Test with manual update check

## Advanced Release Management

### Pre-release Testing
1. Create releases with `-beta` or `-rc` suffix
2. Test with limited devices first
3. Gather feedback before full release

### Staged Rollouts
1. Release to development devices first
2. Monitor for issues
3. Gradually roll out to production

### Rollback Strategy
1. Keep previous version available
2. Test rollback procedures
3. Document rollback steps

## Automation Options

### GitHub Actions (Advanced)
You can set up automated releases using GitHub Actions:

```yaml
name: Create Release
on:
  push:
    tags:
      - 'v*'
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Create Release
        uses: actions/create-release@v1
        with:
          tag_name: ${{ github.ref }}
          release_name: Release ${{ github.ref }}
          body: |
            Automated release for ${{ github.ref }}
          draft: false
          prerelease: false
```

This guide should help you create and manage releases effectively for your OTA update system!
