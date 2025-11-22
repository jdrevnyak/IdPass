#!/usr/bin/env python3
"""
Import students from CSV file to Firebase Firestore

Usage:
    python import_students_csv.py path/to/students.csv
"""

import sys
import os
from firebase_db import FirebaseDatabase

def main():
    if len(sys.argv) < 2:
        print("Usage: python import_students_csv.py path/to/students.csv")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    
    if not os.path.exists(csv_file):
        print(f"Error: File not found: {csv_file}")
        sys.exit(1)
    
    print(f"Importing students from {csv_file}...")
    print("-" * 50)
    
    try:
        # Initialize Firebase database
        db = FirebaseDatabase()
        
        # Import from CSV
        results = db.import_from_csv(csv_file)
        
        # Display results
        print("\n" + "=" * 50)
        print("IMPORT COMPLETE")
        print("=" * 50)
        print(f"✅ Successfully imported: {results['success']} students")
        print(f"❌ Failed to import: {results['failed']} students")
        
        if results['errors']:
            print(f"\n⚠️  Errors ({len(results['errors'])}):")
            for error in results['errors'][:10]:
                print(f"  - {error}")
            if len(results['errors']) > 10:
                print(f"  ... and {len(results['errors']) - 10} more errors")
        
        print("\n" + "=" * 50)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

