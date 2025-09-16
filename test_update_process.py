#!/usr/bin/env python3
"""
Test script to debug the update process
"""

import os
import sys
import shutil
import zipfile
import requests
from pathlib import Path

def test_update_process():
    """Test the complete update process step by step"""
    
    print("🧪 Testing Update Process")
    print("=" * 40)
    
    # Get release info
    print("1. Getting release information...")
    try:
        url = 'https://api.github.com/repos/jdrevnyak/IdPass/releases/latest'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        release_data = response.json()
        
        latest_version = release_data.get('tag_name', '').lstrip('v')
        download_url = release_data.get('zipball_url')
        
        print(f"✅ Latest version: {latest_version}")
        print(f"✅ Download URL: {download_url}")
        
    except Exception as e:
        print(f"❌ Failed to get release info: {e}")
        return False
    
    # Test download
    print("\n2. Testing download...")
    try:
        response = requests.get(download_url, stream=True, timeout=30)
        response.raise_for_status()
        
        # Create temp directory
        temp_dir = Path("/tmp/id_update_test")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir()
        
        zip_path = temp_dir / "update.zip"
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        progress = int((downloaded / total_size) * 100)
                        if progress % 20 == 0:  # Print every 20%
                            print(f"   Download progress: {progress}%")
        
        print(f"✅ Download completed: {downloaded} bytes")
        print(f"✅ File saved to: {zip_path}")
        
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return False
    
    # Test extraction
    print("\n3. Testing extraction...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Find extracted directory
        extracted_dirs = [d for d in temp_dir.iterdir() if d.is_dir()]
        if not extracted_dirs:
            print("❌ No extracted directory found")
            return False
        
        source_dir = extracted_dirs[0]
        print(f"✅ Extracted to: {source_dir}")
        
        # List some files
        files = list(source_dir.rglob('*'))
        print(f"✅ Found {len(files)} files")
        print(f"   Sample files: {[f.name for f in files[:5]]}")
        
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        return False
    
    # Test file permissions
    print("\n4. Testing file permissions...")
    try:
        current_dir = Path("/home/jdrevnyak/id")
        print(f"✅ Current directory: {current_dir}")
        print(f"✅ Current directory exists: {current_dir.exists()}")
        print(f"✅ Current directory writable: {os.access(current_dir, os.W_OK)}")
        
        # Test creating a file
        test_file = current_dir / "test_write.tmp"
        test_file.write_text("test")
        test_file.unlink()
        print("✅ Can write to current directory")
        
    except Exception as e:
        print(f"❌ Permission test failed: {e}")
        return False
    
    # Test backup creation
    print("\n5. Testing backup creation...")
    try:
        backup_dir = current_dir.parent / f"id_backup_test"
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        
        # Test copying a few files
        test_files = ['requirements.txt', 'nfc_reader_gui.py']
        for file_name in test_files:
            src_file = current_dir / file_name
            if src_file.exists():
                backup_dir.mkdir(exist_ok=True)
                shutil.copy2(src_file, backup_dir / file_name)
                print(f"✅ Backed up: {file_name}")
        
        # Cleanup test backup
        shutil.rmtree(backup_dir)
        print("✅ Backup test completed")
        
    except Exception as e:
        print(f"❌ Backup test failed: {e}")
        return False
    
    # Cleanup
    print("\n6. Cleaning up...")
    try:
        shutil.rmtree(temp_dir)
        print("✅ Cleanup completed")
    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}")
    
    print("\n" + "=" * 40)
    print("🎉 Update process test completed successfully!")
    print("The issue might be in the GUI update process or error handling.")
    print("Check the application logs for more specific error messages.")
    
    return True

if __name__ == "__main__":
    test_update_process()
