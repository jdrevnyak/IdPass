# NFC Card Linking Feature

## Overview
When a user taps an NFC card that doesn't have a student assigned to it, the system now automatically shows a list of students without NFC cards and allows the user to link the card to a selected student.

## How It Works

### 1. Unknown Card Detection
- User taps an NFC card
- System checks if the card UID exists in the database
- If no student is found, the system checks for students without NFC UIDs

### 2. Student Selection Overlay
If students without NFC UIDs are found:
- Shows "Link NFC Card to Student" overlay
- Displays the NFC card UID
- Shows dropdown list of students without cards
- User can select a student and link the card

### 3. Card Linking Process
- User selects a student from the dropdown
- Clicks "Link Card" button
- System updates the Google Sheets database
- Card UID is assigned to the selected student
- Success message is shown

### 4. Automatic Check-in
After successful linking:
- System automatically attempts to check in the student
- Shows check-in result message
- LED status is updated if needed

## User Interface

### Student Selection Overlay
- **Title**: "Link NFC Card to Student"
- **NFC UID Display**: Shows the card's UID
- **Instructions**: "Select a student to link this card to:"
- **Student Dropdown**: List of students without NFC cards
- **Buttons**: 
  - Cancel (red) - Closes overlay without linking
  - Link Card (green) - Links card to selected student

### Student List Format
Each student is displayed as: `"Student Name (ID: Student_ID)"`

## Database Changes

### New Methods Added to GoogleSheetsDatabase:

1. **`get_students_without_nfc_uid()`**
   - Returns list of students with empty or missing NFC_UID
   - Returns student data: name, student_id, row_number

2. **`link_nfc_card_to_student(nfc_uid, student_id)`**
   - Updates the NFC_UID field for the selected student
   - Returns success/failure status and message

## Error Handling

### No Unassigned Students
If no students without NFC UIDs are found:
- Shows message: "Unknown Student (UID: {uid})\nNo unassigned students available"
- No overlay is shown

### Linking Failures
If card linking fails:
- Shows error dialog with failure reason
- Overlay remains open for retry

### Check-in Failures
If auto check-in fails after linking:
- Shows message with check-in error
- Card is still linked successfully

## Benefits

1. **Easy Card Assignment**: No need to manually edit Google Sheets
2. **Immediate Use**: Cards can be used right after linking
3. **User-Friendly**: Simple dropdown selection interface
4. **Automatic Check-in**: Students are checked in immediately after linking
5. **Error Prevention**: Validates student selection before linking

## Usage Example

1. **Student taps new card** → "Unknown Card (UID: 123456)\nSelecting student to link..."
2. **Overlay appears** → Shows list of students without cards
3. **User selects student** → "John Smith (ID: 123456)" from dropdown
4. **User clicks "Link Card"** → Card is linked to John Smith
5. **Success message** → "Card successfully linked to John Smith!"
6. **Auto check-in** → "Card linked to John Smith\nStudent checked in successfully!"

## Technical Details

### Signal System
- `card_linked` signal emitted on successful linking
- Signal carries `nfc_uid` and `student_name`
- Main GUI handles signal to trigger auto check-in

### Database Updates
- Updates Google Sheets 'Students' worksheet
- Modifies NFC_UID column for selected student
- Maintains data integrity with error checking

### UI Integration
- Seamlessly integrates with existing overlay system
- Consistent styling with other overlays
- Proper cleanup and state management
