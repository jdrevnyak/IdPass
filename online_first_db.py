"""
Online-First Database System
Uses Firebase Firestore as the primary database when online.
Falls back to local SQLite only when offline.
Syncs local changes to Firestore and clears local DB when connection is restored.
"""

import sqlite3
from datetime import datetime
import threading
import time
import socket
from student_db import StudentDatabase


class TimeoutError(Exception):
    """Custom timeout exception"""
    pass


def run_with_timeout(func, timeout_seconds):
    """Run a function with a timeout using threads"""
    result = [None]
    exception = [None]
    
    def worker():
        try:
            result[0] = func()
        except Exception as e:
            exception[0] = e
    
    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()
    thread.join(timeout_seconds)
    
    if thread.is_alive():
        # Thread is still running - timeout occurred
        raise TimeoutError(f"Operation timed out after {timeout_seconds} seconds")
    
    if exception[0]:
        raise exception[0]
    
    return result[0]


class OnlineFirstDatabase:
    """
    Online-first database that prioritizes Firebase Firestore.
    Only uses local SQLite when offline, and syncs back when online.
    """
    
    def __init__(self, db_name="student_attendance.db", connectivity_check_interval=30):
        self.db_name = db_name
        self.connectivity_check_interval = connectivity_check_interval
        
        # Initialize Firebase (primary)
        self.firebase_db = None
        self.local_db = None
        self.is_online = False
        self.mode = "unknown"  # "online", "offline", or "unknown"
        
        # Thread for checking connectivity
        self.check_thread = None
        self.check_active = True
        
        # Initialize system
        self.init_databases()
        self.start_connectivity_monitor()
    
    def init_databases(self):
        """Initialize Firebase and check initial connectivity"""
        print("[ONLINE-FIRST] Initializing database system...")
        
        # Check internet connectivity first (fast check)
        print("[ONLINE-FIRST] Checking internet connectivity...")
        has_internet = self.check_internet_connection(timeout=5)
        
        if not has_internet:
            # No internet - go straight to offline mode
            print("[ONLINE-FIRST] ⚠ No internet detected - Starting in offline mode")
            self.is_online = False
            self.mode = "offline"
            self.init_local_db()
            return
        
        # Has internet - try to initialize Firebase with timeout
        print("[ONLINE-FIRST] Internet detected - Initializing Firebase (10s timeout)...")
        firebase_initialized = False
        
        def init_firebase():
            from firebase_db import FirebaseDatabase
            return FirebaseDatabase()
        
        try:
            # Use timeout to prevent hanging
            self.firebase_db = run_with_timeout(init_firebase, 10)
            firebase_initialized = True
        except TimeoutError:
            print(f"[ONLINE-FIRST] ⚠ Firebase initialization timed out")
        except Exception as e:
            print(f"[ONLINE-FIRST] ⚠ Firebase initialization failed: {e}")
        
        if firebase_initialized:
            self.is_online = True
            self.mode = "online"
            print("[ONLINE-FIRST] ✓ Online mode - Using Firebase Firestore as primary database")
            
            # Check if there's existing offline data that needs syncing
            self._check_and_sync_offline_data_on_startup()
        else:
            print("[ONLINE-FIRST] Falling back to offline mode...")
            self.is_online = False
            self.mode = "offline"
            self.init_local_db()
    
    def init_local_db(self):
        """Initialize local SQLite database (only when needed)"""
        if self.local_db is None:
            print("[ONLINE-FIRST] Initializing local SQLite database...")
            self.local_db = StudentDatabase(self.db_name)
            print("[ONLINE-FIRST] ✓ Local database initialized")
            
            # If we have Firebase connection, try to sync students to local for offline use
            # This is a best-effort sync - won't fail if Firebase is unavailable
            if self.firebase_db:
                try:
                    print("[ONLINE-FIRST] Attempting to sync students for offline use...")
                    self._sync_students_to_local()
                except Exception as e:
                    print(f"[ONLINE-FIRST] Could not sync students (will use existing local data): {e}")
    
    def check_internet_connection(self, timeout=3):
        """Check if we have internet connectivity"""
        try:
            # Try to reach Google's DNS
            socket.create_connection(("8.8.8.8", 53), timeout=timeout)
            return True
        except OSError:
            pass
        
        # Try to reach Cloudflare's DNS as backup
        try:
            socket.create_connection(("1.1.1.1", 53), timeout=timeout)
            return True
        except OSError:
            return False
    
    def start_connectivity_monitor(self):
        """Start background thread to monitor connectivity"""
        self.check_thread = threading.Thread(target=self._connectivity_worker, daemon=True)
        self.check_thread.start()
        print(f"[ONLINE-FIRST] Connectivity monitor started (checking every {self.connectivity_check_interval}s)")
    
    def _connectivity_worker(self):
        """Background worker that monitors connectivity and handles transitions"""
        print(f"[ONLINE-FIRST] Connectivity worker thread started")
        
        while self.check_active:
            time.sleep(self.connectivity_check_interval)
            
            if not self.check_active:
                break
            
            print(f"[ONLINE-FIRST] Checking connectivity (was_online={self.is_online}, mode={self.mode})...")
            was_online = self.is_online
            currently_online = self.check_internet_connection()
            print(f"[ONLINE-FIRST] Connectivity check result: currently_online={currently_online}")
            
            if was_online != currently_online:
                self.is_online = currently_online
                
                if currently_online:
                    # We just came online!
                    print("[ONLINE-FIRST] ✓ Connection restored! Transitioning to online mode...")
                    self._transition_to_online()
                else:
                    # We just went offline
                    print("[ONLINE-FIRST] ⚠ Connection lost! Transitioning to offline mode...")
                    self._transition_to_offline()
            elif not was_online and self.mode == "offline":
                # We started offline but now have internet - sync any offline data
                if currently_online:
                    print("[ONLINE-FIRST] ✓ Internet detected while offline! Attempting to sync...")
                    self.is_online = True
                    self._transition_to_online()
        
        print("[ONLINE-FIRST] Connectivity worker thread stopped")
    
    def _transition_to_online(self):
        """Handle transition from offline to online mode"""
        # Initialize Firebase if not already done
        if self.firebase_db is None:
            print("[ONLINE-FIRST] Initializing Firebase connection...")
            
            def init_firebase():
                from firebase_db import FirebaseDatabase
                return FirebaseDatabase()
            
            try:
                self.firebase_db = run_with_timeout(init_firebase, 10)
                print("[ONLINE-FIRST] ✓ Firebase connected")
            except TimeoutError:
                print(f"[ONLINE-FIRST] ✗ Firebase initialization timed out")
                self.mode = "offline"
                return
            except Exception as e:
                print(f"[ONLINE-FIRST] ✗ Failed to initialize Firebase: {e}")
                self.mode = "offline"
                return
        
        self.mode = "online"
        
        # If we have local data, sync it to Firebase
        if self.local_db is not None:
            print("[ONLINE-FIRST] Checking for local changes to sync...")
            try:
                # Check if there's any data to sync
                cursor = self.local_db.conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM attendance")
                attendance_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM bathroom_breaks")
                breaks_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM nurse_visits")
                visits_count = cursor.fetchone()[0]
                
                if attendance_count > 0 or breaks_count > 0 or visits_count > 0:
                    print(f"[ONLINE-FIRST] Found offline data: {attendance_count} attendance, {breaks_count} breaks, {visits_count} visits")
                    print("[ONLINE-FIRST] Syncing local changes to Firebase...")
                    self._sync_local_to_firebase()
                    self._clear_local_database()
                    print("[ONLINE-FIRST] ✓ Local data synced and cleared")
                else:
                    print("[ONLINE-FIRST] No offline data to sync")
            except Exception as e:
                print(f"[ONLINE-FIRST] ✗ Error syncing local data: {e}")
                self.mode = "offline"  # Stay offline if sync failed
    
    def _check_and_sync_offline_data_on_startup(self):
        """Check if there's offline data when starting in online mode and sync it"""
        # Check if local DB file exists
        import os
        if not os.path.exists(self.db_name):
            print("[ONLINE-FIRST] No local database file found - no offline data to sync")
            return
        
        # Open local DB temporarily to check for data
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM attendance WHERE 1")
            attendance_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM bathroom_breaks WHERE 1")
            breaks_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM nurse_visits WHERE 1")
            visits_count = cursor.fetchone()[0]
            
            conn.close()
            
            if attendance_count > 0 or breaks_count > 0 or visits_count > 0:
                print(f"[ONLINE-FIRST] 🔍 Found existing offline data on startup!")
                print(f"[ONLINE-FIRST] Data: {attendance_count} attendance, {breaks_count} breaks, {visits_count} visits")
                print("[ONLINE-FIRST] Initializing local DB to sync data...")
                
                # Initialize local DB to access the data
                if self.local_db is None:
                    from student_db import StudentDatabase
                    self.local_db = StudentDatabase(self.db_name)
                
                # Sync to Firebase
                print("[ONLINE-FIRST] Syncing offline data to Firebase...")
                self._sync_local_to_firebase()
                self._clear_local_database()
                print("[ONLINE-FIRST] ✓ Startup sync completed")
            else:
                print("[ONLINE-FIRST] No offline data found on startup")
                
        except Exception as e:
            print(f"[ONLINE-FIRST] Could not check for offline data: {e}")
    
    def _transition_to_offline(self):
        """Handle transition from online to offline mode"""
        print("[ONLINE-FIRST] Transitioning to offline mode...")
        self.mode = "offline"
        self.init_local_db()
        print("[ONLINE-FIRST] ✓ Offline mode active - using local database")
    
    def _sync_local_to_firebase(self):
        """Sync all local SQLite data to Firebase Firestore"""
        if not self.local_db:
            return
        
        cursor = self.local_db.conn.cursor()
        
        # Sync attendance
        cursor.execute("""
            SELECT a.student_uid, s.name, a.date, a.check_in, a.check_out, a.scheduled_check_out
            FROM attendance a
            JOIN students s ON a.student_uid = s.id OR a.student_uid = s.student_id
        """)
        attendance_records = cursor.fetchall()
        
        for student_uid, student_name, date, check_in, check_out, scheduled_check_out in attendance_records:
            # Convert timestamps to ISO format
            check_in_iso = self._to_iso(check_in) if check_in else ''
            check_out_iso = self._to_iso(check_out) if check_out else ''
            scheduled_iso = self._to_iso(scheduled_check_out) if scheduled_check_out else ''
            
            attendance_data = {
                'student_uid': student_uid,
                'student_name': student_name,
                'date': date,
                'check_in': check_in_iso,
                'check_out': check_out_iso,
                'scheduled_check_out': scheduled_iso
            }
            
            doc_id = f"{student_uid}_{date}"
            self.firebase_db.db.collection('attendance').document(doc_id).set(attendance_data)
        
        print(f"[ONLINE-FIRST] Synced {len(attendance_records)} attendance records")
        
        # Sync bathroom breaks
        cursor.execute("""
            SELECT b.student_uid, s.name, b.break_start, b.break_end, b.duration_minutes
            FROM bathroom_breaks b
            JOIN students s ON b.student_uid = s.id OR b.student_uid = s.student_id
        """)
        breaks = cursor.fetchall()
        
        for student_uid, student_name, break_start, break_end, duration in breaks:
            start_iso = self._to_iso(break_start) if break_start else ''
            end_iso = self._to_iso(break_end) if break_end else None
            
            break_data = {
                'student_uid': student_uid,
                'student_name': student_name,
                'break_start': start_iso,
                'break_end': end_iso,
                'duration_minutes': duration
            }
            
            doc_id = f"{student_uid}_{start_iso}"
            self.firebase_db.db.collection('bathroom_breaks').document(doc_id).set(break_data)
        
        print(f"[ONLINE-FIRST] Synced {len(breaks)} bathroom breaks")
        
        # Sync nurse visits
        cursor.execute("""
            SELECT n.student_uid, s.name, n.visit_start, n.visit_end, n.duration_minutes
            FROM nurse_visits n
            JOIN students s ON n.student_uid = s.id OR n.student_uid = s.student_id
        """)
        visits = cursor.fetchall()
        
        for student_uid, student_name, visit_start, visit_end, duration in visits:
            start_iso = self._to_iso(visit_start) if visit_start else ''
            end_iso = self._to_iso(visit_end) if visit_end else None
            
            visit_data = {
                'student_uid': student_uid,
                'student_name': student_name,
                'visit_start': start_iso,
                'visit_end': end_iso,
                'duration_minutes': duration
            }
            
            doc_id = f"{student_uid}_{start_iso}"
            self.firebase_db.db.collection('nurse_visits').document(doc_id).set(visit_data)
        
        print(f"[ONLINE-FIRST] Synced {len(visits)} nurse visits")
    
    def _to_iso(self, timestamp):
        """Convert timestamp to ISO format"""
        if not timestamp:
            return ''
        
        try:
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace(' ', 'T'))
            else:
                dt = timestamp
            return dt.isoformat()
        except:
            return str(timestamp)
    
    def _sync_students_to_local(self):
        """Sync students from Firebase to local database for offline use"""
        if not self.firebase_db or not self.local_db:
            return
        
        try:
            students_ref = self.firebase_db.db.collection('students').get()
            cursor = self.local_db.conn.cursor()
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
                
                if student_id and name:
                    primary_key = doc.id
                    cursor.execute("""
                        INSERT OR REPLACE INTO students (id, student_id, name, created_at)
                        VALUES (?, ?, ?, ?)
                    """, (primary_key, student_id, name, created_at))
                    synced_count += 1
            
            self.local_db.conn.commit()
            print(f"[ONLINE-FIRST] Synced {synced_count} students to local database")
        except Exception as e:
            print(f"[ONLINE-FIRST] Error syncing students to local: {e}")
    
    def _clear_local_database(self):
        """Clear activity data from local SQLite database (keep students)"""
        if not self.local_db:
            return
        
        cursor = self.local_db.conn.cursor()
        cursor.execute("DELETE FROM attendance")
        cursor.execute("DELETE FROM bathroom_breaks")
        cursor.execute("DELETE FROM nurse_visits")
        # NOTE: We keep students in local DB - they'll be used again if we go offline
        self.local_db.conn.commit()
        print("[ONLINE-FIRST] Local activity data cleared (students retained)")
    
    # Proxy methods - delegate to appropriate database
    
    def add_student(self, nfc_uid, student_id, name):
        """Add student (always to Firebase, students are not stored locally in offline mode)"""
        if self.firebase_db:
            return self.firebase_db.add_student(nfc_uid, student_id, name)
        return False
    
    def get_student_by_uid(self, nfc_uid):
        """Get student by NFC UID"""
        if self.mode == "online" and self.firebase_db:
            return self.firebase_db.get_student_by_uid(nfc_uid)
        elif self.mode == "offline" and self.local_db:
            return self.local_db.get_student_by_uid(nfc_uid)
        return None
    
    def get_student_by_student_id(self, student_id):
        """Get student by student ID"""
        if self.mode == "online" and self.firebase_db:
            return self.firebase_db.get_student_by_student_id(student_id)
        elif self.mode == "offline" and self.local_db:
            return self.local_db.get_student_by_student_id(student_id)
        return None
    
    def check_in(self, nfc_uid=None, student_id=None):
        """Check in a student"""
        if self.mode == "online" and self.firebase_db:
            return self.firebase_db.check_in(nfc_uid, student_id)
        elif self.mode == "offline" and self.local_db:
            return self.local_db.check_in(nfc_uid, student_id)
        else:
            return False, "Database not available"
    
    def is_checked_in(self, identifier):
        """Check if student is checked in"""
        if self.mode == "online" and self.firebase_db:
            return self.firebase_db.is_checked_in(identifier)
        elif self.mode == "offline" and self.local_db:
            return self.local_db.is_checked_in(identifier)
        return False
    
    def is_on_break(self, identifier):
        """Check if student is on bathroom break"""
        if self.mode == "online" and self.firebase_db:
            return self.firebase_db.is_on_break(identifier)
        elif self.mode == "offline" and self.local_db:
            return self.local_db.is_on_break(identifier)
        return False
    
    def start_bathroom_break(self, identifier):
        """Start bathroom break"""
        if self.mode == "online" and self.firebase_db:
            return self.firebase_db.start_bathroom_break(identifier)
        elif self.mode == "offline" and self.local_db:
            return self.local_db.start_bathroom_break(identifier)
        else:
            return False, "Database not available"
    
    def end_bathroom_break(self, identifier):
        """End bathroom break"""
        if self.mode == "online" and self.firebase_db:
            return self.firebase_db.end_bathroom_break(identifier)
        elif self.mode == "offline" and self.local_db:
            return self.local_db.end_bathroom_break(identifier)
        else:
            return False, "Database not available"
    
    def is_at_nurse(self, identifier):
        """Check if student is at nurse"""
        if self.mode == "online" and self.firebase_db:
            return self.firebase_db.is_at_nurse(identifier)
        elif self.mode == "offline" and self.local_db:
            return self.local_db.is_at_nurse(identifier)
        return False
    
    def start_nurse_visit(self, nfc_uid=None, student_id=None):
        """Start nurse visit"""
        if self.mode == "online" and self.firebase_db:
            return self.firebase_db.start_nurse_visit(nfc_uid, student_id)
        elif self.mode == "offline" and self.local_db:
            return self.local_db.start_nurse_visit(nfc_uid, student_id)
        else:
            return False, "Database not available"
    
    def end_nurse_visit(self, nfc_uid=None, student_id=None):
        """End nurse visit"""
        if self.mode == "online" and self.firebase_db:
            return self.firebase_db.end_nurse_visit(nfc_uid, student_id)
        elif self.mode == "offline" and self.local_db:
            return self.local_db.end_nurse_visit(nfc_uid, student_id)
        else:
            return False, "Database not available"
    
    def has_students_out(self):
        """Check if any students are out"""
        if self.mode == "online" and self.firebase_db:
            return self.firebase_db.has_students_out()
        elif self.mode == "offline" and self.local_db:
            # Check both bathroom breaks and nurse visits in offline mode
            try:
                cursor = self.local_db.conn.cursor()
                
                # Check for active bathroom breaks
                cursor.execute("SELECT id FROM bathroom_breaks WHERE break_end IS NULL LIMIT 1")
                if cursor.fetchone():
                    return True
                
                # Check for active nurse visits
                cursor.execute("SELECT id FROM nurse_visits WHERE visit_end IS NULL LIMIT 1")
                if cursor.fetchone():
                    return True
                
                return False
            except Exception as e:
                print(f"[ONLINE-FIRST] Error checking students out: {e}")
                return False
        return False
    
    def get_periods(self):
        """Get school periods"""
        if self.firebase_db:
            return self.firebase_db.get_periods()
        return []
    
    def auto_checkout_students(self):
        """Auto-checkout students at period end"""
        if self.mode == "online" and self.firebase_db:
            return self.firebase_db.auto_checkout_students()
        elif self.mode == "offline" and self.local_db:
            return self.local_db.auto_checkout_students()
    
    def get_students_without_nfc_uid(self):
        """Get students without NFC UID"""
        if self.firebase_db:
            return self.firebase_db.get_students_without_nfc_uid()
        return []
    
    def link_nfc_card_to_student(self, nfc_uid, student_id):
        """Link NFC card to student"""
        if self.firebase_db:
            return self.firebase_db.link_nfc_card_to_student(nfc_uid, student_id)
        return False, "Firebase not available"
    
    def force_sync(self):
        """Force sync (only relevant if offline with local data)"""
        if self.mode == "offline" and self.local_db and self.check_internet_connection():
            print("[ONLINE-FIRST] Manual sync requested...")
            self._transition_to_online()
        elif self.mode == "online":
            print("[ONLINE-FIRST] Already online, no sync needed")
    
    def get_sync_status(self):
        """Get current database mode status"""
        return {
            'mode': self.mode,
            'is_online': self.is_online,
            'firebase_connected': self.firebase_db is not None,
            'local_db_active': self.local_db is not None,
            'description': 'Online (Firestore)' if self.mode == 'online' else 'Offline (Local SQLite)'
        }
    
    def cleanup(self):
        """Clean up resources"""
        self.check_active = False
        if self.check_thread and self.check_thread.is_alive():
            self.check_thread.join(timeout=5)
        if self.local_db:
            # Sync any remaining data before cleanup
            if self.is_online and self.firebase_db:
                try:
                    self._sync_local_to_firebase()
                except:
                    pass

