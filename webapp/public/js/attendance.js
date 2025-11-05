// Attendance Logic

// Require authentication
requireAuth();

// Display user email
checkAuthState((user) => {
  if (user) {
    document.getElementById('userEmail').textContent = user.email;
  }
});

// Set default date to today
document.getElementById('filterDate').value = new Date().toISOString().split('T')[0];

let allAttendance = [];
let allStudents = [];

// Load students for filter
async function loadStudents() {
  const snapshot = await db.collection('students').get();
  const select = document.getElementById('filterStudent');
  
  snapshot.forEach((doc) => {
    const data = doc.data();
    allStudents.push(data);
    const option = document.createElement('option');
    option.value = data.student_id;
    option.textContent = `${data.name} (${data.student_id})`;
    select.appendChild(option);
  });
}

// Format time for display
function formatTime(timestamp) {
  if (!timestamp) return '-';
  const date = new Date(timestamp);
  return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
}

// Calculate duration in minutes
function calculateDuration(checkIn, checkOut) {
  if (!checkIn || !checkOut) return '-';
  const start = new Date(checkIn);
  const end = new Date(checkOut);
  return Math.floor((end - start) / 1000 / 60);
}

// Load attendance records
async function loadAttendance() {
  const filterDate = document.getElementById('filterDate').value;
  const filterStudent = document.getElementById('filterStudent').value;

  if (!filterDate) {
    alert('Please select a date');
    return;
  }

  try {
    const snapshot = await db.collection('attendance')
      .where('date', '==', filterDate)
      .get();

    allAttendance = [];
    snapshot.forEach((doc) => {
      const data = doc.data();
      allAttendance.push(data);
    });

    // Filter by student if selected
    let filteredAttendance = allAttendance;
    if (filterStudent) {
      filteredAttendance = allAttendance.filter(a => a.student_uid === filterStudent);
    }

    displayAttendance(filteredAttendance);

  } catch (error) {
    console.error('Error loading attendance:', error);
    alert('Failed to load attendance records');
  }
}

// Display attendance records
function displayAttendance(records) {
  const tbody = document.getElementById('attendanceTableBody');

  if (records.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No attendance records found</td></tr>';
    return;
  }

  // Sort by check-in time
  records.sort((a, b) => {
    if (!a.check_in) return 1;
    if (!b.check_in) return -1;
    return new Date(b.check_in) - new Date(a.check_in);
  });

  tbody.innerHTML = records.map(record => `
    <tr>
      <td>${record.student_name || 'Unknown'}</td>
      <td>${record.date || '-'}</td>
      <td>${formatTime(record.check_in)}</td>
      <td>${formatTime(record.check_out)}</td>
      <td>${formatTime(record.scheduled_check_out)}</td>
      <td>${calculateDuration(record.check_in, record.check_out)}</td>
    </tr>
  `).join('');
}

// Export attendance to CSV
function exportAttendance() {
  const filterDate = document.getElementById('filterDate').value;

  if (allAttendance.length === 0) {
    alert('No data to export. Please load attendance records first.');
    return;
  }

  // Create CSV content
  let csv = 'Student,Date,Check In,Check Out,Scheduled Check Out,Duration (min)\n';

  allAttendance.forEach(record => {
    const duration = calculateDuration(record.check_in, record.check_out);
    csv += `"${record.student_name || 'Unknown'}",${record.date},${record.check_in || ''},${record.check_out || ''},${record.scheduled_check_out || ''},${duration}\n`;
  });

  // Create blob and download
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `attendance_${filterDate}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
}

// Load data on page load
loadStudents();
loadAttendance();

