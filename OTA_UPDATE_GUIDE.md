# OTA Update Guide for ID Project

This guide explains how to set up and use Over-The-Air (OTA) updates for your ID student attendance system running on Raspberry Pi.

## Overview

The OTA update system provides automatic updates for the Python PyQt5 application running on Raspberry Pi, allowing you to deploy new features and bug fixes without physical access to the device.

## Python Application OTA Updates

### Features

- Automatic update checking every 24 hours
- GitHub releases integration
- Safe update installation with backup
- Preserves important files (database, credentials)
- User-friendly progress dialogs
- Automatic application restart after updates

### Setup Instructions

1. **Run the setup script:**
   ```bash
   ./setup_ota_updates.sh
   ```

2. **Configure GitHub repository:**
   - Create a GitHub repository for your project
   - Update `update_config.json` with your repository details:
     ```json
     {
         "repo_owner": "your-github-username",
         "repo_name": "your-repo-name"
     }
     ```

3. **Update version numbers:**
   - Increment the version in `nfc_reader_gui.py` for each release
   - Create GitHub releases with version tags (e.g., v1.0.1, v1.0.2)

### How It Works

1. **Update Checking:** The system automatically checks GitHub releases every 24 hours
2. **Download:** When an update is available, it downloads the latest release
3. **Backup:** Creates a backup of the current installation
4. **Install:** Installs new files while preserving important data
5. **Restart:** Automatically restarts the application

### Manual Update Check

You can manually check for updates by calling:
```python
self.update_manager.check_for_updates(show_message=True)
```


## Security Considerations

### Python Application Updates

- Updates are downloaded over HTTPS from GitHub
- Files are verified before installation
- Automatic backups prevent data loss
- Preserved files maintain system configuration
- Secure authentication with GitHub API

## Troubleshooting

### Python Application Issues

**Update check fails:**
- Verify internet connection
- Check GitHub repository URL and permissions
- Ensure the repository has releases

**Update installation fails:**
- Check disk space availability
- Verify file permissions
- Check logs in `/home/jdrevnyak/id/logs/`

**Application won't restart:**
- Manually restart the application
- Check for Python process conflicts


## Configuration Files

### update_config.json
```json
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
```


## Best Practices

1. **Version Management:**
   - Use semantic versioning (1.0.0, 1.0.1, 1.1.0)
   - Always increment version numbers
   - Document changes in release notes

2. **Testing:**
   - Test updates on a development system first
   - Create backups before major updates
   - Test rollback procedures

3. **Monitoring:**
   - Monitor update logs regularly
   - Set up alerts for failed updates
   - Track update success rates

4. **Security:**
   - Keep GitHub repository secure
   - Use strong authentication tokens
   - Regularly review update logs

## Advanced Features

### Custom Update Server

Instead of GitHub releases, you can set up your own update server:

1. Create a simple HTTP server
2. Host update files and version information
3. Modify the updater to use your server
4. Implement additional security measures

### Staged Rollouts

For production environments:

1. Deploy updates to a subset of devices first
2. Monitor for issues
3. Gradually roll out to all devices
4. Implement automatic rollback on failure

### Update Scheduling

Configure updates to occur during maintenance windows:

1. Modify the auto-check interval
2. Implement user-scheduled updates
3. Add maintenance mode functionality

## Support

For issues with the OTA update system:

1. Check the logs in `/home/jdrevnyak/id/logs/`
2. Verify network connectivity
3. Test with manual update checks
4. Review configuration files
5. Check GitHub repository permissions

The OTA update system is designed to be robust and user-friendly, focusing specifically on Raspberry Pi Python application updates. Proper configuration and testing are essential for reliable operation.
