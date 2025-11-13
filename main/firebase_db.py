"""
Firebase Firestore Database Module

This module handles all data storage operations using Firebase Firestore.
All data (students, attendance, breaks, nurse visits) is stored in Firestore.
"""

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, time
import os
from typing import Optional, Tuple, List, Dict


# School periods configuration
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
    """Get the current period and end time for a given datetime"""
    t = dt.time()
    for period, start, end in PERIODS:
        if start <= t <= end:
            return period, end
    return None, None


class FirebaseDatabase:
    """Database class that uses Firebase Firestore for all data storage operations."""
    
    def __init__(self, credentials_file="firebase-service-account.json"):
        self.credentials_file = credentials_file
        self.db = None
        self.periods = PERIODS  # Default periods, will be updated from Firestore
        self.init_connection()
        self.load_periods()  # Load periods from Firestore on init
    
    def init_connection(self):
        """Initialize connection to Firebase Firestore"""
        try:
            # Check if Firebase app is already initialized
            if not firebase_admin._apps:
                # Initialize Firebase Admin SDK
                if os.path.exists(self.credentials_file):
                    cred = credentials.Certificate(self.credentials_file)
                    firebase_admin.initialize_app(cred)
                    print(f"[FIREBASE] Initialized with credentials from {self.credentials_file}")
                else:
                    print(f"[FIREBASE] Warning: Credentials file not found at {self.credentials_file}")
                    print("[FIREBASE] Attempting to initialize with default credentials...")
                    firebase_admin.initialize_app()
            
            # Get Firestore client
            self.db = firestore.client()
            print("[FIREBASE] Connected to Firestore database")
            
        except Exception as e:
            print(f"[FIREBASE] Error connecting to Firestore: {e}")
            raise
    
    def load_periods(self):
        """Load school periods from Firestore"""
        try:
            doc = self.db.collection('settings').document('periods').get()
            if doc.exists:
                data = doc.to_dict()
                periods_data = data.get('periods', [])
                
                # Convert periods data to the format used by the app
                # Each period has: name, start_hour, start_minute, end_hour, end_minute
                self.periods = []
                for period in periods_data:
                    name = period.get('name', '')
                    start_time = time(period['start_hour'], period['start_minute'])
                    end_time = time(period['end_hour'], period['end_minute'])
                    self.periods.append((name, start_time, end_time))
                
                print(f"[FIREBASE] Loaded {len(self.periods)} periods from Firestore")
            else:
                # No periods in Firestore, use defaults
                print("[FIREBASE] No periods found in Firestore, using default periods")
                self.periods = PERIODS
                
        except Exception as e:
            print(f"[FIREBASE] Error loading periods: {e}")
            print("[FIREBASE] Using default periods")
            self.periods = PERIODS
    
    def get_periods(self) -> List[Tuple]:
        """Get the current periods configuration"""
        return self.periods
    
    def get_period_for_time(self, dt):
        """Get the current period and end time for a given datetime"""
        t = dt.time()
        for period, start, end in self.periods:
            if start <= t <= end:
                return period, end
        return None, None
    
    def add_student(self, nfc_uid: str, student_id: str, name: str) -> bool:
        """Add a new student to the Firestore database"""
        try:
            students_ref = self.db.collection('students')
            
            # Check if student already exists by NFC UID
            if nfc_uid:
                doc = students_ref.document(nfc_uid).get()
                if doc.exists:
                    return False
            
            # Check if student_id already exists
            query = students_ref.where('student_id', '==', student_id).limit(1).get()
            if len(list(query)) > 0:
                return False
            
            # Use NFC UID as document ID if available, otherwise use student_id
            doc_id = nfc_uid if nfc_uid else student_id
            
            # Add new student
            student_data = {
                'nfc_uid': nfc_uid or '',
                'student_id': student_id,
                'name': name,
                'created_at': firestore.SERVER_TIMESTAMP
            }
            
            students_ref.document(doc_id).set(student_data)
            print(f"[FIREBASE] Added student: {name} (ID: {student_id})")
            return True
            
        except Exception as e:
            print(f"[FIREBASE] Error adding student: {e}")
            return False
    
    def get_student_by_uid(self, nfc_uid: str) -> Optional[Tuple[str, str]]:
        """Get student information by NFC UID"""
        try:
            doc = self.db.collection('students').document(nfc_uid).get()
            if doc.exists:
                data = doc.to_dict()
                return (data['student_id'], data['name'])
            return None
            
        except Exception as e:
            print(f"[FIREBASE] Error getting student by UID: {e}")
            return None
    
    def get_student_by_student_id(self, student_id: str) -> Optional[Tuple[str, str]]:
        """Get student information by school student_id"""
        try:
            students_ref = self.db.collection('students')
            query = students_ref.where('student_id', '==', str(student_id)).limit(1).get()
            
            for doc in query:
                data = doc.to_dict()
                return (data.get('nfc_uid', ''), data['name'])
            
            return None
            
        except Exception as e:
            print(f"[FIREBASE] Error getting student by ID: {e}")
            return None
    
    def get_identifier(self, nfc_uid: Optional[str] = None, student_id: Optional[str] = None) -> Optional[str]:
        """Return the identifier to use: NFC UID if present, else student_id"""
        if nfc_uid:
            return nfc_uid
        elif student_id:
            return student_id
        else:
            return None
    
    def get_student_name(self, identifier: str) -> str:
        """Get student name by identifier (NFC UID or Student ID)"""
        try:
            # Try by NFC UID first
            doc = self.db.collection('students').document(identifier).get()
            if doc.exists:
                return doc.to_dict()['name']
            
            # Try by student_id
            students_ref = self.db.collection('students')
            query = students_ref.where('student_id', '==', str(identifier)).limit(1).get()
            
            for doc in query:
                return doc.to_dict()['name']
            
            return "Unknown Student"
            
        except Exception as e:
            print(f"[FIREBASE] Error getting student name: {e}")
            return "Unknown Student"
    
    def check_in(self, nfc_uid: Optional[str] = None, student_id: Optional[str] = None) -> Tuple[bool, str]:
        """Record student check-in"""
        try:
            identifier = self.get_identifier(nfc_uid, student_id)
            if not identifier:
                return False, "No student identifier provided"
            
            # Check if student exists
            if nfc_uid:
                student_info = self.get_student_by_uid(nfc_uid)
            else:
                student_info = self.get_student_by_student_id(student_id)
            
            if not student_info:
                return False, "Student not found in database"
            
            # Check if already checked in today
            today = datetime.now().date().isoformat()
            attendance_ref = self.db.collection('attendance')
            query = attendance_ref.where('student_uid', '==', identifier).where('date', '==', today).limit(1).get()
            
            if len(list(query)) > 0:
                return False, "Already checked in today"
            
            # Determine scheduled check-out time
            current_time = datetime.now()
            _, period_end = self.get_period_for_time(current_time)
            scheduled_check_out = None
            if period_end:
                scheduled_check_out = current_time.replace(
                    hour=period_end.hour, 
                    minute=period_end.minute, 
                    second=0, 
                    microsecond=0
                ).isoformat()
            
            # Get student name
            student_name = self.get_student_name(identifier)
            
            # Add attendance record
            attendance_data = {
                'student_uid': identifier,
                'student_name': student_name,
                'date': today,
                'check_in': current_time.isoformat(),
                'check_out': '',
                'scheduled_check_out': scheduled_check_out or ''
            }
            
            attendance_ref.add(attendance_data)
            
            return True, "Checked in successfully"
            
        except Exception as e:
            print(f"[FIREBASE] Error during check-in: {e}")
            return False, f"Error during check-in: {str(e)}"
    
    def is_checked_in(self, identifier: str) -> bool:
        """Check if student is checked in today"""
        try:
            today = datetime.now().date().isoformat()
            attendance_ref = self.db.collection('attendance')
            query = attendance_ref.where('student_uid', '==', identifier).where('date', '==', today).limit(1).get()
            
            return len(list(query)) > 0
            
        except Exception as e:
            print(f"[FIREBASE] Error checking if checked in: {e}")
            return False
    
    def is_on_break(self, identifier: str) -> bool:
        """Check if student is currently on a bathroom break"""
        try:
            breaks_ref = self.db.collection('bathroom_breaks')
            query = breaks_ref.where('student_uid', '==', identifier).where('break_end', '==', None).limit(1).get()
            
            return len(list(query)) > 0
            
        except Exception as e:
            print(f"[FIREBASE] Error checking break status: {e}")
            return False
    
    def start_bathroom_break(self, identifier: str) -> Tuple[bool, str]:
        """Start a bathroom break for a student"""
        try:
            if not self.is_checked_in(identifier):
                # Auto-check-in the student first
                print(f"[FIREBASE] Student {identifier} not checked in, auto-checking in...")
                if identifier.startswith('TEST') or len(str(identifier)) > 10:
                    success, message = self.check_in(nfc_uid=identifier)
                else:
                    success, message = self.check_in(student_id=identifier)
                
                if not success:
                    return False, f"Auto-check-in failed: {message}"
                print(f"[FIREBASE] Auto-check-in successful: {message}")
            
            # Check if this student has an active break - if so, end it
            if self.is_on_break(identifier):
                print(f"[FIREBASE] Student {identifier} is already on a break, ending current break...")
                success, message = self.end_bathroom_break(identifier)
                if success:
                    print(f"[FIREBASE] Ended previous break: {message}")
                    return True, "Previous break ended, ready for new activities"
                else:
                    return False, f"Failed to end previous break: {message}"
            
            # Check if any OTHER student is currently on a break
            breaks_ref = self.db.collection('bathroom_breaks')
            query = breaks_ref.where('break_end', '==', None).get()
            
            for doc in query:
                data = doc.to_dict()
                if data['student_uid'] != identifier:
                    active_student = data['student_uid']
                    student_name = self.get_student_name(active_student)
                    return False, f"Another student ({student_name}) is already on a break"
            
            # Get student name and start new break
            student_name = self.get_student_name(identifier)
            current_time = datetime.now().isoformat()
            
            break_data = {
                'student_uid': identifier,
                'student_name': student_name,
                'break_start': current_time,
                'break_end': None,
                'duration_minutes': None
            }
            
            breaks_ref.add(break_data)
            
            return True, "Break started"
            
        except Exception as e:
            print(f"[FIREBASE] Error starting bathroom break: {e}")
            return False, str(e)
    
    def end_bathroom_break(self, identifier: str) -> Tuple[bool, str]:
        """End a bathroom break for a student"""
        try:
            breaks_ref = self.db.collection('bathroom_breaks')
            query = breaks_ref.where('student_uid', '==', identifier).where('break_end', '==', None).get()
            
            for doc in query:
                data = doc.to_dict()
                
                # Calculate duration
                start_time = datetime.fromisoformat(data['break_start'])
                end_time = datetime.now()
                duration = int((end_time - start_time).total_seconds() / 60)
                
                # Update the document
                doc.reference.update({
                    'break_end': end_time.isoformat(),
                    'duration_minutes': duration
                })
                
                return True, "Break ended"
            
            return False, "Student is not on a break"
            
        except Exception as e:
            print(f"[FIREBASE] Error ending bathroom break: {e}")
            return False, str(e)
    
    def is_at_nurse(self, identifier: str) -> bool:
        """Check if student is currently at the nurse"""
        try:
            nurse_ref = self.db.collection('nurse_visits')
            query = nurse_ref.where('student_uid', '==', identifier).where('visit_end', '==', None).limit(1).get()
            
            return len(list(query)) > 0
            
        except Exception as e:
            print(f"[FIREBASE] Error checking nurse status: {e}")
            return False
    
    def has_students_out(self) -> bool:
        """Check if any students are currently out (on bathroom break, at nurse, or at water fountain)"""
        try:
            # Check for active bathroom breaks
            breaks_ref = self.db.collection('bathroom_breaks')
            breaks_query = breaks_ref.where('break_end', '==', None).limit(1).get()
            
            if len(list(breaks_query)) > 0:
                return True
            
            # Check for active nurse visits
            nurse_ref = self.db.collection('nurse_visits')
            nurse_query = nurse_ref.where('visit_end', '==', None).limit(1).get()
            
            if len(list(nurse_query)) > 0:
                return True
            
            # Check for active water visits
            water_ref = self.db.collection('water_visits')
            water_query = water_ref.where('visit_end', '==', None).limit(1).get()
            
            if len(list(water_query)) > 0:
                return True
            
            return False
            
        except Exception as e:
            print(f"[FIREBASE] Error checking if students are out: {e}")
            return False
    
    def get_students_without_nfc_uid(self) -> List[Dict]:
        """Get list of students who don't have an NFC UID assigned"""
        try:
            students_ref = self.db.collection('students')
            query = students_ref.where('nfc_uid', '==', '').get()
            
            unassigned_students = []
            for i, doc in enumerate(query):
                data = doc.to_dict()
                unassigned_students.append({
                    'student_id': data['student_id'],
                    'name': data['name'],
                    'row_number': i + 1
                })
            
            return unassigned_students
            
        except Exception as e:
            print(f"[FIREBASE] Error getting students without NFC UID: {e}")
            return []
    
    def link_nfc_card_to_student(self, nfc_uid: str, student_id: str) -> Tuple[bool, str]:
        """Link an NFC card UID to a student"""
        try:
            students_ref = self.db.collection('students')
            query = students_ref.where('student_id', '==', str(student_id)).limit(1).get()
            
            for doc in query:
                data = doc.to_dict()
                student_name = data['name']
                
                # Delete old document
                doc.reference.delete()
                
                # Create new document with NFC UID as ID
                new_data = {
                    'nfc_uid': nfc_uid,
                    'student_id': student_id,
                    'name': student_name,
                    'created_at': data.get('created_at', firestore.SERVER_TIMESTAMP)
                }
                students_ref.document(nfc_uid).set(new_data)
                
                print(f"[FIREBASE] Linked NFC UID {nfc_uid} to student {student_name} (ID: {student_id})")
                return True, f"Card linked to {student_name}"
            
            return False, "Student not found"
            
        except Exception as e:
            print(f"[FIREBASE] Error linking NFC card: {e}")
            return False, str(e)
    
    def start_nurse_visit(self, nfc_uid: Optional[str] = None, student_id: Optional[str] = None) -> Tuple[bool, str]:
        """Start a nurse visit for a student"""
        try:
            identifier = self.get_identifier(nfc_uid, student_id)
            if not self.is_checked_in(identifier):
                # Auto-check-in the student first
                print(f"[FIREBASE] Student {identifier} not checked in, auto-checking in...")
                if identifier.startswith('TEST') or len(str(identifier)) > 10:
                    success, message = self.check_in(nfc_uid=identifier)
                else:
                    success, message = self.check_in(student_id=identifier)
                
                if not success:
                    return False, f"Auto-check-in failed: {message}"
                print(f"[FIREBASE] Auto-check-in successful: {message}")
            
            # Check if this student has an active nurse visit - if so, end it
            if self.is_at_nurse(identifier):
                print(f"[FIREBASE] Student {identifier} is already at nurse, ending current visit...")
                success, message = self.end_nurse_visit(nfc_uid=nfc_uid, student_id=student_id)
                if success:
                    print(f"[FIREBASE] Ended previous nurse visit: {message}")
                    return True, "Previous nurse visit ended, ready for new activities"
                else:
                    return False, f"Failed to end previous nurse visit: {message}"
            
            # Get student name and start new nurse visit
            student_name = self.get_student_name(identifier)
            current_time = datetime.now().isoformat()
            
            visit_data = {
                'student_uid': identifier,
                'student_name': student_name,
                'visit_start': current_time,
                'visit_end': None,
                'duration_minutes': None
            }
            
            self.db.collection('nurse_visits').add(visit_data)
            
            return True, "Nurse visit started"
            
        except Exception as e:
            print(f"[FIREBASE] Error starting nurse visit: {e}")
            return False, str(e)
    
    def end_nurse_visit(self, nfc_uid: Optional[str] = None, student_id: Optional[str] = None) -> Tuple[bool, str]:
        """End a nurse visit for a student"""
        try:
            identifier = self.get_identifier(nfc_uid, student_id)
            nurse_ref = self.db.collection('nurse_visits')
            query = nurse_ref.where('student_uid', '==', identifier).where('visit_end', '==', None).get()
            
            for doc in query:
                data = doc.to_dict()
                
                # Calculate duration
                start_time = datetime.fromisoformat(data['visit_start'])
                end_time = datetime.now()
                duration = int((end_time - start_time).total_seconds() / 60)
                
                # Update the document
                doc.reference.update({
                    'visit_end': end_time.isoformat(),
                    'duration_minutes': duration
                })
                
                return True, "Nurse visit ended"
            
            return False, "Student is not at the nurse"
            
        except Exception as e:
            print(f"[FIREBASE] Error ending nurse visit: {e}")
            return False, str(e)
    
    def is_at_water(self, identifier: str) -> bool:
        """Check if student is currently at the water fountain"""
        try:
            water_ref = self.db.collection('water_visits')
            query = water_ref.where('student_uid', '==', identifier).where('visit_end', '==', None).limit(1).get()
            
            return len(list(query)) > 0
            
        except Exception as e:
            print(f"[FIREBASE] Error checking water status: {e}")
            return False
    
    def start_water_visit(self, nfc_uid: Optional[str] = None, student_id: Optional[str] = None) -> Tuple[bool, str]:
        """Start a water fountain visit for a student"""
        try:
            identifier = self.get_identifier(nfc_uid, student_id)
            if not self.is_checked_in(identifier):
                # Auto-check-in the student first
                print(f"[FIREBASE] Student {identifier} not checked in, auto-checking in...")
                if identifier.startswith('TEST') or len(str(identifier)) > 10:
                    success, message = self.check_in(nfc_uid=identifier)
                else:
                    success, message = self.check_in(student_id=identifier)
                
                if not success:
                    return False, f"Auto-check-in failed: {message}"
                print(f"[FIREBASE] Auto-check-in successful: {message}")
            
            # Check if this student has an active water visit - if so, end it
            if self.is_at_water(identifier):
                print(f"[FIREBASE] Student {identifier} is already at water fountain, ending current visit...")
                success, message = self.end_water_visit(nfc_uid=nfc_uid, student_id=student_id)
                if success:
                    print(f"[FIREBASE] Ended previous water visit: {message}")
                    return True, "Previous water visit ended, ready for new activities"
                else:
                    return False, f"Failed to end previous water visit: {message}"
            
            # Get student name and start new water visit
            student_name = self.get_student_name(identifier)
            current_time = datetime.now().isoformat()
            
            visit_data = {
                'student_uid': identifier,
                'student_name': student_name,
                'visit_start': current_time,
                'visit_end': None,
                'duration_minutes': None
            }
            
            self.db.collection('water_visits').add(visit_data)
            
            return True, "Water visit started"
            
        except Exception as e:
            print(f"[FIREBASE] Error starting water visit: {e}")
            return False, str(e)
    
    def end_water_visit(self, nfc_uid: Optional[str] = None, student_id: Optional[str] = None) -> Tuple[bool, str]:
        """End a water fountain visit for a student"""
        try:
            identifier = self.get_identifier(nfc_uid, student_id)
            water_ref = self.db.collection('water_visits')
            query = water_ref.where('student_uid', '==', identifier).where('visit_end', '==', None).get()
            
            for doc in query:
                data = doc.to_dict()
                
                # Calculate duration
                start_time = datetime.fromisoformat(data['visit_start'])
                end_time = datetime.now()
                duration = int((end_time - start_time).total_seconds() / 60)
                
                # Update the document
                doc.reference.update({
                    'visit_end': end_time.isoformat(),
                    'duration_minutes': duration
                })
                
                return True, "Water visit ended"
            
            return False, "Student is not at the water fountain"
            
        except Exception as e:
            print(f"[FIREBASE] Error ending water visit: {e}")
            return False, str(e)
    
    def get_today_attendance(self) -> List[Tuple]:
        """Get today's attendance records"""
        try:
            today = datetime.now().date().isoformat()
            
            # Get all students
            students = {}
            students_ref = self.db.collection('students').get()
            for doc in students_ref:
                data = doc.to_dict()
                students[doc.id] = {
                    'student_id': data['student_id'],
                    'name': data['name']
                }
            
            # Get today's attendance
            attendance_ref = self.db.collection('attendance')
            query = attendance_ref.where('date', '==', today).get()
            
            attendance_map = {}
            for doc in query:
                data = doc.to_dict()
                student_uid = data['student_uid']
                attendance_map[student_uid] = {
                    'check_in': datetime.fromisoformat(data['check_in']) if data.get('check_in') else None,
                    'check_out': datetime.fromisoformat(data['check_out']) if data.get('check_out') else None
                }
            
            # Build results
            results = []
            for uid, student_data in students.items():
                student_id = student_data['student_id']
                name = student_data['name']
                attendance = attendance_map.get(uid, {})
                check_in = attendance.get('check_in')
                check_out = attendance.get('check_out')
                results.append((student_id, name, check_in, check_out))
            
            return results
            
        except Exception as e:
            print(f"[FIREBASE] Error getting today's attendance: {e}")
            return []
    
    def get_today_breaks(self) -> List[Tuple]:
        """Get all bathroom breaks for today"""
        try:
            today = datetime.now().date().isoformat()
            
            breaks_ref = self.db.collection('bathroom_breaks')
            all_breaks = breaks_ref.get()
            
            results = []
            for doc in all_breaks:
                data = doc.to_dict()
                if data.get('break_start'):
                    start_dt = datetime.fromisoformat(data['break_start'])
                    if start_dt.date().isoformat() == today:
                        student_name = data.get('student_name', 'Unknown')
                        end_dt = datetime.fromisoformat(data['break_end']) if data.get('break_end') else None
                        duration = data.get('duration_minutes')
                        results.append((student_name, start_dt, end_dt, duration))
            
            return results
            
        except Exception as e:
            print(f"[FIREBASE] Error getting today's breaks: {e}")
            return []
    
    def get_today_nurse_visits(self) -> List[Tuple]:
        """Get all nurse visits for today"""
        try:
            today = datetime.now().date().isoformat()
            
            nurse_ref = self.db.collection('nurse_visits')
            all_visits = nurse_ref.get()
            
            results = []
            for doc in all_visits:
                data = doc.to_dict()
                if data.get('visit_start'):
                    start_dt = datetime.fromisoformat(data['visit_start'])
                    if start_dt.date().isoformat() == today:
                        student_name = data.get('student_name', 'Unknown')
                        end_dt = datetime.fromisoformat(data['visit_end']) if data.get('visit_end') else None
                        duration = data.get('duration_minutes')
                        results.append((student_name, start_dt, end_dt, duration))
            
            return results
            
        except Exception as e:
            print(f"[FIREBASE] Error getting today's nurse visits: {e}")
            return []
    
    def auto_checkout_students(self):
        """Automatically check out students whose scheduled_check_out time has passed and end active breaks/visits at period end"""
        try:
            now = datetime.now()
            today = now.date().isoformat()

            attendance_ref = self.db.collection('attendance')
            query = attendance_ref.where('date', '==', today).where('check_out', '==', '').get()

            for doc in query:
                data = doc.to_dict()
                scheduled_check_out = data.get('scheduled_check_out')

                if scheduled_check_out:
                    try:
                        scheduled_dt = datetime.fromisoformat(scheduled_check_out)
                        if scheduled_dt <= now:
                            doc.reference.update({'check_out': now.isoformat()})
                            print(f"[FIREBASE] Auto-checked out student: {data['student_uid']}")
                    except Exception as e:
                        print(f"[FIREBASE] Error processing scheduled checkout for {data['student_uid']}: {e}")
                        continue

            # Also auto-end bathroom breaks, nurse visits, and water visits at period end
            self._auto_end_breaks_and_visits_at_period_end()

        except Exception as e:
            print(f"[FIREBASE] Error in auto-checkout: {e}")

    def _auto_end_breaks_and_visits_at_period_end(self):
        """Automatically end active bathroom breaks, nurse visits, and water visits when the current period ends"""
        try:
            now = datetime.now()

            # Get current period end time
            _, period_end_time = self.get_period_for_time(now)

            if not period_end_time:
                # No current period or period end time available
                return

            # Create period end datetime for today
            period_end_dt = datetime.combine(now.date(), period_end_time)

            # Only auto-end if we're past the period end time
            if now <= period_end_dt:
                return

            print(f"[FIREBASE AUTO-END] Period ended at {period_end_dt}, auto-ending active breaks and visits...")

            # Auto-end bathroom breaks
            breaks_ref = self.db.collection('bathroom_breaks')
            breaks_query = breaks_ref.where('break_end', '==', None).get()

            for doc in breaks_query:
                try:
                    data = doc.to_dict()
                    break_start_str = data.get('break_start')

                    if break_start_str:
                        # Parse break start time
                        break_start_dt = datetime.fromisoformat(break_start_str)

                        # Only auto-end breaks that started before the period end
                        if break_start_dt < period_end_dt:
                            # Calculate duration
                            duration = int((period_end_dt - break_start_dt).total_seconds() / 60)

                            # End the break
                            doc.reference.update({
                                'break_end': period_end_dt.isoformat(),
                                'duration_minutes': duration
                            })

                            print(f"[FIREBASE AUTO-END] Ended bathroom break for {data['student_uid']} (duration: {duration}min)")

                except Exception as e:
                    print(f"[FIREBASE AUTO-END] Error ending bathroom break: {e}")

            # Auto-end nurse visits
            nurse_ref = self.db.collection('nurse_visits')
            nurse_query = nurse_ref.where('visit_end', '==', None).get()

            for doc in nurse_query:
                try:
                    data = doc.to_dict()
                    visit_start_str = data.get('visit_start')

                    if visit_start_str:
                        # Parse visit start time
                        visit_start_dt = datetime.fromisoformat(visit_start_str)

                        # Only auto-end visits that started before the period end
                        if visit_start_dt < period_end_dt:
                            # Calculate duration
                            duration = int((period_end_dt - visit_start_dt).total_seconds() / 60)

                            # End the visit
                            doc.reference.update({
                                'visit_end': period_end_dt.isoformat(),
                                'duration_minutes': duration
                            })

                            print(f"[FIREBASE AUTO-END] Ended nurse visit for {data['student_uid']} (duration: {duration}min)")

                except Exception as e:
                    print(f"[FIREBASE AUTO-END] Error ending nurse visit: {e}")

            # Auto-end water visits
            water_ref = self.db.collection('water_visits')
            water_query = water_ref.where('visit_end', '==', None).get()

            for doc in water_query:
                try:
                    data = doc.to_dict()
                    visit_start_str = data.get('visit_start')

                    if visit_start_str:
                        # Parse visit start time
                        visit_start_dt = datetime.fromisoformat(visit_start_str)

                        # Only auto-end visits that started before the period end
                        if visit_start_dt < period_end_dt:
                            # Calculate duration
                            duration = int((period_end_dt - visit_start_dt).total_seconds() / 60)

                            # End the visit
                            doc.reference.update({
                                'visit_end': period_end_dt.isoformat(),
                                'duration_minutes': duration
                            })

                            print(f"[FIREBASE AUTO-END] Ended water visit for {data['student_uid']} (duration: {duration}min)")

                except Exception as e:
                    print(f"[FIREBASE AUTO-END] Error ending water visit: {e}")

        except Exception as e:
            print(f"[FIREBASE AUTO-END] Error in auto-end breaks and visits: {e}")
    
    def import_from_csv(self, csv_file: str) -> Dict:
        """Import students from CSV file"""
        import csv
        results = {"success": 0, "failed": 0, "errors": []}
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                # Try to detect if file has headers
                sample = file.read(1024)
                file.seek(0)
                
                has_header = csv.Sniffer().has_header(sample)
                reader = csv.reader(file)
                
                if has_header:
                    next(reader)  # Skip header row
                
                for row_num, row in enumerate(reader, start=2 if has_header else 1):
                    try:
                        if len(row) < 3:
                            results["failed"] += 1
                            results["errors"].append(f"Row {row_num}: Not enough columns")
                            continue
                        
                        nfc_uid = row[0].strip() if row[0] else ''
                        student_id = row[1].strip()
                        name = row[2].strip()
                        created_at = row[3].strip() if len(row) > 3 and row[3] else datetime.now().isoformat()
                        
                        if not student_id or not name:
                            results["failed"] += 1
                            results["errors"].append(f"Row {row_num}: Missing student_id or name")
                            continue
                        
                        # Use NFC UID as document ID if available, otherwise use student_id
                        doc_id = nfc_uid if nfc_uid else student_id
                        
                        student_data = {
                            'nfc_uid': nfc_uid,
                            'student_id': student_id,
                            'name': name,
                            'created_at': created_at
                        }
                        
                        self.db.collection('students').document(doc_id).set(student_data)
                        results["success"] += 1
                        
                    except Exception as e:
                        results["failed"] += 1
                        results["errors"].append(f"Row {row_num}: {str(e)}")
            
            print(f"[FIREBASE] CSV Import: {results['success']} successful, {results['failed']} failed")
            return results
            
        except Exception as e:
            results["errors"].append(f"File error: {str(e)}")
            return results
    
    def import_from_json(self, json_file: str) -> Dict:
        """Import students from JSON file"""
        import json
        results = {"success": 0, "failed": 0, "errors": []}
        
        try:
            with open(json_file, 'r', encoding='utf-8') as file:
                students = json.load(file)
                
                if not isinstance(students, list):
                    results["errors"].append("JSON must contain an array of student objects")
                    return results
                
                for idx, student in enumerate(students):
                    try:
                        nfc_uid = student.get('nfc_uid', '') or student.get('NFC_UID', '')
                        student_id = student.get('student_id') or student.get('Student_ID')
                        name = student.get('name') or student.get('Name')
                        created_at = student.get('created_at') or student.get('Created_At') or datetime.now().isoformat()
                        
                        if not student_id or not name:
                            results["failed"] += 1
                            results["errors"].append(f"Student {idx + 1}: Missing student_id or name")
                            continue
                        
                        # Use NFC UID as document ID if available, otherwise use student_id
                        doc_id = nfc_uid if nfc_uid else str(student_id)
                        
                        student_data = {
                            'nfc_uid': nfc_uid,
                            'student_id': str(student_id),
                            'name': name,
                            'created_at': created_at
                        }
                        
                        self.db.collection('students').document(doc_id).set(student_data)
                        results["success"] += 1
                        
                    except Exception as e:
                        results["failed"] += 1
                        results["errors"].append(f"Student {idx + 1}: {str(e)}")
            
            print(f"[FIREBASE] JSON Import: {results['success']} successful, {results['failed']} failed")
            return results
            
        except Exception as e:
            results["errors"].append(f"File error: {str(e)}")
            return results


if __name__ == "__main__":
    # Test the Firebase database
    print("Testing Firebase Database...")
    
    try:
        db = FirebaseDatabase()
        print("✅ Successfully connected to Firebase!")
        
        # Test adding a student
        success = db.add_student("TEST123", "999999", "Test Student")
        if success:
            print("✅ Successfully added test student")
        else:
            print("ℹ️ Test student already exists or couldn't be added")
        
        # Test getting student
        student = db.get_student_by_uid("TEST123")
        if student:
            print(f"✅ Retrieved student: {student}")
        
        print("🎉 Firebase integration working!")
        
    except Exception as e:
        print(f"❌ Error testing Firebase: {e}")

