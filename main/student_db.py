import sqlite3
from datetime import datetime, time
import os
import csv
import json

PERIODS = [
    (1, time(7, 25), time(8, 8)),
    (2, time(8, 12), time(8, 55)),
    ('HR', time(8, 55), time(9, 1)),
    (3, time(9, 5), time(9, 48)),
    (4, time(9, 52), time(10, 35)),
    (5, time(10, 39), time(11, 22)),
    (6, time(11, 26), time(12, 9)),
    (7, time(12, 13), time(12, 56)),
    (8, time(13, 0), time(13, 43)),
    (9, time(13, 47), time(14, 30)),
]

def get_period_for_time(dt):
    t = dt.time()
    for period, start, end in PERIODS:
        if start <= t <= end:
            return period, end
    return None, None

class StudentDatabase:
    def __init__(self, db_name="student_attendance.db"):
        self.db_name = db_name
        self.conn = None
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        self.conn = sqlite3.connect(self.db_name)
        cursor = self.conn.cursor()
        
        # Create students table (id = NFC UID, student_id = school number)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id TEXT PRIMARY KEY,              -- NFC card UID
            student_id TEXT UNIQUE NOT NULL,  -- School 6-digit ID
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create attendance table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_uid TEXT,
            date DATE,
            check_in TIMESTAMP,
            check_out TIMESTAMP,
            scheduled_check_out TIMESTAMP,
            FOREIGN KEY (student_uid) REFERENCES students (id)
        )
        ''')
        
        # Create bathroom_breaks table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS bathroom_breaks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_uid TEXT,
            break_start TIMESTAMP,
            break_end TIMESTAMP,
            duration_minutes INTEGER,
            FOREIGN KEY (student_uid) REFERENCES students (id)
        )
        ''')
        
        # Create nurse_visits table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS nurse_visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_uid TEXT,
            visit_start TIMESTAMP,
            visit_end TIMESTAMP,
            duration_minutes INTEGER,
            FOREIGN KEY (student_uid) REFERENCES students (id)
        )
        ''')
        
        # Create water_visits table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS water_visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_uid TEXT,
            visit_start TIMESTAMP,
            visit_end TIMESTAMP,
            duration_minutes INTEGER,
            FOREIGN KEY (student_uid) REFERENCES students (id)
        )
        ''')
        
        self.conn.commit()
    
    def __del__(self):
        """Clean up database connection when object is destroyed"""
        if self.conn:
            self.conn.close()
    
    def add_student(self, nfc_uid, student_id, name):
        """Add a new student to the database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO students (id, student_id, name) VALUES (?, ?, ?)",
                (nfc_uid, student_id, name)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_student_by_uid(self, nfc_uid):
        """Get student information by NFC UID"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT student_id, name FROM students WHERE id = ?",
            (nfc_uid,)
        )
        result = cursor.fetchone()
        return result if result else None
    
    def get_student_by_student_id(self, student_id):
        """Get student information by school student_id"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, name FROM students WHERE student_id = ?",
            (student_id,)
        )
        result = cursor.fetchone()
        return result if result else None
    
    def get_identifier(self, nfc_uid=None, student_id=None):
        """Return the identifier to use for attendance/breaks: NFC UID if present, else student_id."""
        if nfc_uid:
            return nfc_uid
        elif student_id:
            return student_id
        else:
            return None

    def check_in(self, nfc_uid=None, student_id=None):
        """Record student check-in using a consistent identifier."""
        cursor = self.conn.cursor()
        today = datetime.now().date()
        current_time = datetime.now()
        identifier = self.get_identifier(nfc_uid, student_id)
        if not identifier:
            return False, "No student identifier provided"
        # Check if student exists
        if nfc_uid:
            cursor.execute("SELECT name FROM students WHERE id = ?", (nfc_uid,))
        else:
            cursor.execute("SELECT name FROM students WHERE student_id = ?", (student_id,))
        student = cursor.fetchone()
        if not student:
            return False, "Student not found in database"
        # Check if already checked in
        cursor.execute(
            "SELECT id FROM attendance WHERE student_uid = ? AND date = ?",
            (identifier, today)
        )
        if cursor.fetchone():
            return False, "Already checked in today"
        # Determine scheduled check-out time
        _, period_end = get_period_for_time(current_time)
        scheduled_check_out = None
        if period_end:
            scheduled_check_out = current_time.replace(hour=period_end.hour, minute=period_end.minute, second=0, microsecond=0)
        try:
            cursor.execute(
                "INSERT INTO attendance (student_uid, date, check_in, scheduled_check_out) VALUES (?, ?, ?, ?)",
                (identifier, today, current_time, scheduled_check_out if scheduled_check_out else None)
            )
            self.conn.commit()
            return True, "Checked in successfully"
        except Exception as e:
            return False, f"Error during check-in: {str(e)}"
    
    def is_checked_in(self, identifier):
        """Check if student is checked in today by identifier (NFC UID or student_id)"""
        cursor = self.conn.cursor()
        today = datetime.now().date()
        cursor.execute(
            "SELECT id FROM attendance WHERE student_uid = ? AND date = ?",
            (identifier, today)
        )
        result = cursor.fetchone()
        return result is not None
    
    def is_on_break(self, identifier):
        """Check if student is currently on a break by identifier (NFC UID or student_id)"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, break_start 
            FROM bathroom_breaks 
            WHERE student_uid = ? 
            AND break_end IS NULL
        """, (identifier,))
        result = cursor.fetchone()
        return result is not None
    
    def get_today_attendance(self):
        """Get today's attendance records"""
        cursor = self.conn.cursor()
        today = datetime.now().date()
        
        # Get all students and their attendance for today
        cursor.execute('''
        SELECT 
            s.student_id,
            s.name,
            a.check_in,
            a.check_out
        FROM students s
        LEFT JOIN attendance a ON s.student_id = a.student_id AND a.date = ?
        ORDER BY s.name
        ''', (today,))
        
        results = cursor.fetchall()
        
        # Convert string timestamps to datetime objects
        processed_results = []
        for student_id, name, check_in, check_out in results:
            try:
                # Try parsing with microseconds first
                check_in_dt = datetime.strptime(check_in, "%Y-%m-%d %H:%M:%S.%f") if check_in else None
                check_out_dt = datetime.strptime(check_out, "%Y-%m-%d %H:%M:%S.%f") if check_out else None
            except ValueError:
                try:
                    # If that fails, try without microseconds
                    check_in_dt = datetime.strptime(check_in, "%Y-%m-%d %H:%M:%S") if check_in else None
                    check_out_dt = datetime.strptime(check_out, "%Y-%m-%d %H:%M:%S") if check_out else None
                except (ValueError, TypeError) as e:
                    print(f"Error processing timestamps for student {name}: {e}")
                    check_in_dt = None
                    check_out_dt = None
            
            processed_results.append((student_id, name, check_in_dt, check_out_dt))
        
        return processed_results
    
    def check_out(self, student_id):
        """Record student check-out"""
        cursor = self.conn.cursor()
        today = datetime.now().date()
        current_time = datetime.now()
        
        # Check if student is checked in
        cursor.execute(
            "SELECT id FROM attendance WHERE student_id = ? AND date = ? AND check_out IS NULL",
            (student_id, today)
        )
        attendance = cursor.fetchone()
        if not attendance:
            return False, "Not checked in today"
        
        # Record check-out
        cursor.execute(
            "UPDATE attendance SET check_out = ? WHERE id = ?",
            (current_time, attendance[0])
        )
        self.conn.commit()
        return True, "Checked out successfully"
    
    def start_bathroom_break(self, identifier):
        """Start a bathroom break for a student by identifier (NFC UID or student_id)"""
        if not self.is_checked_in(identifier):
            return False, "Student is not checked in"
        try:
            cursor = self.conn.cursor()
            # Check if any student is currently on a break
            cursor.execute("""
                SELECT s.name 
                FROM bathroom_breaks b
                JOIN students s ON b.student_uid = s.id OR b.student_uid = s.student_id
                WHERE b.break_end IS NULL
            """)
            active_break = cursor.fetchone()
            if active_break:
                return False, f"Another student ({active_break[0]}) is already on a break"
            # Check if this student has an active break
            cursor.execute("""
                SELECT id FROM bathroom_breaks 
                WHERE student_uid = ? 
                AND break_end IS NULL
            """, (identifier,))
            if cursor.fetchone():
                return False, "Student is already on a break"
            # Start new break
            current_time = datetime.now()
            cursor.execute("""
                INSERT INTO bathroom_breaks (student_uid, break_start)
                VALUES (?, ?)
            """, (identifier, current_time))
            self.conn.commit()
            return True, "Break started"
        except Exception as e:
            self.conn.rollback()
            return False, str(e)
    
    def end_bathroom_break(self, identifier):
        """End a bathroom break for a student by identifier (NFC UID or student_id)"""
        print(f"[DB-DEBUG] end_bathroom_break called for identifier: {identifier}")
        try:
            cursor = self.conn.cursor()
            # Get the active break
            print(f"[DB-DEBUG] Querying for active break for {identifier}")
            cursor.execute("""
                SELECT id, break_start 
                FROM bathroom_breaks
                WHERE student_uid = ? 
                AND break_end IS NULL
            """, (identifier,))
            result = cursor.fetchone()
            print(f"[DB-DEBUG] Query result: {result}")
            
            if not result:
                print(f"[DB-DEBUG] No active break found for {identifier}")
                return False, "Student is not on a break"
                
            break_id, break_start = result
            break_end = datetime.now()
            print(f"[DB-DEBUG] Break ID: {break_id}, Start: {break_start}, End: {break_end}")
            
            # Calculate duration
            try:
                # Try parsing as string first (for old data)
                if isinstance(break_start, str):
                    print(f"[DB-DEBUG] break_start is string, parsing...")
                    try:
                        # Try ISO format first (with T separator)
                        start_dt = datetime.fromisoformat(break_start)
                        print(f"[DB-DEBUG] Parsed using fromisoformat")
                    except ValueError:
                        try:
                            # Try with microseconds
                            start_dt = datetime.strptime(break_start, "%Y-%m-%d %H:%M:%S.%f")
                            print(f"[DB-DEBUG] Parsed using strptime with microseconds")
                        except ValueError:
                            # Try without microseconds
                            start_dt = datetime.strptime(break_start, "%Y-%m-%d %H:%M:%S")
                            print(f"[DB-DEBUG] Parsed using strptime without microseconds")
                else:
                    # Already a datetime object
                    print(f"[DB-DEBUG] break_start is datetime object")
                    start_dt = break_start
            except Exception as e:
                print(f"[DB-DEBUG] Error parsing break_start: {e}")
                start_dt = break_end  # Fallback to avoid errors
            
            duration = int((break_end - start_dt).total_seconds() / 60)
            print(f"[DB-DEBUG] Calculated duration: {duration} minutes")
            print(f"[DB-DEBUG] Updating bathroom_breaks set break_end={break_end}, duration={duration} where id={break_id}")
            
            cursor.execute("""
                UPDATE bathroom_breaks
                SET break_end = ?, duration_minutes = ?
                WHERE id = ?
            """, (break_end, duration, break_id))
            
            rows_affected = cursor.rowcount
            print(f"[DB-DEBUG] UPDATE affected {rows_affected} rows")
            
            self.conn.commit()
            print(f"[DB-DEBUG] Commit successful")
            
            # Verify the update
            cursor.execute("""
                SELECT break_end, duration_minutes 
                FROM bathroom_breaks 
                WHERE id = ?
            """, (break_id,))
            verify_result = cursor.fetchone()
            print(f"[DB-DEBUG] Verification query result: {verify_result}")
            
            return True, "Break ended"
        except Exception as e:
            print(f"[DB-DEBUG] Exception in end_bathroom_break: {e}")
            self.conn.rollback()
            return False, str(e)
    
    def get_today_breaks(self):
        """Get all bathroom breaks for today"""
        cursor = self.conn.cursor()
        today = datetime.now().date()
        
        # Debug: Print the current date we're searching for
        print(f"Searching for breaks on date: {today}")
        
        cursor.execute("""
            SELECT s.student_id, b.break_start, b.break_end, b.duration_minutes
            FROM bathroom_breaks b
            JOIN students s ON b.student_id = s.student_id
            WHERE date(b.break_start) = ?
            ORDER BY b.break_start DESC
        """, (today.strftime("%Y-%m-%d"),))
        
        results = cursor.fetchall()
        print(f"Found {len(results)} breaks for today")  # Debug log
        
        # Debug: Print raw results
        for result in results:
            print(f"Raw break data: {result}")
        
        # Convert string timestamps to datetime objects
        formatted_results = []
        for student_id, start, end, duration in results:
            try:
                # Try parsing with microseconds first
                start_dt = datetime.strptime(start, "%Y-%m-%d %H:%M:%S.%f") if start else None
                end_dt = datetime.strptime(end, "%Y-%m-%d %H:%M:%S.%f") if end else None
            except ValueError:
                try:
                    # If that fails, try without microseconds
                    start_dt = datetime.strptime(start, "%Y-%m-%d %H:%M:%S") if start else None
                    end_dt = datetime.strptime(end, "%Y-%m-%d %H:%M:%S") if end else None
                except ValueError as e:
                    print(f"Error processing timestamps for student {student_id}: {str(e)}")
                    continue
            
            formatted_results.append((student_id, start_dt, end_dt, duration))
            print(f"Processed break for {student_id}: start={start_dt}, end={end_dt}, duration={duration}")  # Debug log
        
        return formatted_results
    
    def import_from_csv(self, csv_file):
        """Import students from a CSV file
        Expected CSV format:
        id,student_id,name
        """
        results = {"success": 0, "failed": 0, "errors": []}
        try:
            with open(csv_file, 'r') as file:
                reader = csv.DictReader(file)
                if not all(col in reader.fieldnames for col in ['id', 'student_id', 'name']):
                    raise ValueError("CSV must contain 'id', 'student_id', and 'name' columns")
                cursor = self.conn.cursor()
                for row in reader:
                    try:
                        nfc_uid = row.get('id')
                        student_id = row.get('student_id')
                        name = row.get('name')
                        if not nfc_uid or not student_id or not name:
                            results["failed"] += 1
                            results["errors"].append(f"Missing data in row: {row}")
                            continue
                        cursor.execute(
                            "INSERT INTO students (id, student_id, name) VALUES (?, ?, ?)",
                            (nfc_uid, student_id, name)
                        )
                        results["success"] += 1
                    except sqlite3.IntegrityError:
                        results["failed"] += 1
                        results["errors"].append(f"Duplicate NFC UID or student ID: {nfc_uid}, {student_id}")
                    except Exception as e:
                        results["failed"] += 1
                        results["errors"].append(f"Error processing row {row}: {str(e)}")
                self.conn.commit()
        except Exception as e:
            results["errors"].append(f"File error: {str(e)}")
            return results
        return results
    
    def import_from_json(self, json_file):
        """Import students from a JSON file
        Expected JSON format:
        [
            {"id": "nfc_uid", "student_id": "123456", "name": "John Doe"},
            ...
        ]
        """
        results = {"success": 0, "failed": 0, "errors": []}
        try:
            with open(json_file, 'r') as file:
                students = json.load(file)
                if not isinstance(students, list):
                    raise ValueError("JSON must contain an array of student objects")
                cursor = self.conn.cursor()
                for student in students:
                    try:
                        nfc_uid = student.get('id')
                        student_id = student.get('student_id')
                        name = student.get('name')
                        if not nfc_uid or not student_id or not name:
                            results["failed"] += 1
                            results["errors"].append(f"Missing data in object: {student}")
                            continue
                        cursor.execute(
                            "INSERT INTO students (id, student_id, name) VALUES (?, ?, ?)",
                            (nfc_uid, student_id, name)
                        )
                        results["success"] += 1
                    except sqlite3.IntegrityError:
                        results["failed"] += 1
                        results["errors"].append(f"Duplicate NFC UID or student ID: {nfc_uid}, {student_id}")
                    except Exception as e:
                        results["failed"] += 1
                        results["errors"].append(f"Error processing student {student}: {str(e)}")
                self.conn.commit()
        except Exception as e:
            results["errors"].append(f"File error: {str(e)}")
            return results
        return results
    
    def is_at_nurse(self, identifier):
        """Check if student is currently at the nurse by identifier (NFC UID or student_id)"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, visit_start 
            FROM nurse_visits 
            WHERE student_uid = ? 
            AND visit_end IS NULL
        """, (identifier,))
        result = cursor.fetchone()
        return result is not None
    
    def start_nurse_visit(self, nfc_uid=None, student_id=None):
        """Start a nurse visit for a student by identifier (NFC UID or student_id)"""
        identifier = self.get_identifier(nfc_uid, student_id)
        if not self.is_checked_in(identifier):
            return False, "Student is not checked in"
        try:
            cursor = self.conn.cursor()
            # Check if this student has an active nurse visit
            cursor.execute("""
                SELECT id FROM nurse_visits 
                WHERE student_uid = ? 
                AND visit_end IS NULL
            """, (identifier,))
            if cursor.fetchone():
                return False, "Student is already at the nurse"
            # Start new nurse visit
            current_time = datetime.now()
            cursor.execute("""
                INSERT INTO nurse_visits (student_uid, visit_start)
                VALUES (?, ?)
            """, (identifier, current_time))
            self.conn.commit()
            return True, "Nurse visit started"
        except Exception as e:
            self.conn.rollback()
            return False, str(e)
    
    def end_nurse_visit(self, nfc_uid=None, student_id=None):
        """End a nurse visit for a student by identifier (NFC UID or student_id)"""
        identifier = self.get_identifier(nfc_uid, student_id)
        try:
            cursor = self.conn.cursor()
            # Get the active nurse visit
            cursor.execute("""
                SELECT id, visit_start 
                FROM nurse_visits
                WHERE student_uid = ? 
                AND visit_end IS NULL
            """, (identifier,))
            result = cursor.fetchone()
            if not result:
                return False, "Student is not at the nurse"
            visit_id, visit_start = result
            visit_end = datetime.now()
            # Calculate duration
            try:
                # Try parsing as string first (for old data)
                if isinstance(visit_start, str):
                    try:
                        # Try ISO format first (with T separator)
                        start_dt = datetime.fromisoformat(visit_start)
                    except ValueError:
                        try:
                            # Try with microseconds
                            start_dt = datetime.strptime(visit_start, "%Y-%m-%d %H:%M:%S.%f")
                        except ValueError:
                            # Try without microseconds
                            start_dt = datetime.strptime(visit_start, "%Y-%m-%d %H:%M:%S")
                else:
                    # Already a datetime object
                    start_dt = visit_start
            except Exception as e:
                print(f"Error parsing visit_start: {e}")
                start_dt = visit_end  # Fallback to avoid errors
            
            duration = int((visit_end - start_dt).total_seconds() / 60)
            cursor.execute("""
                UPDATE nurse_visits
                SET visit_end = ?, duration_minutes = ?
                WHERE id = ?
            """, (visit_end, duration, visit_id))
            self.conn.commit()
            return True, "Nurse visit ended"
        except Exception as e:
            self.conn.rollback()
            return False, str(e)
    
    def get_today_nurse_visits(self):
        """Get all nurse visits for today (returns student_id, start, end, duration)"""
        cursor = self.conn.cursor()
        today = datetime.now().date()
        cursor.execute("""
            SELECT s.student_id, n.visit_start, n.visit_end, n.duration_minutes
            FROM nurse_visits n
            JOIN students s ON n.student_uid = s.id OR n.student_uid = s.student_id
            WHERE date(n.visit_start) = ?
            ORDER BY n.visit_start DESC
        """, (today.strftime("%Y-%m-%d"),))
        results = cursor.fetchall()
        formatted_results = []
        for student_id, start, end, duration in results:
            try:
                start_dt = datetime.strptime(start, "%Y-%m-%d %H:%M:%S.%f") if start else None
                end_dt = datetime.strptime(end, "%Y-%m-%d %H:%M:%S.%f") if end else None
            except ValueError:
                try:
                    start_dt = datetime.strptime(start, "%Y-%m-%d %H:%M:%S") if start else None
                    end_dt = datetime.strptime(end, "%Y-%m-%d %H:%M:%S") if end else None
                except ValueError as e:
                    continue
            formatted_results.append((student_id, start_dt, end_dt, duration))
        return formatted_results
    
    def is_at_water(self, identifier):
        """Check if student is currently at the water fountain by identifier (NFC UID or student_id)"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, visit_start 
            FROM water_visits 
            WHERE student_uid = ? 
            AND visit_end IS NULL
        """, (identifier,))
        result = cursor.fetchone()
        return result is not None
    
    def start_water_visit(self, nfc_uid=None, student_id=None):
        """Start a water fountain visit for a student by identifier (NFC UID or student_id)"""
        identifier = self.get_identifier(nfc_uid, student_id)
        if not self.is_checked_in(identifier):
            return False, "Student is not checked in"
        try:
            cursor = self.conn.cursor()
            # Check if this student has an active water visit
            cursor.execute("""
                SELECT id FROM water_visits 
                WHERE student_uid = ? 
                AND visit_end IS NULL
            """, (identifier,))
            if cursor.fetchone():
                return False, "Student is already at the water fountain"
            # Start new water visit
            current_time = datetime.now()
            cursor.execute("""
                INSERT INTO water_visits (student_uid, visit_start)
                VALUES (?, ?)
            """, (identifier, current_time))
            self.conn.commit()
            return True, "Water visit started"
        except Exception as e:
            self.conn.rollback()
            return False, str(e)
    
    def end_water_visit(self, nfc_uid=None, student_id=None):
        """End a water fountain visit for a student by identifier (NFC UID or student_id)"""
        identifier = self.get_identifier(nfc_uid, student_id)
        try:
            cursor = self.conn.cursor()
            # Get the active water visit
            cursor.execute("""
                SELECT id, visit_start 
                FROM water_visits
                WHERE student_uid = ? 
                AND visit_end IS NULL
            """, (identifier,))
            result = cursor.fetchone()
            if not result:
                return False, "Student is not at the water fountain"
            visit_id, visit_start = result
            visit_end = datetime.now()
            # Calculate duration
            try:
                # Try parsing as string first (for old data)
                if isinstance(visit_start, str):
                    try:
                        # Try ISO format first (with T separator)
                        start_dt = datetime.fromisoformat(visit_start)
                    except ValueError:
                        try:
                            # Try with microseconds
                            start_dt = datetime.strptime(visit_start, "%Y-%m-%d %H:%M:%S.%f")
                        except ValueError:
                            # Try without microseconds
                            start_dt = datetime.strptime(visit_start, "%Y-%m-%d %H:%M:%S")
                else:
                    # Already a datetime object
                    start_dt = visit_start
            except Exception as e:
                print(f"Error parsing visit_start: {e}")
                start_dt = visit_end  # Fallback to avoid errors
            
            duration = int((visit_end - start_dt).total_seconds() / 60)
            cursor.execute("""
                UPDATE water_visits
                SET visit_end = ?, duration_minutes = ?
                WHERE id = ?
            """, (visit_end, duration, visit_id))
            self.conn.commit()
            return True, "Water visit ended"
        except Exception as e:
            self.conn.rollback()
            return False, str(e)
    
    def auto_checkout_students(self):
        """Automatically check out students whose scheduled_check_out time has passed and check_out is NULL."""
        cursor = self.conn.cursor()
        now = datetime.now()
        today = now.date()
        cursor.execute(
            "SELECT id, student_uid, scheduled_check_out FROM attendance WHERE date = ? AND check_out IS NULL AND scheduled_check_out IS NOT NULL",
            (today,)
        )
        rows = cursor.fetchall()
        for row in rows:
            att_id, student_uid, scheduled_str = row
            try:
                scheduled_dt = datetime.strptime(scheduled_str, "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue
            if scheduled_dt <= now:
                cursor.execute(
                    "UPDATE attendance SET check_out = ? WHERE id = ?",
                    (now, att_id)
                )
        self.conn.commit() 