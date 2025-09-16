"""
Hybrid Database System
Combines local SQLite database (for speed) with Google Sheets (for cloud storage)
- All operations are performed on local SQLite first (fast)
- BIDIRECTIONAL sync: Changes sync both ways between Google Sheets and local database
- Periodic sync runs every 10 minutes (configurable)
- Initial data is loaded from Google Sheets on startup
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
from gsheets_db import GoogleSheetsDatabase


class HybridDatabase(StudentDatabase):
    """Hybrid database that uses local SQLite as primary storage with Google Sheets sync"""
    
    def __init__(self, db_name="student_attendance.db", sync_interval_minutes=10):
        # Initialize local SQLite database
        super().__init__(db_name)
        
        # Initialize Google Sheets connection
        self.gsheets_db = None
        self.sync_interval = sync_interval_minutes * 60  # Convert to seconds
        self.sync_thread = None
        self.sync_active = True
        self.last_sync = None
        
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
        """Initialize the Google Sheets sync system"""
        try:
            print("[HYBRID] Initializing Google Sheets connection...")
            self.gsheets_db = GoogleSheetsDatabase()
            print("[HYBRID] Google Sheets connection established")
            
            # Perform initial sync from Google Sheets to local DB
            self.initial_sync_from_google_sheets()
            
            # Start the periodic sync thread
            self.start_sync_thread()
            
        except Exception as e:
            print(f"[HYBRID] Warning: Could not connect to Google Sheets: {e}")
            print("[HYBRID] Running in local-only mode")
    
    def initial_sync_from_google_sheets(self):
        """Load all data from Google Sheets into local SQLite database"""
        if not self.gsheets_db:
            return
            
        try:
            print("[HYBRID] Starting initial sync from Google Sheets...")
            
            # Use the new sync methods for consistency
            self._sync_students_from_sheets()
            self._sync_attendance_from_sheets()
            self._sync_breaks_from_sheets()
            self._sync_nurse_visits_from_sheets()
            
            self.last_sync = datetime.now()
            print(f"[HYBRID] Initial sync completed at {self.last_sync}")
            
        except Exception as e:
            print(f"[HYBRID] Error during initial sync: {e}")
    
    def start_sync_thread(self):
        """Start the background sync thread"""
        if self.gsheets_db:
            self.sync_thread = threading.Thread(target=self._sync_worker, daemon=True)
            self.sync_thread.start()
            print(f"[HYBRID] Sync thread started (interval: {self.sync_interval}s)")
    
    def _sync_worker(self):
        """Background worker that syncs changes bidirectionally"""
        while self.sync_active:
            try:
                time_module.sleep(self.sync_interval)
                if self.sync_active:
                    # First pull any new data from Google Sheets
                    self.sync_from_google_sheets()
                    # Then push any local changes to Google Sheets
                    self.sync_to_google_sheets()
            except Exception as e:
                print(f"[HYBRID] Sync worker error: {e}")
    
    def sync_from_google_sheets(self):
        """Sync new data from Google Sheets to local database"""
        if not self.gsheets_db:
            return
            
        try:
            print("[HYBRID] Starting sync from Google Sheets...")
            
            # Sync new students from Google Sheets
            self._sync_students_from_sheets()
            
            # Sync today's attendance from Google Sheets
            self._sync_attendance_from_sheets()
            
            # Sync active bathroom breaks from Google Sheets
            self._sync_breaks_from_sheets()
            
            # Sync active nurse visits from Google Sheets
            self._sync_nurse_visits_from_sheets()
            
            print("[HYBRID] Sync from Google Sheets completed")
            
        except Exception as e:
            print(f"[HYBRID] Error during sync from Google Sheets: {e}")
    
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
    
    def sync_to_google_sheets(self):
        """Sync pending changes to Google Sheets"""
        if not self.gsheets_db:
            return
            
        with self.changes_lock:
            if not any(self.pending_changes.values()):
                return  # No logging for empty syncs to reduce noise
            
            print("[HYBRID] Starting sync to Google Sheets...")
            
            try:
                # Sync students changes
                if self.pending_changes['students']:
                    self._sync_students_to_sheets()
                
                # Sync attendance changes
                if self.pending_changes['attendance']:
                    self._sync_attendance_to_sheets()
                
                # Sync bathroom breaks changes
                if self.pending_changes['bathroom_breaks']:
                    self._sync_breaks_to_sheets()
                
                # Sync nurse visits changes
                if self.pending_changes['nurse_visits']:
                    self._sync_nurse_visits_to_sheets()
                
                # Clear pending changes
                for key in self.pending_changes:
                    self.pending_changes[key].clear()
                
                self.last_sync = datetime.now()
                print(f"[HYBRID] Sync to Google Sheets completed at {self.last_sync}")
                
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "Quota exceeded" in error_msg:
                    print(f"[HYBRID] Google Sheets API quota exceeded. Local data is safe. Will retry later.")
                    # Don't clear pending changes so they can be retried later
                    return
                else:
                    print(f"[HYBRID] Error during sync to Google Sheets: {e}")
    
    def _sync_students_from_sheets(self):
        """Sync students from Google Sheets to local database"""
        try:
            students_ws = self.gsheets_db.spreadsheet.worksheet('Students')
            students = students_ws.get_all_records()
            
            cursor = self.conn.cursor()
            synced_count = 0
            
            for student in students:
                nfc_uid = student.get('NFC_UID', '').strip()
                student_id = str(student.get('Student_ID', '')).strip()
                name = student.get('Name', '').strip()
                created_at = student.get('Created_At', '')
                
                if student_id and name:  # Only sync if we have required fields
                    try:
                        # Use student_id as primary key if no NFC_UID
                        primary_key = nfc_uid if nfc_uid else student_id
                        
                        cursor.execute("""
                            INSERT OR REPLACE INTO students (id, student_id, name, created_at)
                            VALUES (?, ?, ?, ?)
                        """, (primary_key, student_id, name, created_at))
                        synced_count += 1
                    except Exception as e:
                        print(f"[HYBRID] Error syncing student {name}: {e}")
            
            self.conn.commit()
            print(f"[HYBRID] Synced {synced_count} students from Google Sheets")
            
        except Exception as e:
            print(f"[HYBRID] Error syncing students from Google Sheets: {e}")
    
    def _sync_attendance_from_sheets(self):
        """Sync today's attendance from Google Sheets to local database"""
        try:
            attendance_ws = self.gsheets_db.spreadsheet.worksheet('Attendance')
            attendance_records = attendance_ws.get_all_records()
            
            today = datetime.now().date().isoformat()
            cursor = self.conn.cursor()
            
            for record in attendance_records:
                if record.get('Date') == today:  # Only sync today's records
                    try:
                        cursor.execute("""
                            INSERT OR REPLACE INTO attendance 
                            (student_uid, date, check_in, check_out, scheduled_check_out)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            record.get('Student_UID', ''),
                            record.get('Date', ''),
                            record.get('Check_In', ''),
                            record.get('Check_Out', ''),
                            record.get('Scheduled_Check_Out', '')
                        ))
                    except Exception as e:
                        print(f"[HYBRID] Error syncing attendance record: {e}")
            
            self.conn.commit()
            print(f"[HYBRID] Synced attendance records from Google Sheets")
            
        except Exception as e:
            print(f"[HYBRID] Error syncing attendance from Google Sheets: {e}")
    
    def _sync_breaks_from_sheets(self):
        """Sync active bathroom breaks from Google Sheets to local database"""
        try:
            breaks_ws = self.gsheets_db.spreadsheet.worksheet('Bathroom_Breaks')
            breaks = breaks_ws.get_all_records()
            
            cursor = self.conn.cursor()
            today = datetime.now().date().isoformat()
            
            for break_record in breaks:
                # Sync today's breaks or active breaks
                break_start = break_record.get('Break_Start', '')
                if break_start:
                    break_date = datetime.fromisoformat(break_start).date().isoformat()
                    if break_date == today:
                        try:
                            cursor.execute("""
                                INSERT OR REPLACE INTO bathroom_breaks 
                                (student_uid, break_start, break_end, duration_minutes)
                                VALUES (?, ?, ?, ?)
                            """, (
                                break_record.get('Student_UID', ''),
                                break_record.get('Break_Start', ''),
                                break_record.get('Break_End', ''),
                                break_record.get('Duration_Minutes', '')
                            ))
                        except Exception as e:
                            print(f"[HYBRID] Error syncing bathroom break: {e}")
            
            self.conn.commit()
            print(f"[HYBRID] Synced bathroom breaks from Google Sheets")
            
        except Exception as e:
            print(f"[HYBRID] Error syncing bathroom breaks from Google Sheets: {e}")
    
    def _sync_nurse_visits_from_sheets(self):
        """Sync active nurse visits from Google Sheets to local database"""
        try:
            nurse_ws = self.gsheets_db.spreadsheet.worksheet('Nurse_Visits')
            visits = nurse_ws.get_all_records()
            
            cursor = self.conn.cursor()
            today = datetime.now().date().isoformat()
            
            for visit in visits:
                # Sync today's visits or active visits
                visit_start = visit.get('Visit_Start', '')
                if visit_start:
                    visit_date = datetime.fromisoformat(visit_start).date().isoformat()
                    if visit_date == today:
                        try:
                            cursor.execute("""
                                INSERT OR REPLACE INTO nurse_visits 
                                (student_uid, visit_start, visit_end, duration_minutes)
                                VALUES (?, ?, ?, ?)
                            """, (
                                visit.get('Student_UID', ''),
                                visit.get('Visit_Start', ''),
                                visit.get('Visit_End', ''),
                                visit.get('Duration_Minutes', '')
                            ))
                        except Exception as e:
                            print(f"[HYBRID] Error syncing nurse visit: {e}")
            
            self.conn.commit()
            print(f"[HYBRID] Synced nurse visits from Google Sheets")
            
        except Exception as e:
            print(f"[HYBRID] Error syncing nurse visits from Google Sheets: {e}")
    
    def _sync_students_to_sheets(self):
        """Sync student changes to Google Sheets"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, student_id, name, created_at FROM students")
        students = cursor.fetchall()
        
        students_ws = self.gsheets_db.spreadsheet.worksheet('Students')
        
        # Clear existing data and rewrite (simple approach)
        students_ws.clear()
        
        # Add header
        students_ws.update(values=[['NFC_UID', 'Student_ID', 'Name', 'Created_At']], range_name='A1:D1')
        
        # Add data - handle case where primary key might be student_id instead of NFC_UID
        if students:
            data = []
            for primary_key, student_id, name, created_at in students:
                # If primary key equals student_id, then there's no separate NFC_UID
                nfc_uid = primary_key if primary_key != student_id else ''
                data.append([nfc_uid, student_id, name, created_at])
            students_ws.update(values=data, range_name=f'A2:D{len(students)+1}')
        
        print(f"[HYBRID] Synced {len(students)} students to Google Sheets")
    
    def _sync_attendance_to_sheets(self):
        """Sync attendance changes to Google Sheets with bulk optimization"""
        cursor = self.conn.cursor()
        today = datetime.now().date().isoformat()
        cursor.execute("""
            SELECT s.student_id, s.name, a.date, a.check_in, a.check_out, a.scheduled_check_out
            FROM attendance a
            JOIN students s ON a.student_uid = s.id OR a.student_uid = s.student_id
            WHERE a.date = ?
        """, (today,))
        
        attendance_records = cursor.fetchall()
        
        if attendance_records:
            print(f"[HYBRID] Syncing {len(attendance_records)} attendance records to Google Sheets...")
            
            # For large datasets, use chunked bulk sync
            if len(attendance_records) > 100:
                self._bulk_sync_attendance(attendance_records, today)
            else:
                # For smaller datasets, use regular sync
                self._regular_sync_attendance(attendance_records)
        
        print(f"[HYBRID] Completed sync of {len(attendance_records)} attendance records")
    
    def _bulk_sync_attendance(self, attendance_records, today):
        """Sync large attendance datasets using chunked approach"""
        try:
            attendance_ws = self.gsheets_db.spreadsheet.worksheet('Attendance')
            
            # Clear today's data first (more efficient than checking duplicates)
            print(f"[HYBRID] Clearing existing attendance data for {today}...")
            self._clear_attendance_for_date(attendance_ws, today)
            
            # Get starting ID
            next_id = self.gsheets_db.get_next_id('Attendance')
            
            # Process in chunks to respect API limits
            chunk_size = 50  # Conservative chunk size
            total_chunks = (len(attendance_records) + chunk_size - 1) // chunk_size
            
            for chunk_idx in range(total_chunks):
                start_idx = chunk_idx * chunk_size
                end_idx = min(start_idx + chunk_size, len(attendance_records))
                chunk = attendance_records[start_idx:end_idx]
                
                print(f"[HYBRID] Processing chunk {chunk_idx + 1}/{total_chunks} ({len(chunk)} records)...")
                
                # Prepare batch data
                batch_data = []
                for record in chunk:
                    student_id, student_name, date, check_in, check_out, scheduled_check_out = record
                    new_row = [next_id, student_id, student_name, date, check_in, check_out or '', scheduled_check_out or '']
                    batch_data.append(new_row)
                    next_id += 1
                
                # Use retry with backoff for API calls
                def append_batch():
                    return attendance_ws.append_rows(batch_data)
                
                self._retry_with_backoff(append_batch)
                
                # Wait between chunks to respect rate limits (except for last chunk)
                if chunk_idx < total_chunks - 1:
                    print(f"[HYBRID] Waiting 65 seconds before next chunk to respect API limits...")
                    time_module.sleep(65)  # Slightly more than 1 minute to be safe
            
            print(f"[HYBRID] Bulk sync completed: {len(attendance_records)} records in {total_chunks} chunks")
            
        except Exception as e:
            print(f"[HYBRID] Error in bulk attendance sync: {e}")
            raise
    
    def _regular_sync_attendance(self, attendance_records):
        """Sync smaller attendance datasets using regular approach"""
        try:
            attendance_ws = self.gsheets_db.spreadsheet.worksheet('Attendance')
            
            # Get existing records to check for duplicates
            existing_records = attendance_ws.get_all_records()
            existing_keys = set()
            
            for record in existing_records:
                # Create unique key: student_id + date + check_in_time
                key = f"{record.get('Student_UID', '')}_{record.get('Date', '')}_{record.get('Check_In', '')}"
                existing_keys.add(key)
            
            next_id = self.gsheets_db.get_next_id('Attendance')
            
            # Prepare batch data, excluding duplicates
            batch_data = []
            skipped_count = 0
            
            for record in attendance_records:
                student_id, student_name, date, check_in, check_out, scheduled_check_out = record
                
                # Check if this record already exists
                record_key = f"{student_id}_{date}_{check_in}"
                if record_key in existing_keys:
                    skipped_count += 1
                    continue
                
                new_row = [next_id, student_id, student_name, date, check_in, check_out or '', scheduled_check_out or '']
                batch_data.append(new_row)
                next_id += 1
            
            # Only sync if we have new records
            if batch_data:
                def append_batch():
                    return attendance_ws.append_rows(batch_data)
                
                self._retry_with_backoff(append_batch)
                print(f"[HYBRID] Synced {len(batch_data)} new attendance records, skipped {skipped_count} duplicates")
            else:
                print(f"[HYBRID] No new attendance records to sync (skipped {skipped_count} duplicates)")
            
        except Exception as e:
            print(f"[HYBRID] Error in regular attendance sync: {e}")
            raise
    
    def _clear_attendance_for_date(self, attendance_ws, target_date):
        """Clear existing attendance records for a specific date"""
        try:
            all_records = attendance_ws.get_all_records()
            rows_to_delete = []
            
            for i, record in enumerate(all_records):
                if record.get('Date') == target_date:
                    rows_to_delete.append(i + 2)  # +2 for header and 0-based index
            
            # Delete rows in reverse order to maintain correct indices
            for row_num in sorted(rows_to_delete, reverse=True):
                attendance_ws.delete_rows(row_num)
                
            if rows_to_delete:
                print(f"[HYBRID] Cleared {len(rows_to_delete)} existing records for {target_date}")
                
        except Exception as e:
            print(f"[HYBRID] Warning: Could not clear existing data: {e}")
            # Continue anyway - duplicates are better than no data
    
    def _sync_breaks_to_sheets(self):
        """Sync bathroom breaks to Google Sheets"""
        cursor = self.conn.cursor()
        today = datetime.now().date().isoformat()
        cursor.execute("""
            SELECT s.student_id, s.name, b.break_start, b.break_end, b.duration_minutes
            FROM bathroom_breaks b
            JOIN students s ON b.student_uid = s.id OR b.student_uid = s.student_id
            WHERE date(b.break_start) = ?
        """, (today,))
        
        breaks = cursor.fetchall()
        
        if breaks:
            breaks_ws = self.gsheets_db.spreadsheet.worksheet('Bathroom_Breaks')
            
            # Get existing records to check for duplicates
            existing_records = breaks_ws.get_all_records()
            existing_keys = set()
            
            for record in existing_records:
                # Create unique key: student_id + break_start_time
                key = f"{record.get('Student_UID', '')}_{record.get('Break_Start', '')}"
                existing_keys.add(key)
            
            next_id = self.gsheets_db.get_next_id('Bathroom_Breaks')
            
            # Batch operations to reduce API calls and prevent duplicates
            batch_data = []
            skipped_count = 0
            
            for break_record in breaks[:10]:  # Limit to 10 records per sync to avoid quota
                student_id, student_name, break_start, break_end, duration = break_record
                
                # Check if this record already exists
                record_key = f"{student_id}_{break_start}"
                if record_key in existing_keys:
                    skipped_count += 1
                    continue
                
                new_row = [next_id, student_id, student_name, break_start, break_end or '', duration or '']
                batch_data.append(new_row)
                next_id += 1
            
            if batch_data:
                # Use batch append instead of individual append_row calls
                breaks_ws.append_rows(batch_data)
                print(f"[HYBRID] Synced {len(batch_data)} new bathroom break records, skipped {skipped_count} duplicates")
            else:
                print(f"[HYBRID] No new bathroom break records to sync (skipped {skipped_count} duplicates)")
        
        print(f"[HYBRID] Synced {len(breaks)} bathroom breaks to Google Sheets")
    
    def _sync_nurse_visits_to_sheets(self):
        """Sync nurse visits to Google Sheets"""
        cursor = self.conn.cursor()
        today = datetime.now().date().isoformat()
        cursor.execute("""
            SELECT s.student_id, s.name, n.visit_start, n.visit_end, n.duration_minutes
            FROM nurse_visits n
            JOIN students s ON n.student_uid = s.id OR n.student_uid = s.student_id
            WHERE date(n.visit_start) = ?
        """, (today,))
        
        visits = cursor.fetchall()
        
        if visits:
            nurse_ws = self.gsheets_db.spreadsheet.worksheet('Nurse_Visits')
            
            # Get existing records to check for duplicates
            existing_records = nurse_ws.get_all_records()
            existing_keys = set()
            
            for record in existing_records:
                # Create unique key: student_id + visit_start_time
                key = f"{record.get('Student_UID', '')}_{record.get('Visit_Start', '')}"
                existing_keys.add(key)
            
            next_id = self.gsheets_db.get_next_id('Nurse_Visits')
            
            # Prepare batch data, excluding duplicates
            batch_data = []
            skipped_count = 0
            
            for visit in visits:
                student_id, student_name, visit_start, visit_end, duration = visit
                
                # Check if this record already exists
                record_key = f"{student_id}_{visit_start}"
                if record_key in existing_keys:
                    skipped_count += 1
                    continue
                
                new_row = [next_id, student_id, student_name, visit_start, visit_end or '', duration or '']
                batch_data.append(new_row)
                next_id += 1
            
            if batch_data:
                nurse_ws.append_rows(batch_data)
                print(f"[HYBRID] Synced {len(batch_data)} new nurse visit records, skipped {skipped_count} duplicates")
            else:
                print(f"[HYBRID] No new nurse visit records to sync (skipped {skipped_count} duplicates)")
        
        print(f"[HYBRID] Completed nurse visits sync")
    
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
        self.sync_from_google_sheets()
        self.sync_to_google_sheets()
    
    def force_sync_from_sheets(self):
        """Force an immediate sync FROM Google Sheets to local database"""
        print("[HYBRID] Forcing immediate sync from Google Sheets...")
        self.sync_from_google_sheets()
    
    def force_sync_to_sheets(self):
        """Force an immediate sync TO Google Sheets from local database"""
        print("[HYBRID] Forcing immediate sync to Google Sheets...")
        self.sync_to_google_sheets()
    
    def force_bulk_attendance_sync(self):
        """Force a bulk sync of all attendance data (use carefully due to API limits)"""
        print("[HYBRID] Starting bulk attendance sync...")
        print("[HYBRID] WARNING: This may take 10+ minutes for large datasets")
        
        # Mark attendance for sync
        self._track_change('attendance')
        
        # Perform the sync
        try:
            self._sync_attendance_to_sheets()
            print("[HYBRID] Bulk attendance sync completed successfully")
        except Exception as e:
            print(f"[HYBRID] Bulk attendance sync failed: {e}")
            print("[HYBRID] You may need to wait for API quotas to reset and try again")
    
    def get_sync_status(self):
        """Get sync status information"""
        with self.changes_lock:
            pending_count = sum(len(changes) for changes in self.pending_changes.values())
        
        # Check if we have quota issues
        quota_warning = ""
        if pending_count > 0 and self.gsheets_db is not None:
            quota_warning = " (May be delayed due to API limits)"
        
        return {
            'last_sync': self.last_sync,
            'pending_changes': pending_count,  # Keep original key name for compatibility
            'pending_outbound_changes': pending_count,  # Also provide new descriptive name
            'google_sheets_connected': self.gsheets_db is not None,
            'sync_interval_minutes': self.sync_interval / 60,
            'bidirectional_sync': True,
            'sync_direction': 'Both (Google Sheets ↔ Local Database)',
            'quota_warning': quota_warning
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
    
    def clear_google_sheets_attendance(self):
        """Clear all attendance records from Google Sheets"""
        if not self.gsheets_db:
            return False, "Google Sheets not connected"
            
        try:
            attendance_ws = self.gsheets_db.spreadsheet.worksheet('Attendance')
            
            # Clear all data except header
            attendance_ws.clear()
            
            # Restore header
            header = ['ID', 'Student_UID', 'Student_Name', 'Date', 'Check_In', 'Check_Out', 'Scheduled_Check_Out']
            attendance_ws.update(values=[header], range_name='A1:G1')
            
            print("[HYBRID] Cleared Google Sheets attendance data")
            return True, "Google Sheets attendance cleared"
            
        except Exception as e:
            print(f"[HYBRID] Error clearing Google Sheets attendance: {e}")
            return False, str(e)
    
    def clear_google_sheets_bathroom_breaks(self):
        """Clear all bathroom break records from Google Sheets"""
        if not self.gsheets_db:
            return False, "Google Sheets not connected"
            
        try:
            breaks_ws = self.gsheets_db.spreadsheet.worksheet('Bathroom_Breaks')
            
            # Clear all data except header
            breaks_ws.clear()
            
            # Restore header
            header = ['ID', 'Student_UID', 'Student_Name', 'Break_Start', 'Break_End', 'Duration_Minutes']
            breaks_ws.update(values=[header], range_name='A1:F1')
            
            print("[HYBRID] Cleared Google Sheets bathroom breaks data")
            return True, "Google Sheets bathroom breaks cleared"
            
        except Exception as e:
            print(f"[HYBRID] Error clearing Google Sheets bathroom breaks: {e}")
            return False, str(e)
    
    def clear_google_sheets_nurse_visits(self):
        """Clear all nurse visit records from Google Sheets"""
        if not self.gsheets_db:
            return False, "Google Sheets not connected"
            
        try:
            nurse_ws = self.gsheets_db.spreadsheet.worksheet('Nurse_Visits')
            
            # Clear all data except header
            nurse_ws.clear()
            
            # Restore header
            header = ['ID', 'Student_UID', 'Student_Name', 'Visit_Start', 'Visit_End', 'Duration_Minutes']
            nurse_ws.update(values=[header], range_name='A1:F1')
            
            print("[HYBRID] Cleared Google Sheets nurse visits data")
            return True, "Google Sheets nurse visits cleared"
            
        except Exception as e:
            print(f"[HYBRID] Error clearing Google Sheets nurse visits: {e}")
            return False, str(e)
    
    def clear_all_activity_data(self, include_google_sheets=True):
        """Clear all attendance, bathroom breaks, and nurse visits (keeps students)"""
        print("[HYBRID] Clearing all activity data...")
        
        results = []
        
        if include_google_sheets and self.gsheets_db:
            print("[HYBRID] Clearing Google Sheets data first...")
            
            # Clear Google Sheets first
            success, message = self.clear_google_sheets_attendance()
            results.append(f"Google Sheets Attendance: {message}")
            
            success, message = self.clear_google_sheets_bathroom_breaks()
            results.append(f"Google Sheets Bathroom breaks: {message}")
            
            success, message = self.clear_google_sheets_nurse_visits()
            results.append(f"Google Sheets Nurse visits: {message}")
        
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
        db.force_sync_from_sheets()
        print("✅ Force sync from Google Sheets completed")
        
        db.force_sync_to_sheets()
        print("✅ Force sync to Google Sheets completed")
        
        # Test full bidirectional sync
        db.force_sync()
        print("✅ Full bidirectional sync completed")
        
        print("🎉 Hybrid database system working!")
        
    except Exception as e:
        print(f"❌ Error testing hybrid database: {e}")
