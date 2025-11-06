"""
OTA Update Manager for ID Project

This module handles automatic updates for the Python application running on Raspberry Pi.
It checks for updates from GitHub releases and downloads/installs them automatically.
"""

import os
import sys
import json
import shutil
import subprocess
import requests
import zipfile
from pathlib import Path
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import QMessageBox, QProgressDialog


class UpdateChecker(QThread):
    """Thread for checking updates without blocking the UI"""
    
    update_available = pyqtSignal(dict)  # Emits update info if available
    check_complete = pyqtSignal(bool)    # Emits True if update check completed successfully
    
    def __init__(self, current_version="1.0.0", repo_owner="your-username", repo_name="id-project"):
        super().__init__()
        self.current_version = current_version
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.github_api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
        
    def run(self):
        """Check for updates from GitHub releases"""
        try:
            print(f"[UPDATE] Checking for updates from {self.github_api_url}")
            response = requests.get(self.github_api_url, timeout=10)
            response.raise_for_status()
            
            release_data = response.json()
            latest_version = release_data.get('tag_name', '').lstrip('v')
            
            print(f"[UPDATE] Current version: {self.current_version}")
            print(f"[UPDATE] Latest version: {latest_version}")
            
            if self._is_newer_version(latest_version, self.current_version):
                update_info = {
                    'version': latest_version,
                    'download_url': release_data.get('zipball_url'),
                    'release_notes': release_data.get('body', ''),
                    'published_at': release_data.get('published_at', ''),
                    'assets': release_data.get('assets', [])
                }
                print(f"[UPDATE] Update available: {latest_version}")
                self.update_available.emit(update_info)
            else:
                print("[UPDATE] No updates available")
                
            self.check_complete.emit(True)
            
        except Exception as e:
            print(f"[UPDATE] Error checking for updates: {e}")
            self.check_complete.emit(False)
    
    def _is_newer_version(self, latest, current):
        """Compare version strings (simple semantic versioning)"""
        try:
            latest_parts = [int(x) for x in latest.split('.')]
            current_parts = [int(x) for x in current.split('.')]
            
            # Pad with zeros if different lengths
            max_len = max(len(latest_parts), len(current_parts))
            latest_parts.extend([0] * (max_len - len(latest_parts)))
            current_parts.extend([0] * (max_len - len(current_parts)))
            
            return latest_parts > current_parts
        except:
            return False


class UpdateDownloader(QThread):
    """Thread for downloading updates to the deposit folder"""
    
    progress_update = pyqtSignal(int)    # Download progress percentage
    status_update = pyqtSignal(str)     # Status message
    download_complete = pyqtSignal(bool) # True if successful
    
    def __init__(self, update_info, deposit_dir):
        super().__init__()
        self.update_info = update_info
        self.deposit_dir = Path(deposit_dir)
        self.temp_dir = Path("/tmp/id_update")
        
    def run(self):
        """Download update and extract to deposit folder"""
        try:
            self.status_update.emit("Starting update download...")
            
            # Clear deposit directory first
            if self.deposit_dir.exists():
                for item in self.deposit_dir.iterdir():
                    try:
                        if item.is_file():
                            item.unlink()
                        elif item.is_dir():
                            shutil.rmtree(item)
                    except Exception as e:
                        print(f"[UPDATE] Warning: Could not clear {item.name}: {e}")
            else:
                self.deposit_dir.mkdir(parents=True)
            
            # Create temp directory
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
            self.temp_dir.mkdir(parents=True)
            
            # Download the update
            download_url = self.update_info['download_url']
            zip_path = self.temp_dir / "update.zip"
            
            self.status_update.emit("Downloading update...")
            print(f"[UPDATE] Downloading from: {download_url}")
            response = requests.get(download_url, stream=True, timeout=60)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            self.progress_update.emit(progress)
            
            print(f"[UPDATE] Downloaded {downloaded} bytes")
            self.status_update.emit("Extracting update...")
            
            # Extract the update
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.temp_dir)
            
            # Find the extracted directory (GitHub creates a directory with commit hash)
            extracted_dirs = [d for d in self.temp_dir.iterdir() if d.is_dir()]
            if not extracted_dirs:
                raise Exception("No extracted directory found")
            
            source_dir = extracted_dirs[0]
            print(f"[UPDATE] Found source directory: {source_dir.name}")
            
            self.status_update.emit("Copying files to deposit folder...")
            
            # Copy files from extracted directory to deposit folder
            files_copied = 0
            for item in source_dir.iterdir():
                if item.name.startswith('.'):
                    continue  # Skip hidden files
                    
                dest_path = self.deposit_dir / item.name
                try:
                    if item.is_file():
                        shutil.copy2(item, dest_path)
                        files_copied += 1
                        print(f"[UPDATE] Copied file: {item.name}")
                    elif item.is_dir():
                        if dest_path.exists():
                            shutil.rmtree(dest_path)
                        shutil.copytree(item, dest_path)
                        files_copied += 1
                        print(f"[UPDATE] Copied directory: {item.name}")
                except Exception as e:
                    print(f"[UPDATE] Warning: Could not copy {item.name}: {e}")
            
            # Clean up temp directory
            shutil.rmtree(self.temp_dir)
            
            print(f"[UPDATE] Successfully copied {files_copied} items to deposit folder")
            self.status_update.emit(f"Update ready! {files_copied} files in deposit folder. Restart to apply.")
            self.download_complete.emit(True)
            
        except requests.exceptions.RequestException as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"[UPDATE] Network error: {e}")
            print(f"[UPDATE] Full error details:\n{error_details}")
            self.status_update.emit(f"Network error: {str(e)}")
            self.download_complete.emit(False)
        except zipfile.BadZipFile as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"[UPDATE] Invalid zip file: {e}")
            print(f"[UPDATE] Full error details:\n{error_details}")
            self.status_update.emit(f"Invalid update file: {str(e)}")
            self.download_complete.emit(False)
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"[UPDATE] Error during update: {e}")
            print(f"[UPDATE] Full error details:\n{error_details}")
            self.status_update.emit(f"Update failed: {str(e)}")
            self.download_complete.emit(False)


class UpdateManager:
    """Main update manager class"""
    
    def __init__(self, parent_window, current_version="1.0.0", repo_owner="your-username", repo_name="id-project", deposit_dir=None):
        self.parent_window = parent_window
        self.current_version = current_version
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.update_checker = None
        self.update_downloader = None
        self.progress_dialog = None
        
        # Detect deposit directory (should be ../deposit relative to main directory)
        if deposit_dir:
            self.deposit_dir = Path(deposit_dir)
        else:
            # Assume we're running from main/ directory, so deposit is ../deposit
            current_dir = Path(__file__).parent
            self.deposit_dir = current_dir.parent / "deposit"
        
        # Ensure deposit directory exists
        self.deposit_dir.mkdir(exist_ok=True)
        print(f"[UPDATE] Using deposit directory: {self.deposit_dir}")
        
        # Auto-check for updates on startup (every 24 hours) - DISABLED
        self.auto_check_timer = QTimer()
        self.auto_check_timer.timeout.connect(self.check_for_updates)
        # self.auto_check_timer.start(24 * 60 * 60 * 1000)  # 24 hours - DISABLED
        
        # Check for updates 30 seconds after startup - DISABLED
        # QTimer.singleShot(30000, self.check_for_updates)  # DISABLED
    
    def check_for_updates(self, show_message=True):
        """Check for updates from GitHub"""
        if self.update_checker and self.update_checker.isRunning():
            return
            
        self.update_checker = UpdateChecker(self.current_version, self.repo_owner, self.repo_name)
        self.update_checker.update_available.connect(self.on_update_available)
        self.update_checker.check_complete.connect(lambda success: self.on_check_complete(success, show_message))
        self.update_checker.start()
    
    def on_update_available(self, update_info):
        """Handle when an update is available"""
        version = update_info['version']
        release_notes = update_info['release_notes']
        
        msg = QMessageBox(self.parent_window)
        msg.setWindowTitle("Update Available")
        msg.setText(f"Version {version} is available!\n\nRelease Notes:\n{release_notes[:200]}...")
        msg.setInformativeText("Would you like to download and install this update?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.Yes)
        
        if msg.exec_() == QMessageBox.Yes:
            self.download_and_install_update(update_info)
    
    def on_check_complete(self, success, show_message):
        """Handle update check completion"""
        if not success and show_message:
            QMessageBox.warning(self.parent_window, "Update Check", 
                              "Failed to check for updates. Please check your internet connection.")
    
    def download_and_install_update(self, update_info):
        """Download update to deposit folder"""
        if self.update_downloader and self.update_downloader.isRunning():
            return
            
        # Create progress dialog
        self.progress_dialog = QProgressDialog("Downloading update...", "Cancel", 0, 100, self.parent_window)
        self.progress_dialog.setWindowTitle("Downloading Update")
        self.progress_dialog.setModal(True)
        self.progress_dialog.show()
        
        # Pass deposit directory to UpdateDownloader
        self.update_downloader = UpdateDownloader(update_info, self.deposit_dir)
        self.update_downloader.progress_update.connect(self.progress_dialog.setValue)
        self.update_downloader.status_update.connect(self.progress_dialog.setLabelText)
        self.update_downloader.download_complete.connect(self.on_update_complete)
        self.update_downloader.start()
    
    def on_update_complete(self, success):
        """Handle update completion"""
        self.progress_dialog.close()
        
        if success:
            msg = QMessageBox(self.parent_window)
            msg.setWindowTitle("Update Ready")
            msg.setText("The update has been downloaded successfully!")
            msg.setInformativeText(
                "Files have been placed in the deposit folder.\n\n"
                "The OTA update system will automatically apply them when you restart the application.\n\n"
                "You can restart now or wait until a convenient time."
            )
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
            
            # Don't restart automatically - let user restart when convenient
        else:
            QMessageBox.critical(self.parent_window, "Update Failed", 
                               "The update download failed. Please try again later or check your internet connection.")
    
    def restart_application(self):
        """Restart the application"""
        try:
            # Get the current script path
            script_path = sys.argv[0]
            python_executable = sys.executable
            
            # Start new instance
            subprocess.Popen([python_executable, script_path])
            
            # Close current instance
            self.parent_window.close()
            sys.exit(0)
            
        except Exception as e:
            print(f"[UPDATE] Error restarting application: {e}")
            QMessageBox.critical(self.parent_window, "Restart Error", 
                               "Please manually restart the application to apply updates.")


# Example usage in your main application
if __name__ == "__main__":
    # This would be integrated into your NFCReaderGUI class
    print("Update manager module loaded successfully")
