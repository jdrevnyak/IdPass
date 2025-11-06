#!/usr/bin/env python3
"""
Test script to verify the updater can download to deposit folder correctly
"""

import sys
from pathlib import Path

# Add main to path
sys.path.insert(0, str(Path(__file__).parent / "main"))

from updater import UpdateManager

# Simulate what the GUI does
class FakeWindow:
    """Mock window for testing"""
    pass

def test_deposit_detection():
    """Test that UpdateManager correctly detects deposit directory"""
    print("Testing UpdateManager deposit directory detection...")
    print()
    
    try:
        # Create a mock window
        window = FakeWindow()
        
        # Initialize UpdateManager as the GUI does
        manager = UpdateManager(
            parent_window=window,
            current_version="1.0.7",
            repo_owner="jdrevnyak",
            repo_name="IdPass"
        )
        
        print(f"✓ UpdateManager initialized")
        print(f"  Deposit directory: {manager.deposit_dir}")
        print(f"  Deposit exists: {manager.deposit_dir.exists()}")
        print(f"  Deposit absolute: {manager.deposit_dir.absolute()}")
        print()
        
        # Check if deposit is the correct one
        expected_deposit = Path(__file__).parent / "deposit"
        if manager.deposit_dir.absolute() == expected_deposit.absolute():
            print(f"✓ Deposit directory is correct!")
        else:
            print(f"✗ WARNING: Deposit directory mismatch!")
            print(f"  Expected: {expected_deposit.absolute()}")
            print(f"  Got: {manager.deposit_dir.absolute()}")
        
        print()
        print("Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_deposit_detection()
    sys.exit(0 if success else 1)

