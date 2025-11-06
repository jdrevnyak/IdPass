#!/usr/bin/env python3
"""
OTA Update Manager for ID Project

This script monitors a 'deposit' folder for new files and automatically updates
the 'main' folder, then restarts the application. This allows for over-the-air
updates without needing to stop the running application manually.

Based on: https://github.com/gruvw/python-ota-update
"""

import os
import sys
import shutil
import time
import subprocess
import requests
import zipfile
import json
from pathlib import Path
from datetime import datetime


class OTAUpdateManager:
    """Manages over-the-air updates for the application"""

    def __init__(self, project_root=None, github_repo_owner=None, github_repo_name=None, current_version=None):
        self.project_root = Path(project_root or Path(__file__).parent)
        self.deposit_dir = self.project_root / "deposit"
        self.main_dir = self.project_root / "main"
        self.logs_dir = self.project_root / "logs"
        self.main_script = self.main_dir / "main.py"

        # GitHub configuration
        self.github_repo_owner = github_repo_owner or "jackdrevnyak"  # Default values
        self.github_repo_name = github_repo_name or "IdPass"
        self.current_version = current_version or self._get_current_version()

        # Files to preserve during updates (won't be overwritten)
        self.preserve_files = [
            'student_attendance.db',
            'firebase-service-account.json',
            'requirements.txt',
            'main.py',  # Critical launcher file
            'version.txt'  # Version tracking file
        ]

        # Create necessary directories
        self._ensure_directories()

        # Create logger
        self.logger = self._create_logger()

    def _ensure_directories(self):
        """Ensure all necessary directories exist"""
        for dir_path in [self.deposit_dir, self.main_dir, self.logs_dir]:
            dir_path.mkdir(exist_ok=True)

    def _create_logger(self):
        """Create a simple logger"""
        log_file = self.logs_dir / f"logfile_{datetime.now().strftime('%d-%m-%Y_%H.%M.%S')}.log"

        def log(message, level="INFO"):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] [{level}] {message}"

            # Print to console
            print(log_entry)

            # Write to log file
            try:
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(log_entry + "\n")
            except Exception as e:
                print(f"[ERROR] Could not write to log file: {e}")

        return log

    def _get_current_version(self):
        """Get current version from version file or default"""
        version_file = self.main_dir / "version.txt"
        try:
            if version_file.exists():
                return version_file.read_text().strip()
        except Exception:
            pass
        return "1.0.0"  # Default version

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

    def check_github_releases(self):
        """Check for new releases on GitHub"""
        try:
            api_url = f"https://api.github.com/repos/{self.github_repo_owner}/{self.github_repo_name}/releases/latest"
            self.logger(f"Checking for updates from {api_url}")

            response = requests.get(api_url, timeout=10)
            response.raise_for_status()

            release_data = response.json()
            latest_version = release_data.get('tag_name', '').lstrip('v')

            self.logger(f"Current version: {self.current_version}")
            self.logger(f"Latest version: {latest_version}")

            if self._is_newer_version(latest_version, self.current_version):
                self.logger(f"Update available: {latest_version}")
                return release_data
            else:
                self.logger("No updates available")
                return None

        except Exception as e:
            self.logger(f"Error checking for GitHub releases: {e}", "ERROR")
            return None

    def download_release_to_deposit(self, release_data):
        """Download the latest release to the deposit directory"""
        try:
            # Clear deposit directory first
            self._clear_deposit()

            download_url = release_data.get('zipball_url')
            if not download_url:
                self.logger("No download URL found in release data", "ERROR")
                return False

            self.logger(f"Downloading release from {download_url}")

            # Download the zip file
            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()

            zip_path = self.deposit_dir / "release.zip"
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            self.logger("Extracting release files...")

            # Extract the zip file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Extract to a temporary directory first
                temp_extract_dir = self.deposit_dir / "temp_extract"
                temp_extract_dir.mkdir(exist_ok=True)
                zip_ref.extractall(temp_extract_dir)

            # Find the extracted directory (GitHub creates a directory with a hash)
            extracted_dirs = [d for d in temp_extract_dir.iterdir() if d.is_dir()]
            if not extracted_dirs:
                self.logger("No extracted directory found", "ERROR")
                return False

            source_dir = extracted_dirs[0]
            self.logger(f"Found source directory: {source_dir.name}")

            # IMPORTANT: Never use main/ subdirectory as source
            # The GitHub release should contain files at the root level
            # If there's a main/ subdirectory, it's a mistake in the repo structure
            main_subdir = source_dir / "main"
            if main_subdir.exists() and main_subdir.is_dir():
                self.logger(f"WARNING: Detected main/ subdirectory in release!", "WARN")
                self.logger(f"This indicates the GitHub repository has an incorrect structure.", "WARN")
                self.logger(f"The repository should have files at ROOT level, not in a main/ folder.", "WARN")
                self.logger(f"Ignoring the main/ subdirectory and using root-level files.", "WARN")

            # Move files from the extracted directory to deposit
            # Skip files that should be preserved locally
            files_copied = 0
            for item in source_dir.iterdir():
                if item.name in self.preserve_files:
                    self.logger(f"Skipping preserved file: {item.name}")
                    continue

                # CRITICAL: Skip the main/ subdirectory to prevent nesting
                # The main/ folder is a runtime directory and should never be in the release
                if item.name == 'main' and item.is_dir():
                    self.logger(f"Skipping main/ subdirectory (runtime directory, should not be in release)")
                    continue

                # Skip hidden files and system directories
                if item.name.startswith('.'):
                    self.logger(f"Skipping hidden file/directory: {item.name}")
                    continue

                dest_path = self.deposit_dir / item.name
                try:
                    if item.is_file():
                        shutil.copy2(item, dest_path)
                        files_copied += 1
                    elif item.is_dir():
                        if dest_path.exists():
                            shutil.rmtree(dest_path)
                        shutil.copytree(item, dest_path)
                        files_copied += 1
                except Exception as e:
                    self.logger(f"Error copying {item.name}: {e}", "ERROR")

            # Clean up
            shutil.rmtree(temp_extract_dir)
            zip_path.unlink()

            self.logger(f"Release downloaded and extracted to deposit directory ({files_copied} files copied)")
            return True

        except requests.exceptions.RequestException as e:
            self.logger(f"Network error downloading release: {e}", "ERROR")
            return False
        except zipfile.BadZipFile as e:
            self.logger(f"Invalid zip file: {e}", "ERROR")
            return False
        except Exception as e:
            self.logger(f"Error downloading release: {e}", "ERROR")
            return False

    def check_for_updates_and_download(self):
        """Check for updates and download if available"""
        self.logger("Checking for GitHub releases...")

        release_data = self.check_github_releases()
        if release_data:
            self.logger("New release found, downloading...")
            success = self.download_release_to_deposit(release_data)
            if success:
                self.logger("Update downloaded successfully!")
                return True
            else:
                self.logger("Failed to download update", "ERROR")
                return False
        else:
            self.logger("No updates available")
            return False

    def _copy_tree_preserve(self, src, dst):
        """Copy directory tree while preserving certain files"""
        for item in src.iterdir():
            if item.name.startswith('.'):  # Skip hidden files
                continue

            # CRITICAL: Never copy a 'main' directory into the main directory
            # This would create nested main/main/ structure
            if item.name == 'main' and item.is_dir():
                self.logger(f"WARNING: Skipping 'main/' directory to prevent nesting!", "WARN")
                self.logger(f"The 'main/' folder should not be in the deposit directory.", "WARN")
                continue

            dest_path = dst / item.name

            try:
                if item.is_file():
                    # Check if this file should be preserved
                    if item.name in self.preserve_files and dest_path.exists():
                        self.logger(f"Preserving existing file: {item.name}")
                        continue

                    shutil.copy2(item, dest_path)
                    self.logger(f"Copied file: {item.name}")

                elif item.is_dir():
                    if dest_path.exists():
                        # Directory exists, copy contents recursively
                        self._copy_tree_preserve(item, dest_path)
                    else:
                        # Directory doesn't exist, copy entire tree
                        shutil.copytree(item, dest_path)
                        self.logger(f"Copied directory: {item.name}")

            except Exception as e:
                self.logger(f"Error copying {item.name}: {e}", "ERROR")

    def _clear_deposit(self):
        """Clear all files from the deposit directory"""
        try:
            for item in self.deposit_dir.iterdir():
                try:
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                    self.logger(f"Cleared from deposit: {item.name}")
                except Exception as e:
                    self.logger(f"Error clearing {item.name}: {e}", "ERROR")
        except Exception as e:
            self.logger(f"Error clearing deposit directory: {e}", "ERROR")

    def _start_main_application(self):
        """Start the main application"""
        if not self.main_script.exists():
            raise Exception(f"No main.py found in {self.main_dir}")

        self.logger("Starting main application...")
        python_exe = sys.executable

        try:
            # Start the main application as a subprocess
            process = subprocess.Popen([python_exe, str(self.main_script)], cwd=str(self.main_dir))
            self.logger(f"Main application started with PID: {process.pid}")
            return process
        except Exception as e:
            self.logger(f"Failed to start main application: {e}", "ERROR")
            raise

    def check_for_updates(self):
        """Check if there are any files in the deposit directory"""
        try:
            items = list(self.deposit_dir.iterdir())
            # Filter out hidden files and directories
            items = [item for item in items if not item.name.startswith('.')]
            return len(items) > 0
        except Exception as e:
            self.logger(f"Error checking for updates: {e}", "ERROR")
            return False

    def apply_update(self):
        """Apply updates from deposit to main directory"""
        self.logger("Starting update process...")

        try:
            # Copy new files from deposit to main
            self._copy_tree_preserve(self.deposit_dir, self.main_dir)

            # Clear the deposit directory
            self._clear_deposit()

            self.logger("Update applied successfully!")
            return True

        except Exception as e:
            self.logger(f"Update failed: {e}", "ERROR")
            return False

    def run(self):
        """Main update loop"""
        self.logger("OTA Update Manager starting...")

        # Check if main.py exists in main directory
        if not self.main_script.exists():
            if self.check_for_updates():
                self.logger("No main.py found, initializing from deposit...")
                success = self.apply_update()
                if not success:
                    self.logger("Failed to initialize from deposit!", "ERROR")
                    sys.exit(1)
            else:
                self.logger("No main.py in main directory and no files in deposit!", "ERROR")
                self.logger("Please add your application files to the 'deposit' folder.", "ERROR")
                sys.exit(1)

        # Start the main application
        main_process = None
        try:
            main_process = self._start_main_application()
        except Exception as e:
            self.logger(f"Failed to start initial application: {e}", "ERROR")
            sys.exit(1)

        self.logger("Monitoring for updates...")

        # Track last GitHub check time
        last_github_check = 0
        GITHUB_CHECK_INTERVAL = 3600  # Check for GitHub releases every hour

        # Main monitoring loop
        while True:
            try:
                # Check if main process is still running
                if main_process.poll() is not None:
                    self.logger(f"Main application exited with code: {main_process.returncode}")

                    # If there are updates pending, apply them and restart
                    if self.check_for_updates():
                        self.logger("Updates detected, applying...")
                        if self.apply_update():
                            self.logger("Update applied, restarting application...")
                            main_process = self._start_main_application()
                        else:
                            self.logger("Update failed, keeping current version", "ERROR")
                            main_process = self._start_main_application()
                    else:
                        # No updates, just restart the application
                        self.logger("No updates, restarting application...")
                        main_process = self._start_main_application()

                # Check for GitHub releases periodically
                current_time = time.time()
                if current_time - last_github_check > GITHUB_CHECK_INTERVAL:
                    try:
                        update_found = self.check_for_updates_and_download()
                        if update_found:
                            self.logger("New version downloaded to deposit folder - will be applied on next restart")
                        last_github_check = current_time
                    except Exception as e:
                        self.logger(f"Error checking GitHub releases: {e}", "ERROR")

                # Check for updates every 2 seconds
                time.sleep(2)

            except KeyboardInterrupt:
                self.logger("Received shutdown signal")
                if main_process and main_process.poll() is None:
                    self.logger("Terminating main application...")
                    main_process.terminate()
                    try:
                        main_process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        main_process.kill()
                break

            except Exception as e:
                self.logger(f"Error in monitoring loop: {e}", "ERROR")
                time.sleep(5)  # Wait a bit before continuing

        self.logger("OTA Update Manager shutting down...")


def main():
    """Main entry point"""
    try:
        manager = OTAUpdateManager()
        manager.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
