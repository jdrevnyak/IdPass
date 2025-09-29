"""
Google Sheets Database Module

This module handles all data storage operations using Google Sheets instead of SQLite.
All data (students, attendance, breaks, nurse visits) is stored in Google Sheets.
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, time
import os


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


class GoogleSheetsDatabase:
    """Database class that uses Google Sheets for all data storage operations."""
    
    def __init__(self, credentials_file="bussed-2e3ff-04a2f3a1396d.json", spreadsheet_name="Student Attendance Tracking"):
        self.credentials_file = credentials_file
        self.spreadsheet_name = spreadsheet_name
        self.gc = None
        self.spreadsheet = None
        self.init_connection()
        self.ensure_worksheets()
    
    def init_connection(self):
        """Initialize connection to Google Sheets"""
        try:
            # Define the scope
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Authenticate using service account credentials
            creds = ServiceAccountCredentials.from_json_keyfile_name(self.credentials_file, scope)
            self.gc = gspread.authorize(creds)
            
            # Try to open existing spreadsheet or create new one
            try:
                self.spreadsheet = self.gc.open(self.spreadsheet_name)
                print(f"Connected to existing spreadsheet: {self.spreadsheet_name}")
            except gspread.SpreadsheetNotFound:
                try:
                    self.spreadsheet = self.gc.create(self.spreadsheet_name)
                    print(f"Created new spreadsheet: {self.spreadsheet_name}")
                    
                    # Share with the service account email for editing
                    self.spreadsheet.share('idcheck@-2e3ff.iam.gserviceaccount.com', perm_type='user', role='writer')
                except Exception as create_error:
                    print(f"Cannot create new spreadsheet (quota exceeded): {create_error}")
                    # Try to find any existing spreadsheet we can use
                    spreadsheets = self.gc.openall()
                    if spreadsheets:
                        self.spreadsheet = spreadsheets[0]  # Use the first available spreadsheet
                        print(f"Using existing spreadsheet: {self.spreadsheet.title}")
                    else:
                        raise Exception("No accessible spreadsheets found and cannot create new one due to quota")
                
        except Exception as e:
            print(f"Error connecting to Google Sheets: {e}")
            raise
    
    def ensure_worksheets(self):
        """Ensure all required worksheets exist with proper headers"""
        worksheets_config = {
            'Students': ['NFC_UID', 'Student_ID', 'Name', 'Created_At'],
            'Attendance': ['ID', 'Student_UID', 'Student_Name', 'Date', 'Check_In', 'Check_Out', 'Scheduled_Check_Out'],
            'Bathroom_Breaks': ['ID', 'Student_UID', 'Student_Name', 'Break_Start', 'Break_End', 'Duration_Minutes'],
            'Nurse_Visits': ['ID', 'Student_UID', 'Student_Name', 'Visit_Start', 'Visit_End', 'Duration_Minutes']
        }
        
        existing_worksheets = [ws.title for ws in self.spreadsheet.worksheets()]
        
        for sheet_name, headers in worksheets_config.items():
            if sheet_name not in existing_worksheets:
                # Create new worksheet
                worksheet = self.spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=len(headers))
                print(f"Created worksheet: {sheet_name}")
            else:
                worksheet = self.spreadsheet.worksheet(sheet_name)
            
            # Set headers if they don't exist
            try:
                current_headers = worksheet.row_values(1)
                if not current_headers or current_headers != headers:
                    worksheet.update(values=[headers], range_name='1:1')
                    print(f"Updated headers for {sheet_name}")
            except Exception as e:
                print(f"Error setting headers for {sheet_name}: {e}")
        
        # Remove default "Sheet1" if it exists and is empty
        try:
            sheet1 = self.spreadsheet.worksheet("Sheet1")
            if not sheet1.get_all_values():
                self.spreadsheet.del_worksheet(sheet1)
                print("Removed empty default Sheet1")
        except:
            pass
    
    def get_next_id(self, worksheet_name):
        """Get the next available ID for a worksheet"""
        try:
            worksheet = self.spreadsheet.worksheet(worksheet_name)
            ids = worksheet.col_values(1)[1:]  # Skip header
            if not ids:
                return 1
            # Filter out non-numeric IDs and get max
            numeric_ids = [int(id_val) for id_val in ids if id_val.isdigit()]
            return max(numeric_ids) + 1 if numeric_ids else 1
        except Exception as e:
            print(f"Error getting next ID for {worksheet_name}: {e}")
            return 1
    
    def add_student(self, nfc_uid, student_id, name):
        """Add a new student to the Google Sheets database"""
        try:
            worksheet = self.spreadsheet.worksheet('Students')
            
            # Check if student already exists
            students = worksheet.get_all_records()
            for student in students:
                if student['NFC_UID'] == nfc_uid or str(student['Student_ID']) == str(student_id):
                    return False
            
            # Add new student
            new_row = [nfc_uid, student_id, name, datetime.now().isoformat()]
            worksheet.append_row(new_row)
            print(f"Added student: {name} (ID: {student_id})")
            return True
            
        except Exception as e:
            print(f"Error adding student: {e}")
            return False
    
    def get_student_by_uid(self, nfc_uid):
        """Get student information by NFC UID"""
        try:
            worksheet = self.spreadsheet.worksheet('Students')
            students = worksheet.get_all_records()
            
            for student in students:
                if student['NFC_UID'] == nfc_uid:
                    return (student['Student_ID'], student['Name'])
            return None
            
        except Exception as e:
            print(f"Error getting student by UID: {e}")
            return None
    
    def get_student_by_student_id(self, student_id):
        """Get student information by school student_id"""
        try:
            worksheet = self.spreadsheet.worksheet('Students')
            students = worksheet.get_all_records()
            
            for student in students:
                # Convert both to strings for comparison to handle int/string mismatch
                if str(student['Student_ID']) == str(student_id):
                    return (student['NFC_UID'], student['Name'])
            return None
            
        except Exception as e:
            print(f"Error getting student by ID: {e}")
            return None
    
    def get_identifier(self, nfc_uid=None, student_id=None):
        """Return the identifier to use: NFC UID if present, else student_id"""
        if nfc_uid:
            return nfc_uid
        elif student_id:
            return student_id
        else:
            return None
    
    def get_student_name(self, identifier):
        """Get student name by identifier (NFC UID or Student ID)"""
        try:
            worksheet = self.spreadsheet.worksheet('Students')
            students = worksheet.get_all_records()
            
            for student in students:
                if (student['NFC_UID'] == identifier or 
                    str(student['Student_ID']) == str(identifier)):
                    return student['Name']
            return "Unknown Student"
            
        except Exception as e:
            print(f"Error getting student name: {e}")
            return "Unknown Student"
    
    def check_in(self, nfc_uid=None, student_id=None):
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
            attendance_ws = self.spreadsheet.worksheet('Attendance')
            attendance_records = attendance_ws.get_all_records()
            
            for record in attendance_records:
                if str(record['Student_UID']) == str(identifier) and record['Date'] == today:
                    return False, "Already checked in today"
            
            # Determine scheduled check-out time
            current_time = datetime.now()
            _, period_end = get_period_for_time(current_time)
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
            next_id = self.get_next_id('Attendance')
            new_row = [
                next_id,
                identifier,
                student_name,
                today,
                current_time.isoformat(),
                '',  # Check_Out (empty)
                scheduled_check_out or ''
            ]
            attendance_ws.append_row(new_row)
            
            return True, "Checked in successfully"
            
        except Exception as e:
            print(f"Error during check-in: {e}")
            return False, f"Error during check-in: {str(e)}"
    
    def is_checked_in(self, identifier):
        """Check if student is checked in today"""
        try:
            today = datetime.now().date().isoformat()
            attendance_ws = self.spreadsheet.worksheet('Attendance')
            attendance_records = attendance_ws.get_all_records()
            
            for record in attendance_records:
                if str(record['Student_UID']) == str(identifier) and record['Date'] == today:
                    return True
            return False
            
        except Exception as e:
            print(f"Error checking if checked in: {e}")
            return False
    
    def is_on_break(self, identifier):
        """Check if student is currently on a bathroom break"""
        try:
            breaks_ws = self.spreadsheet.worksheet('Bathroom_Breaks')
            breaks = breaks_ws.get_all_records()
            
            for break_record in breaks:
                if (str(break_record['Student_UID']) == str(identifier) and 
                    break_record['Break_End'] == ''):
                    return True
            return False
            
        except Exception as e:
            print(f"Error checking break status: {e}")
            return False
    
    def start_bathroom_break(self, identifier):
        """Start a bathroom break for a student"""
        try:
            if not self.is_checked_in(identifier):
                # Auto-check-in the student first
                print(f"Student {identifier} not checked in, auto-checking in...")
                # Determine if it's an NFC UID or Student ID
                if identifier.startswith('TEST') or len(str(identifier)) > 10:
                    # Looks like NFC UID
                    success, message = self.check_in(nfc_uid=identifier)
                else:
                    # Looks like Student ID
                    success, message = self.check_in(student_id=identifier)
                
                if not success:
                    return False, f"Auto-check-in failed: {message}"
                print(f"Auto-check-in successful: {message}")
            
            # Check if this student has an active break - if so, end it
            if self.is_on_break(identifier):
                print(f"Student {identifier} is already on a break, ending current break...")
                success, message = self.end_bathroom_break(identifier)
                if success:
                    print(f"Ended previous break: {message}")
                    return True, "Previous break ended, ready for new activities"
                else:
                    return False, f"Failed to end previous break: {message}"
            
            # Check if any OTHER student is currently on a break
            breaks_ws = self.spreadsheet.worksheet('Bathroom_Breaks')
            breaks = breaks_ws.get_all_records()
            
            for break_record in breaks:
                if (break_record['Break_End'] == '' and 
                    str(break_record['Student_UID']) != str(identifier)):
                    # Get student name for active break
                    active_student = break_record['Student_UID']
                    students_ws = self.spreadsheet.worksheet('Students')
                    students = students_ws.get_all_records()
                    student_name = "Unknown"
                    for student in students:
                        if student['NFC_UID'] == active_student or str(student['Student_ID']) == str(active_student):
                            student_name = student['Name']
                            break
                    return False, f"Another student ({student_name}) is already on a break"
            
            # Get student name and start new break
            student_name = self.get_student_name(identifier)
            next_id = self.get_next_id('Bathroom_Breaks')
            current_time = datetime.now().isoformat()
            new_row = [next_id, identifier, student_name, current_time, '', '']  # End and duration empty
            breaks_ws.append_row(new_row)
            
            return True, "Break started"
            
        except Exception as e:
            print(f"Error starting bathroom break: {e}")
            return False, str(e)
    
    def end_bathroom_break(self, identifier):
        """End a bathroom break for a student"""
        try:
            breaks_ws = self.spreadsheet.worksheet('Bathroom_Breaks')
            breaks = breaks_ws.get_all_records()
            
            # Find active break
            for i, break_record in enumerate(breaks):
                if (str(break_record['Student_UID']) == str(identifier) and 
                    break_record['Break_End'] == ''):
                    
                    # Calculate duration
                    start_time = datetime.fromisoformat(break_record['Break_Start'])
                    end_time = datetime.now()
                    duration = int((end_time - start_time).total_seconds() / 60)
                    
                    # Update the row (i+2 because of header and 0-based index)
                    # Column E is Break_End, Column F is Duration_Minutes (after adding Student_Name)
                    row_num = i + 2
                    breaks_ws.update(values=[[end_time.isoformat(), duration]], range_name=f'E{row_num}:F{row_num}')
                    
                    return True, "Break ended"
            
            return False, "Student is not on a break"
            
        except Exception as e:
            print(f"Error ending bathroom break: {e}")
            return False, str(e)
    
    def is_at_nurse(self, identifier):
        """Check if student is currently at the nurse"""
        try:
            nurse_ws = self.spreadsheet.worksheet('Nurse_Visits')
            visits = nurse_ws.get_all_records()
            
            for visit in visits:
                if (str(visit['Student_UID']) == str(identifier) and 
                    visit['Visit_End'] == ''):
                    return True
            return False
            
        except Exception as e:
            print(f"Error checking nurse status: {e}")
            return False
    
    def has_students_out(self):
        """Check if any students are currently out (on bathroom break or at nurse)"""
        try:
            # Check for active bathroom breaks
            breaks_ws = self.spreadsheet.worksheet('Bathroom_Breaks')
            breaks = breaks_ws.get_all_records()
            
            for break_record in breaks:
                if break_record['Break_End'] == '':  # Active break
                    return True
            
            # Check for active nurse visits
            nurse_ws = self.spreadsheet.worksheet('Nurse_Visits')
            visits = nurse_ws.get_all_records()
            
            for visit in visits:
                if visit['Visit_End'] == '':  # Active visit
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error checking if students are out: {e}")
            return False
    

    def get_students_without_nfc_uid(self):
        """Get list of students who don't have an NFC UID assigned"""
        try:
            worksheet = self.spreadsheet.worksheet('Students')
            students = worksheet.get_all_records()
            
            unassigned_students = []
            for student in students:
                # Check if student has no NFC UID or empty NFC UID
                if not student.get('NFC_UID') or student['NFC_UID'] == '':
                    unassigned_students.append({
                        'student_id': student['Student_ID'],
                        'name': student['Name'],
                        'row_number': students.index(student) + 2  # +2 for header and 0-based index
                    })
            
            return unassigned_students
            
        except Exception as e:
            print(f"Error getting students without NFC UID: {e}")
            return []
    
    def link_nfc_card_to_student(self, nfc_uid, student_id):
        """Link an NFC card UID to a student"""
        try:
            worksheet = self.spreadsheet.worksheet('Students')
            students = worksheet.get_all_records()
            
            # Find the student row
            for i, student in enumerate(students):
                if str(student['Student_ID']) == str(student_id):
                    # Update the NFC_UID field (column A, which is the first column)
                    row_number = i + 2  # +2 for header and 0-based index
                    # Use the correct gspread API syntax
                    worksheet.update(values=[[nfc_uid]], range_name=f'A{row_number}')
                    print(f"Linked NFC UID {nfc_uid} to student {student['Name']} (ID: {student_id})")
                    return True, f"Card linked to {student['Name']}"
            
            return False, "Student not found"
            
        except Exception as e:
            print(f"Error linking NFC card: {e}")
            return False, str(e)
    
    def start_nurse_visit(self, nfc_uid=None, student_id=None):
        """Start a nurse visit for a student"""
        try:
            identifier = self.get_identifier(nfc_uid, student_id)
            if not self.is_checked_in(identifier):
                # Auto-check-in the student first
                print(f"Student {identifier} not checked in, auto-checking in...")
                # Determine if it's an NFC UID or Student ID
                if identifier.startswith('TEST') or len(str(identifier)) > 10:
                    # Looks like NFC UID
                    success, message = self.check_in(nfc_uid=identifier)
                else:
                    # Looks like Student ID
                    success, message = self.check_in(student_id=identifier)
                
                if not success:
                    return False, f"Auto-check-in failed: {message}"
                print(f"Auto-check-in successful: {message}")
            
            # Check if this student has an active nurse visit - if so, end it
            if self.is_at_nurse(identifier):
                print(f"Student {identifier} is already at nurse, ending current visit...")
                success, message = self.end_nurse_visit(nfc_uid=nfc_uid, student_id=student_id)
                if success:
                    print(f"Ended previous nurse visit: {message}")
                    return True, "Previous nurse visit ended, ready for new activities"
                else:
                    return False, f"Failed to end previous nurse visit: {message}"
            
            # Get student name and start new nurse visit
            student_name = self.get_student_name(identifier)
            nurse_ws = self.spreadsheet.worksheet('Nurse_Visits')
            next_id = self.get_next_id('Nurse_Visits')
            current_time = datetime.now().isoformat()
            new_row = [next_id, identifier, student_name, current_time, '', '']  # End and duration empty
            nurse_ws.append_row(new_row)
            
            return True, "Nurse visit started"
            
        except Exception as e:
            print(f"Error starting nurse visit: {e}")
            return False, str(e)
    
    def end_nurse_visit(self, nfc_uid=None, student_id=None):
        """End a nurse visit for a student"""
        try:
            identifier = self.get_identifier(nfc_uid, student_id)
            nurse_ws = self.spreadsheet.worksheet('Nurse_Visits')
            visits = nurse_ws.get_all_records()
            
            # Find active visit
            for i, visit in enumerate(visits):
                if (str(visit['Student_UID']) == str(identifier) and 
                    visit['Visit_End'] == ''):
                    
                    # Calculate duration
                    start_time = datetime.fromisoformat(visit['Visit_Start'])
                    end_time = datetime.now()
                    duration = int((end_time - start_time).total_seconds() / 60)
                    
                    # Update the row (i+2 because of header and 0-based index)
                    # Column E is Visit_End, Column F is Duration_Minutes (after adding Student_Name)
                    row_num = i + 2
                    nurse_ws.update(values=[[end_time.isoformat(), duration]], range_name=f'E{row_num}:F{row_num}')
                    
                    return True, "Nurse visit ended"
            
            return False, "Student is not at the nurse"
            
        except Exception as e:
            print(f"Error ending nurse visit: {e}")
            return False, str(e)
    
    def get_today_attendance(self):
        """Get today's attendance records"""
        try:
            today = datetime.now().date().isoformat()
            
            # Get all students
            students_ws = self.spreadsheet.worksheet('Students')
            students = students_ws.get_all_records()
            
            # Get today's attendance
            attendance_ws = self.spreadsheet.worksheet('Attendance')
            attendance_records = attendance_ws.get_all_records()
            
            results = []
            for student in students:
                student_id = student['Student_ID']
                name = student['Name']
                check_in = None
                check_out = None
                
                # Find attendance record for today
                for record in attendance_records:
                    if (record['Student_UID'] in [student['NFC_UID'], student['Student_ID']] and 
                        record['Date'] == today):
                        if record['Check_In']:
                            check_in = datetime.fromisoformat(record['Check_In'])
                        if record['Check_Out']:
                            check_out = datetime.fromisoformat(record['Check_Out'])
                        break
                
                results.append((student_id, name, check_in, check_out))
            
            return results
            
        except Exception as e:
            print(f"Error getting today's attendance: {e}")
            return []
    
    def get_today_breaks(self):
        """Get all bathroom breaks for today"""
        try:
            today = datetime.now().date().isoformat()
            
            breaks_ws = self.spreadsheet.worksheet('Bathroom_Breaks')
            breaks = breaks_ws.get_all_records()
            
            students_ws = self.spreadsheet.worksheet('Students')
            students = students_ws.get_all_records()
            
            results = []
            for break_record in breaks:
                if break_record['Break_Start']:
                    start_date = datetime.fromisoformat(break_record['Break_Start']).date().isoformat()
                    if start_date == today:
                        # Find student name
                        student_name = "Unknown"
                        for student in students:
                            if student['NFC_UID'] == break_record['Student_UID'] or str(student['Student_ID']) == str(break_record['Student_UID']):
                                student_name = student['Name']
                                break
                        
                        start_time = datetime.fromisoformat(break_record['Break_Start'])
                        end_time = datetime.fromisoformat(break_record['Break_End']) if break_record['Break_End'] else None
                        duration = break_record['Duration_Minutes'] if break_record['Duration_Minutes'] else None
                        
                        results.append((student_name, start_time, end_time, duration))
            
            return results
            
        except Exception as e:
            print(f"Error getting today's breaks: {e}")
            return []
    
    def get_today_nurse_visits(self):
        """Get all nurse visits for today"""
        try:
            today = datetime.now().date().isoformat()
            
            nurse_ws = self.spreadsheet.worksheet('Nurse_Visits')
            visits = nurse_ws.get_all_records()
            
            students_ws = self.spreadsheet.worksheet('Students')
            students = students_ws.get_all_records()
            
            results = []
            for visit in visits:
                if visit['Visit_Start']:
                    start_date = datetime.fromisoformat(visit['Visit_Start']).date().isoformat()
                    if start_date == today:
                        # Find student name
                        student_name = "Unknown"
                        for student in students:
                            if student['NFC_UID'] == visit['Student_UID'] or str(student['Student_ID']) == str(visit['Student_UID']):
                                student_name = student['Name']
                                break
                        
                        start_time = datetime.fromisoformat(visit['Visit_Start'])
                        end_time = datetime.fromisoformat(visit['Visit_End']) if visit['Visit_End'] else None
                        duration = visit['Duration_Minutes'] if visit['Duration_Minutes'] else None
                        
                        results.append((student_name, start_time, end_time, duration))
            
            return results
            
        except Exception as e:
            print(f"Error getting today's nurse visits: {e}")
            return []
    
    def auto_checkout_students(self):
        """Automatically check out students whose scheduled_check_out time has passed"""
        try:
            now = datetime.now()
            today = now.date().isoformat()
            
            attendance_ws = self.spreadsheet.worksheet('Attendance')
            attendance_records = attendance_ws.get_all_records()
            
            for i, record in enumerate(attendance_records):
                if (record['Date'] == today and 
                    record['Check_Out'] == '' and 
                    record['Scheduled_Check_Out']):
                    
                    try:
                        scheduled_dt = datetime.fromisoformat(record['Scheduled_Check_Out'])
                        if scheduled_dt <= now:
                            # Update check-out time (i+2 because of header and 0-based index)
                            # Column F is Check_Out (after adding Student_Name)
                            row_num = i + 2
                            attendance_ws.update(values=[[now.isoformat()]], range_name=f'F{row_num}')
                            print(f"Auto-checked out student: {record['Student_UID']}")
                    except Exception as e:
                        print(f"Error processing scheduled checkout for {record['Student_UID']}: {e}")
                        continue
                        
        except Exception as e:
            print(f"Error in auto-checkout: {e}")
    
    def import_from_csv(self, csv_file):
        """Import students from CSV file"""
        # For now, return a placeholder - can be implemented later if needed
        return {"success": 0, "failed": 0, "errors": ["CSV import not yet implemented for Google Sheets"]}
    
    def import_from_json(self, json_file):
        """Import students from JSON file"""
        # For now, return a placeholder - can be implemented later if needed
        return {"success": 0, "failed": 0, "errors": ["JSON import not yet implemented for Google Sheets"]}


if __name__ == "__main__":
    # Test the Google Sheets database
    print("Testing Google Sheets Database...")
    
    try:
        db = GoogleSheetsDatabase()
        print("✅ Successfully connected to Google Sheets!")
        
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
        
        print("🎉 Google Sheets integration working!")
        
    except Exception as e:
        print(f"❌ Error testing Google Sheets: {e}")