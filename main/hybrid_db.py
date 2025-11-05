"""
Hybrid Database System
Combines local SQLite database (for speed) with Firebase Firestore (for cloud storage)
- All operations are performed on local SQLite first (fast)
- BIDIRECTIONAL sync: Changes sync both ways between Firestore and local database
- Periodic sync runs every 10 minutes (configurable)
- Initial data is loaded from Firestore on startup
- Manual sync methods available for immediate synchronization
"""

import sqlite3
from datetime import datetime, time
import os
import csv
import json
import threading
import time as time_module
import random
from student_db import StudentDatabase, get_period_for_time
from firebase_db import FirebaseDatabase


class HybridDatabase(StudentDatabase):
    """Hybrid database that uses local SQLite as primary storage with Firebase Firestore sync"""
    
    def __init__(self, db_name="student_attendance.db", sync_interval_minutes=10):
        # Initialize local SQLite database
        super().__init__(db_name)
        
        # Initialize Firebase connection
        self.firebase_db = None
        self.sync_interval = sync_interval_minutes * 60  # Convert to seconds
        self.sync_thread = None
        self.sync_active = True
        self.last_sync = None
        self.periods = []  # Will be loaded from Firebase
        
        # Track changes that need to be synced
        self.pending_changes = {
            'students': set(),
            'attendance': set(), 
            'bathroom_breaks': set(),
            'nurse_visits': set()
        }
        self.changes_lock = threading.Lock()
        
        # Initialize sync system
        self.init_sync_system()
    
    def init_sync_system(self):
        """Initialize the Firebase Firestore sync system"""
        try:
            print("[HYBRID] Initializing Firebase Firestore connection...")
            self.firebase_db = FirebaseDatabase()
            print("[HYBRID] Firebase Firestore connection established")
            
            # Load periods from Firebase
            self.load_periods_from_firebase()
            
            # Perform initial sync from Firestore to local DB
            self.initial_sync_from_firestore()
            
            # Start the periodic sync thread
            self.start_sync_thread()
            
        except Exception as e:
            print(f"[HYBRID] Warning: Could not connect to Firebase Firestore: {e}")
            print("[HYBRID] Running in local-only mode")
    
    def load_periods_from_firebase(self):
        """Load school periods from Firebase Firestore"""
        if not self.firebase_db:
            return
        
        try:
            self.periods = self.firebase_db.get_periods()
            print(f"[HYBRID] Loaded {len(self.periods)} periods from Firebase")
        except Exception as e:
            print(f"[HYBRID] Error loading periods from Firebase: {e}")
            self.periods = []
    
    def get_periods(self):
        """Get the current periods configuration"""
        return self.periods if self.periods else []
    
    def initial_sync_from_firestore(self):
        """Load all data from Firebase Firestore into local SQLite database"""
        if not self.firebase_db:
            return
            
        try:
            print("[HYBRID] Starting initial sync from Firebase Firestore...")
            
            # Use the new sync methods for consistency
            self._sync_students_from_firestore()
            self._sync_attendance_from_firestore()
            self._sync_breaks_from_firestore()
            self._sync_nurse_visits_from_firestore()
            
            self.last_sync = datetime.now()
            print(f"[HYBRID] Initial sync completed at {self.last_sync}")
            
        except Exception as e:
            print(f"[HYBRID] Error during initial sync: {e}")
    
    def start_sync_thread(self):
        """Start the background sync thread"""
        if self.firebase_db:
            self.sync_thread = threading.Thread(target=self._sync_worker, daemon=True)
            self.sync_thread.start()
            print(f"[HYBRID] Sync thread started (interval: {self.sync_interval}s)")
    
    def _sync_worker(self):
        """Background worker that syncs changes bidirectionally"""
        while self.sync_active:
            try:
                time_module.sleep(self.sync_interval)
                if self.sync_active:
                    # First pull any new data from Firestore
                    self.sync_from_firestore()
                    # Then push any local changes to Firestore
                    self.sync_to_firestore()
            except Exception as e:
                print(f"[HYBRID] Sync worker error: {e}")
    
    def sync_from_firestore(self):
        """Sync new data from Firebase Firestore to local database"""
        if not self.firebase_db:
            return
            
        try:
            print("[HYBRID] Starting sync from Firebase Firestore...")
            
            # Sync new students from Firestore
            self._sync_students_from_firestore()
            
            # Sync today's attendance from Firestore
            self._sync_attendance_from_firestore()
            
            # Sync active bathroom breaks from Firestore
            self._sync_breaks_from_firestore()
            
            # Sync active nurse visits from Firestore
            self._sync_nurse_visits_from_firestore()
            
            print("[HYBRID] Sync from Firebase Firestore completed")
            
        except Exception as e:
            print(f"[HYBRID] Error during sync from Firebase Firestore: {e}")
    
    def _retry_with_backoff(self, func, max_retries=3):
        """Retry function with exponential backoff for API quota errors"""
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "Quota exceeded" in error_msg:
                    if attempt < max_retries - 1:
                        # Exponential backoff: wait 2^attempt + random seconds
                        wait_time = min((2 ** attempt) + random.uniform(0, 1), 64)
                        print(f"[HYBRID] API quota exceeded, waiting {wait_time:.1f}s before retry (attempt {attempt + 1}/{max_retries})")
                        time_module.sleep(wait_time)
                        continue
                    else:
                        print(f"[HYBRID] API quota exceeded after {max_retries} attempts, will retry later")
                        raise
                else:
                    # Not a quota error, re-raise immediately
                    raise
    
    def sync_to_firestore(self):
        """Sync pending changes to Firebase Firestore"""
        if not self.firebase_db:
            return
            
        with self.changes_lock:
            if not any(self.pending_changes.values()):
                return  # No logging for empty syncs to reduce noise
            
            print("[HYBRID] Starting sync to Firebase Firestore...")
            
            try:
                # Sync students changes
                if self.pending_changes['students']:
                    self._sync_students_to_firestore()
                
                # Sync attendance changes
                if self.pending_changes['attendance']:
                    self._sync_attendance_to_firestore()
                
                # Sync bathroom breaks changes
                if self.pending_changes['bathroom_breaks']:
                    self._sync_breaks_to_firestore()
                
                # Sync nurse visits changes
                if self.pending_changes['nurse_visits']:
                    self._sync_nurse_visits_to_firestore()
                
                # Clear pending changes
                for key in self.pending_changes:
                    self.pending_changes[key].clear()
                
                self.last_sync = datetime.now()
                print(f"[HYBRID] Sync to Firebase Firestore completed at {self.last_sync}")
                
            except Exception as e:
                print(f"[HYBRID] Error during sync to Firebase Firestore: {e}")
                print(f"[HYBRID] Local data is safe. Will retry later.")
    
    def _sync_students_from_firestore(self):
        """Sync students from Firebase Firestore to local database"""
        try:
            students_ref = self.firebase_db.db.collection('students').get()
            
            cursor = self.conn.cursor()
            synced_count = 0
            
            for doc in students_ref:
                data = doc.to_dict()
                nfc_uid = data.get('nfc_uid', '').strip()
                student_id = str(data.get('student_id', '')).strip()
                name = data.get('name', '').strip()
                created_at = data.get('created_at', '')
                
                # Convert Firestore timestamp to string if needed
                if hasattr(created_at, 'isoformat'):
                    created_at = created_at.isoformat()
                elif created_at and not isinstance(created_at, str):
                    created_at = str(created_at)
                
                if student_id and name:  # Only sync if we have required fields
                    try:
                        # Use document ID as primary key (which is nfc_uid or student_id)
                        primary_key = doc.id
                        
                        cursor.execute("""
                            INSERT OR REPLACE INTO students (id, student_id, name, created_at)
                            VALUES (?, ?, ?, ?)
                        """, (primary_key, student_id, name, created_at))
                        synced_count += 1
                    except Exception as e:
                        print(f"[HYBRID] Error syncing student {name}: {e}")
            
            self.conn.commit()
            print(f"[HYBRID] Synced {synced_count} students from Firebase Firestore")
            
        except Exception as e:
            print(f"[HYBRID] Error syncing students from Firebase Firestore: {e}")
    
    def _sync_attendance_from_firestore(self):
        """Sync today's attendance from Firebase Firestore to local database"""
        try:
            today = datetime.now().date().isoformat()
            attendance_ref = self.firebase_db.db.collection('attendance').where('date', '==', today).get()
            
            cursor = self.conn.cursor()
            
            for doc in attendance_ref:
                data = doc.to_dict()
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO attendance 
                        (student_uid, date, check_in, check_out, scheduled_check_out)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        data.get('student_uid', ''),
                        data.get('date', ''),
                        data.get('check_in', ''),
                        data.get('check_out', ''),
                        data.get('scheduled_check_out', '')
                    ))
                except Exception as e:
                    print(f"[HYBRID] Error syncing attendance record: {e}")
            
            self.conn.commit()
            print(f"[HYBRID] Synced attendance records from Firebase Firestore")
            
        except Exception as e:
            print(f"[HYBRID] Error syncing attendance from Firebase Firestore: {e}")
    
    def _sync_breaks_from_firestore(self):
        """Sync active bathroom breaks from Firebase Firestore to local database"""
        try:
            today = datetime.now().date().isoformat()
            breaks_ref = self.firebase_db.db.collection('bathroom_breaks').get()
            
            cursor = self.conn.cursor()
            
            for doc in breaks_ref:
                data = doc.to_dict()
                # Sync today's breaks or active breaks
                break_start = data.get('break_start', '')
                if break_start:
                    try:
                        break_date = datetime.fromisoformat(break_start).date().isoformat()
                        if break_date == today:
                            cursor.execute("""
                                INSERT OR REPLACE INTO bathroom_breaks 
                                (student_uid, break_start, break_end, duration_minutes)
                                VALUES (?, ?, ?, ?)
                            """, (
                                data.get('student_uid', ''),
                                data.get('break_start', ''),
                                data.get('break_end', ''),
                                data.get('duration_minutes', '')
                            ))
                    except Exception as e:
                        print(f"[HYBRID] Error syncing bathroom break: {e}")
            
            self.conn.commit()
            print(f"[HYBRID] Synced bathroom breaks from Firebase Firestore")
            
        except Exception as e:
            print(f"[HYBRID] Error syncing bathroom breaks from Firebase Firestore: {e}")
    
    def _sync_nurse_visits_from_firestore(self):
        """Sync active nurse visits from Firebase Firestore to local database"""
        try:
            today = datetime.now().date().isoformat()
            nurse_ref = self.firebase_db.db.collection('nurse_visits').get()
            
            cursor = self.conn.cursor()
            
            for doc in nurse_ref:
                data = doc.to_dict()
                # Sync today's visits or active visits
                visit_start = data.get('visit_start', '')
                if visit_start:
                    try:
                        visit_date = datetime.fromisoformat(visit_start).date().isoformat()
                        if visit_date == today:
                            cursor.execute("""
                                INSERT OR REPLACE INTO nurse_visits 
                                (student_uid, visit_start, visit_end, duration_minutes)
                                VALUES (?, ?, ?, ?)
                            """, (
                                data.get('student_uid', ''),
                                data.get('visit_start', ''),
                                data.get('visit_end', ''),
                                data.get('duration_minutes', '')
                            ))
                    except Exception as e:
                        print(f"[HYBRID] Error syncing nurse visit: {e}")
            
            self.conn.commit()
            print(f"[HYBRID] Synced nurse visits from Firebase Firestore")
            
        except Exception as e:
            print(f"[HYBRID] Error syncing nurse visits from Firebase Firestore: {e}")
    
    def _sync_students_to_firestore(self):
        """Sync student changes to Firebase Firestore"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, student_id, name, created_at FROM students")
        students = cursor.fetchall()
        
        students_ref = self.firebase_db.db.collection('students')
        
        for primary_key, student_id, name, created_at in students:
            # If primary key equals student_id, then there's no separate NFC_UID
            nfc_uid = primary_key if primary_key != student_id else ''
            
            student_data = {
                'nfc_uid': nfc_uid,
                'student_id': student_id,
                'name': name,
                'created_at': created_at
            }
            
            # Use primary key as document ID
            students_ref.document(primary_key).set(student_data)
        
        print(f"[HYBRID] Synced {len(students)} students to Firebase Firestore")
    
    def _sync_attendance_to_firestore(self):
        """Sync attendance changes to Firebase Firestore"""
        cursor = self.conn.cursor()
        today = datetime.now().date().isoformat()
        cursor.execute("""
            SELECT a.student_uid, s.name, a.date, a.check_in, a.check_out, a.scheduled_check_out
            FROM attendance a
            JOIN students s ON a.student_uid = s.id OR a.student_uid = s.student_id
            WHERE a.date = ?
        """, (today,))
        
        attendance_records = cursor.fetchall()
        
        if attendance_records:
            print(f"[HYBRID] Syncing {len(attendance_records)} attendance records to Firebase Firestore...")
            
            attendance_ref = self.firebase_db.db.collection('attendance')
            
            for student_uid, student_name, date, check_in, check_out, scheduled_check_out in attendance_records:
                attendance_data = {
                    'student_uid': student_uid,
                    'student_name': student_name,
                    'date': date,
                    'check_in': check_in or '',
                    'check_out': check_out or '',
                    'scheduled_check_out': scheduled_check_out or ''
                }
                
                # Use a composite key for the document ID to avoid duplicates
                doc_id = f"{student_uid}_{date}"
                attendance_ref.document(doc_id).set(attendance_data)
            
            print(f"[HYBRID] Completed sync of {len(attendance_records)} attendance records to Firebase Firestore")
    
    def _sync_breaks_to_firestore(self):
        """Sync bathroom breaks to Firebase Firestore"""
        cursor = self.conn.cursor()
        today = datetime.now().date().isoformat()
        cursor.execute("""
            SELECT b.id, b.student_uid, s.name, b.break_start, b.break_end, b.duration_minutes
            FROM bathroom_breaks b
            JOIN students s ON b.student_uid = s.id OR b.student_uid = s.student_id
            WHERE date(b.break_start) = ?
        """, (today,))
        
        breaks = cursor.fetchall()
        
        if breaks:
            breaks_ref = self.firebase_db.db.collection('bathroom_breaks')
            
            for break_id, student_uid, student_name, break_start, break_end, duration in breaks:
                break_data = {
                    'student_uid': student_uid,
                    'student_name': student_name,
                    'break_start': break_start or '',
                    'break_end': break_end or '',
                    'duration_minutes': duration or ''
                }
                
                # Use a composite key for the document ID
                doc_id = f"{student_uid}_{break_start}"
                breaks_ref.document(doc_id).set(break_data)
            
            print(f"[HYBRID] Synced {len(breaks)} bathroom breaks to Firebase Firestore")
    
    def _sync_nurse_visits_to_firestore(self):
        """Sync nurse visits to Firebase Firestore"""
        cursor = self.conn.cursor()
        today = datetime.now().date().isoformat()
        cursor.execute("""
            SELECT n.id, n.student_uid, s.name, n.visit_start, n.visit_end, n.duration_minutes
            FROM nurse_visits n
            JOIN students s ON n.student_uid = s.id OR n.student_uid = s.student_id
            WHERE date(n.visit_start) = ?
        """, (today,))
        
        visits = cursor.fetchall()
        
        if visits:
            nurse_ref = self.firebase_db.db.collection('nurse_visits')
            
            for visit_id, student_uid, student_name, visit_start, visit_end, duration in visits:
                visit_data = {
                    'student_uid': student_uid,
                    'student_name': student_name,
                    'visit_start': visit_start or '',
                    'visit_end': visit_end or '',
                    'duration_minutes': duration or ''
                }
                
                # Use a composite key for the document ID
                doc_id = f"{student_uid}_{visit_start}"
                nurse_ref.document(doc_id).set(visit_data)
            
            print(f"[HYBRID] Synced {len(visits)} nurse visits to Firebase Firestore")
    
    def _track_change(self, table, record_id=None):
        """Track a change that needs to be synced"""
        with self.changes_lock:
            if record_id:
                self.pending_changes[table].add(record_id)
            else:
                self.pending_changes[table].add('modified')
    
    # Override methods to track changes
    def add_student(self, nfc_uid, student_id, name):
        """Add a new student and track for sync"""
        result = super().add_student(nfc_uid, student_id, name)
        if result:
            self._track_change('students')
        return result
    
    def check_in(self, nfc_uid=None, student_id=None):
        """Record student check-in and track for sync"""
        result = super().check_in(nfc_uid, student_id)
        if result[0]:  # If successful
            self._track_change('attendance')
        return result
    
    def start_bathroom_break(self, identifier):
        """Start a bathroom break and track for sync (with auto-check-in)"""
        # Check if student is checked in, if not, auto-check-in first
        if not self.is_checked_in(identifier):
            print(f"[HYBRID] Student {identifier} not checked in, auto-checking in...")
            
            # Determine if identifier is NFC UID or student ID
            student_info = self.get_student_by_student_id(identifier)
            if student_info:
                # It's a student ID
                check_in_result = self.check_in(student_id=identifier)
            else:
                # Try as NFC UID
                student_info = self.get_student_by_uid(identifier)
                if student_info:
                    check_in_result = self.check_in(nfc_uid=identifier)
                else:
                    return False, "Student not found"
            
            if not check_in_result[0]:
                return False, f"Auto-check-in failed: {check_in_result[1]}"
            print(f"[HYBRID] Auto-check-in successful")
        
        result = super().start_bathroom_break(identifier)
        if result[0]:  # If successful
            self._track_change('bathroom_breaks')
        return result
    
    def end_bathroom_break(self, identifier):
        """End a bathroom break and track for sync"""
        result = super().end_bathroom_break(identifier)
        if result[0]:  # If successful
            self._track_change('bathroom_breaks')
        return result
    
    def start_nurse_visit(self, nfc_uid=None, student_id=None):
        """Start a nurse visit and track for sync (with auto-check-in)"""
        identifier = self.get_identifier(nfc_uid, student_id)
        if not identifier:
            return False, "No student identifier provided"
        
        # Check if student is checked in, if not, auto-check-in first
        if not self.is_checked_in(identifier):
            print(f"[HYBRID] Student {identifier} not checked in, auto-checking in...")
            
            # Use the provided parameters for check-in
            if nfc_uid:
                check_in_result = self.check_in(nfc_uid=nfc_uid)
            elif student_id:
                check_in_result = self.check_in(student_id=student_id)
            else:
                return False, "No student identifier provided"
            
            if not check_in_result[0]:
                return False, f"Auto-check-in failed: {check_in_result[1]}"
            print(f"[HYBRID] Auto-check-in successful")
        
        result = super().start_nurse_visit(nfc_uid, student_id)
        if result[0]:  # If successful
            self._track_change('nurse_visits')
        return result
    
    def end_nurse_visit(self, nfc_uid=None, student_id=None):
        """End a nurse visit and track for sync"""
        result = super().end_nurse_visit(nfc_uid, student_id)
        if result[0]:  # If successful
            self._track_change('nurse_visits')
        return result
    
    # Additional methods needed for compatibility with existing code
    def has_students_out(self):
        """Check if any students are currently out (bathroom break or nurse visit)"""
        cursor = self.conn.cursor()
        
        # Check for active bathroom breaks
        cursor.execute("SELECT id FROM bathroom_breaks WHERE break_end IS NULL LIMIT 1")
        if cursor.fetchone():
            return True
        
        # Check for active nurse visits
        cursor.execute("SELECT id FROM nurse_visits WHERE visit_end IS NULL LIMIT 1")
        if cursor.fetchone():
            return True
        
        return False

    def get_students_on_break(self):
        """Get list of students currently on bathroom break"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT s.id, s.student_id, s.name
            FROM bathroom_breaks b
            JOIN students s ON b.student_uid = s.id OR b.student_uid = s.student_id
            WHERE b.break_end IS NULL
        """)

        results = cursor.fetchall()
        return [(row[0], row[1], row[2]) for row in results]  # (nfc_uid, student_id, student_name)

    def get_students_without_nfc_uid(self):
        """Get list of students who don't have an NFC UID assigned"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT student_id, name FROM students WHERE id = '' OR id IS NULL")
        results = cursor.fetchall()
        
        return [
            {
                'student_id': student_id,
                'name': name,
                'row_number': i + 1  # Placeholder for compatibility
            }
            for i, (student_id, name) in enumerate(results)
        ]
    
    def link_nfc_card_to_student(self, nfc_uid, student_id):
        """Link an NFC card UID to a student"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE students SET id = ? WHERE student_id = ?",
                (nfc_uid, student_id)
            )
            
            if cursor.rowcount > 0:
                self.conn.commit()
                self._track_change('students')
                
                # Get student name for return message
                cursor.execute("SELECT name FROM students WHERE student_id = ?", (student_id,))
                result = cursor.fetchone()
                student_name = result[0] if result else "Unknown"
                
                print(f"[HYBRID] Linked NFC UID {nfc_uid} to student {student_name} (ID: {student_id})")
                return True, f"Card linked to {student_name}"
            else:
                return False, "Student not found"
                
        except Exception as e:
            print(f"[HYBRID] Error linking NFC card: {e}")
            return False, str(e)
    
    def force_sync(self):
        """Force an immediate bidirectional sync"""
        print("[HYBRID] Forcing immediate bidirectional sync...")
        self.sync_from_firestore()
        self.sync_to_firestore()
    
    def force_sync_from_firestore(self):
        """Force an immediate sync FROM Firebase Firestore to local database"""
        print("[HYBRID] Forcing immediate sync from Firebase Firestore...")
        self.sync_from_firestore()
    
    def force_sync_to_firestore(self):
        """Force an immediate sync TO Firebase Firestore from local database"""
        print("[HYBRID] Forcing immediate sync to Firebase Firestore...")
        self.sync_to_firestore()
    
    def get_sync_status(self):
        """Get sync status information"""
        with self.changes_lock:
            pending_count = sum(len(changes) for changes in self.pending_changes.values())
        
        return {
            'last_sync': self.last_sync,
            'pending_changes': pending_count,
            'pending_outbound_changes': pending_count,
            'firebase_connected': self.firebase_db is not None,
            'sync_interval_minutes': self.sync_interval / 60,
            'bidirectional_sync': True,
            'sync_direction': 'Both (Firebase Firestore ↔ Local Database)'
        }
    
    def auto_checkout_students(self):
        """Automatically check out students whose scheduled_check_out time has passed"""
        result = super().auto_checkout_students()
        # Track changes if any students were checked out
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM attendance WHERE date = date('now') AND check_out IS NOT NULL")
        if cursor.fetchone()[0] > 0:
            self._track_change('attendance')
        return result
    
    def clear_attendance_data(self):
        """Clear all attendance records from local database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM attendance")
            self.conn.commit()
            
            count = cursor.rowcount
            print(f"[HYBRID] Cleared {count} attendance records from local database")
            return True, f"Cleared {count} attendance records"
            
        except Exception as e:
            print(f"[HYBRID] Error clearing attendance data: {e}")
            return False, str(e)
    
    def clear_bathroom_breaks_data(self):
        """Clear all bathroom break records from local database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM bathroom_breaks")
            self.conn.commit()
            
            count = cursor.rowcount
            print(f"[HYBRID] Cleared {count} bathroom break records from local database")
            return True, f"Cleared {count} bathroom break records"
            
        except Exception as e:
            print(f"[HYBRID] Error clearing bathroom breaks data: {e}")
            return False, str(e)
    
    def clear_nurse_visits_data(self):
        """Clear all nurse visit records from local database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM nurse_visits")
            self.conn.commit()
            
            count = cursor.rowcount
            print(f"[HYBRID] Cleared {count} nurse visit records from local database")
            return True, f"Cleared {count} nurse visit records"
            
        except Exception as e:
            print(f"[HYBRID] Error clearing nurse visits data: {e}")
            return False, str(e)
    
    def clear_firestore_attendance(self):
        """Clear all attendance records from Firebase Firestore"""
        if not self.firebase_db:
            return False, "Firebase Firestore not connected"
            
        try:
            attendance_ref = self.firebase_db.db.collection('attendance')
            docs = attendance_ref.get()
            
            for doc in docs:
                doc.reference.delete()
            
            print("[HYBRID] Cleared Firebase Firestore attendance data")
            return True, "Firebase Firestore attendance cleared"
            
        except Exception as e:
            print(f"[HYBRID] Error clearing Firebase Firestore attendance: {e}")
            return False, str(e)
    
    def clear_firestore_bathroom_breaks(self):
        """Clear all bathroom break records from Firebase Firestore"""
        if not self.firebase_db:
            return False, "Firebase Firestore not connected"
            
        try:
            breaks_ref = self.firebase_db.db.collection('bathroom_breaks')
            docs = breaks_ref.get()
            
            for doc in docs:
                doc.reference.delete()
            
            print("[HYBRID] Cleared Firebase Firestore bathroom breaks data")
            return True, "Firebase Firestore bathroom breaks cleared"
            
        except Exception as e:
            print(f"[HYBRID] Error clearing Firebase Firestore bathroom breaks: {e}")
            return False, str(e)
    
    def clear_firestore_nurse_visits(self):
        """Clear all nurse visit records from Firebase Firestore"""
        if not self.firebase_db:
            return False, "Firebase Firestore not connected"
            
        try:
            nurse_ref = self.firebase_db.db.collection('nurse_visits')
            docs = nurse_ref.get()
            
            for doc in docs:
                doc.reference.delete()
            
            print("[HYBRID] Cleared Firebase Firestore nurse visits data")
            return True, "Firebase Firestore nurse visits cleared"
            
        except Exception as e:
            print(f"[HYBRID] Error clearing Firebase Firestore nurse visits: {e}")
            return False, str(e)
    
    def clear_all_activity_data(self, include_firestore=True):
        """Clear all attendance, bathroom breaks, and nurse visits (keeps students)"""
        print("[HYBRID] Clearing all activity data...")
        
        results = []
        
        if include_firestore and self.firebase_db:
            print("[HYBRID] Clearing Firebase Firestore data first...")
            
            # Clear Firestore first
            success, message = self.clear_firestore_attendance()
            results.append(f"Firebase Firestore Attendance: {message}")
            
            success, message = self.clear_firestore_bathroom_breaks()
            results.append(f"Firebase Firestore Bathroom breaks: {message}")
            
            success, message = self.clear_firestore_nurse_visits()
            results.append(f"Firebase Firestore Nurse visits: {message}")
        
        # Clear local database
        print("[HYBRID] Clearing local database...")
        
        # Clear attendance
        success, message = self.clear_attendance_data()
        results.append(f"Local Attendance: {message}")
        
        # Clear bathroom breaks
        success, message = self.clear_bathroom_breaks_data()
        results.append(f"Local Bathroom breaks: {message}")
        
        # Clear nurse visits
        success, message = self.clear_nurse_visits_data()
        results.append(f"Local Nurse visits: {message}")
        
        print("[HYBRID] Activity data clearing completed")
        return results
    
    def cleanup(self):
        """Clean up resources"""
        self.sync_active = False
        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=5)
        if hasattr(super(), '__del__'):
            super().__del__()


if __name__ == "__main__":
    # Test the hybrid database
    print("Testing Hybrid Database...")
    
    try:
        db = HybridDatabase(sync_interval_minutes=1)  # 1 minute for testing
        print("✅ Hybrid database initialized!")
        
        # Test adding a student
        success = db.add_student("TEST999", "888888", "Hybrid Test Student")
        if success:
            print("✅ Added test student to local database")
        
        # Test getting student
        student = db.get_student_by_uid("TEST999")
        if student:
            print(f"✅ Retrieved student from local database: {student}")
        
        # Test sync status
        status = db.get_sync_status()
        print(f"✅ Sync status: {status}")
        
        # Test bidirectional sync
        print("Testing bidirectional sync...")
        db.force_sync_from_firestore()
        print("✅ Force sync from Firebase Firestore completed")
        
        db.force_sync_to_firestore()
        print("✅ Force sync to Firebase Firestore completed")
        
        # Test full bidirectional sync
        db.force_sync()
        print("✅ Full bidirectional sync completed")
        
        print("🎉 Hybrid database system working!")
        
    except Exception as e:
        print(f"❌ Error testing hybrid database: {e}")
