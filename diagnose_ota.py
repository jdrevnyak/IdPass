#!/usr/bin/env python3
"""
Diagnostic script to check OTA update system configuration
"""

import sys
from pathlib import Path

def diagnose():
    print("="*60)
    print("OTA UPDATE SYSTEM DIAGNOSTIC")
    print("="*60)
    print()
    
    # Check Python
    print("1. PYTHON ENVIRONMENT")
    print(f"   Python executable: {sys.executable}")
    print(f"   Python version: {sys.version}")
    print()
    
    # Check if we're in venv
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    print(f"   Running in virtual environment: {in_venv}")
    if in_venv:
        print(f"   ✓ GOOD: Using virtual environment")
    else:
        print(f"   ⚠ WARNING: Not using virtual environment")
        print(f"      Run: source venv/bin/activate")
    print()
    
    # Check installed packages
    print("2. REQUIRED PACKAGES")
    required = ['serial', 'PyQt5', 'firebase_admin', 'requests']
    for pkg in required:
        try:
            __import__(pkg)
            print(f"   ✓ {pkg}: installed")
        except ImportError:
            print(f"   ✗ {pkg}: NOT INSTALLED")
    print()
    
    # Check file structure
    print("3. FILE STRUCTURE")
    project_root = Path.cwd()
    print(f"   Project root: {project_root}")
    
    main_dir = project_root / "main"
    print(f"   Main directory exists: {main_dir.exists()}")
    
    main_py = main_dir / "main.py"
    print(f"   main/main.py exists: {main_py.exists()}")
    
    version_file = main_dir / "version.txt"
    if version_file.exists():
        version = version_file.read_text().strip()
        print(f"   Current version: {version}")
    else:
        print(f"   version.txt: NOT FOUND")
    
    deposit_dir = project_root / "deposit"
    print(f"   Deposit directory exists: {deposit_dir.exists()}")
    
    if deposit_dir.exists():
        items = [item for item in deposit_dir.iterdir() if not item.name.startswith('.')]
        print(f"   Files in deposit: {len(items)}")
        for item in items:
            print(f"     - {item.name}")
    print()
    
    # Check OTA update script
    print("4. OTA UPDATE SCRIPT")
    ota_script = project_root / "ota-update.py"
    print(f"   ota-update.py exists: {ota_script.exists()}")
    print()
    
    # Check if ota-update.py can import
    print("5. OTA UPDATE SYSTEM TEST")
    try:
        sys.path.insert(0, str(project_root))
        import importlib.util
        spec = importlib.util.spec_from_file_location('ota_update', str(ota_script))
        ota_module = importlib.util.module_from_spec(spec)
        print(f"   ✓ ota-update.py can be loaded")
    except Exception as e:
        print(f"   ✗ ota-update.py cannot be loaded: {e}")
    print()
    
    print("="*60)
    print("RECOMMENDATIONS")
    print("="*60)
    
    if not in_venv:
        print("⚠ Activate virtual environment first:")
        print("   source venv/bin/activate")
        print()
    
    missing_pkgs = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing_pkgs.append(pkg)
    
    if missing_pkgs:
        print("⚠ Install missing packages:")
        print(f"   pip install pyserial PyQt5 firebase-admin requests")
        print()
    
    if deposit_dir.exists() and len([item for item in deposit_dir.iterdir() if not item.name.startswith('.')]) > 0:
        print("✓ Updates are waiting in deposit/")
        print("  Start ota-update.py to apply them:")
        print("  python ota-update.py")
        print()
    
    if not any([not in_venv, missing_pkgs]):
        print("✓ Everything looks good!")
        print("  You can start the OTA system:")
        print("  python ota-update.py")
    
    print("="*60)

if __name__ == "__main__":
    diagnose()

