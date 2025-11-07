// Analytics Logic

// Require authentication
requireAuth();

// Display user email
checkAuthState((user) => {
  if (user) {
    document.getElementById('userEmail').textContent = user.email;
  }
});

// Set default dates (last 7 days)
const today = new Date();
const weekAgo = new Date(today);
weekAgo.setDate(weekAgo.getDate() - 7);

// Get today's date in YYYY-MM-DD format (local timezone)
function getTodayDateLocal() {
  const d = new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

// Get date 7 days ago
function getWeekAgoDate() {
  const d = new Date();
  d.setDate(d.getDate() - 7);
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

document.getElementById('startDate').value = getWeekAgoDate();
document.getElementById('endDate').value = getTodayDateLocal();

let analyticsData = {
  breaks: [],
  nurses: []
};

// Load students for filter
async function loadStudents() {
  try {
    const snapshot = await db.collection('students').get();
    const select = document.getElementById('filterStudent');
    
    const students = [];
    snapshot.forEach((doc) => {
      const data = doc.data();
      students.push({
        uid: doc.id,
        student_id: data.student_id,
        name: data.name
      });
    });
    
    // Sort by name
    students.sort((a, b) => a.name.localeCompare(b.name));
    
    // Add options to select
    students.forEach(student => {
      const option = document.createElement('option');
      option.value = student.uid;
      option.textContent = `${student.name} (${student.student_id})`;
      select.appendChild(option);
    });
    
    console.log('[ANALYTICS] Loaded', students.length, 'students');
  } catch (error) {
    console.error('Error loading students:', error);
  }
}

// Load students on page load
loadStudents();

// Load analytics data
async function loadAnalytics() {
  const startDate = document.getElementById('startDate').value;
  const endDate = document.getElementById('endDate').value;
  const filterStudent = document.getElementById('filterStudent').value;

  if (!startDate || !endDate) {
    alert('Please select both start and end dates');
    return;
  }

  try {
    // Load bathroom breaks
    const breaksSnapshot = await db.collection('bathroom_breaks').get();
    analyticsData.breaks = [];
    breaksSnapshot.forEach((doc) => {
      const data = doc.data();
      if (data.break_start) {
        const breakDate = data.break_start.split('T')[0];
        if (breakDate >= startDate && breakDate <= endDate) {
          // Filter by student if selected
          if (!filterStudent || data.student_uid === filterStudent) {
            analyticsData.breaks.push(data);
          }
        }
      }
    });

    // Load nurse visits
    const nurseSnapshot = await db.collection('nurse_visits').get();
    analyticsData.nurses = [];
    nurseSnapshot.forEach((doc) => {
      const data = doc.data();
      if (data.visit_start) {
        const visitDate = data.visit_start.split('T')[0];
        if (visitDate >= startDate && visitDate <= endDate) {
          // Filter by student if selected
          if (!filterStudent || data.student_uid === filterStudent) {
            analyticsData.nurses.push(data);
          }
        }
      }
    });

    // Calculate and display statistics
    const studentName = filterStudent ? document.getElementById('filterStudent').selectedOptions[0].textContent : 'All Students';
    console.log('[ANALYTICS] Loaded data for:', studentName, 'Breaks:', analyticsData.breaks.length, 'Visits:', analyticsData.nurses.length);
    displayStatistics();
    displayBreaksBreakdown();
    displayNurseBreakdown();
    displayDetailedBreaks();
    displayDetailedNurseVisits();

  } catch (error) {
    console.error('Error loading analytics:', error);
    alert('Failed to load analytics data');
  }
}

// Display summary statistics
function displayStatistics() {
  const completedBreaks = analyticsData.breaks.filter(b => b.duration_minutes);
  const totalBreaks = analyticsData.breaks.length;
  const avgBreakTime = completedBreaks.length > 0
    ? Math.round(completedBreaks.reduce((sum, b) => sum + parseInt(b.duration_minutes || 0), 0) / completedBreaks.length)
    : 0;

  const completedNurse = analyticsData.nurses.filter(n => n.duration_minutes);
  const totalNurse = analyticsData.nurses.length;
  const avgNurseTime = completedNurse.length > 0
    ? Math.round(completedNurse.reduce((sum, n) => sum + parseInt(n.duration_minutes || 0), 0) / completedNurse.length)
    : 0;

  document.getElementById('totalBreaks').textContent = totalBreaks;
  document.getElementById('avgBreakTime').textContent = avgBreakTime;
  document.getElementById('totalNurseVisits').textContent = totalNurse;
  document.getElementById('avgNurseTime').textContent = avgNurseTime;
}

// Display bathroom breaks breakdown by student
function displayBreaksBreakdown() {
  const filterStudent = document.getElementById('filterStudent').value;
  const breakdown = {};

  analyticsData.breaks.forEach(breakRecord => {
    const name = breakRecord.student_name || 'Unknown';
    if (!breakdown[name]) {
      breakdown[name] = {
        count: 0,
        totalTime: 0,
        completedCount: 0
      };
    }
    breakdown[name].count++;
    if (breakRecord.duration_minutes && breakRecord.duration_minutes > 0) {
      breakdown[name].totalTime += parseInt(breakRecord.duration_minutes);
      breakdown[name].completedCount++;
    }
  });

  const tbody = document.getElementById('breaksBreakdownBody');
  const rows = Object.entries(breakdown).map(([name, data]) => ({
    name,
    count: data.count,
    totalTime: data.totalTime,
    avgTime: data.completedCount > 0 ? Math.round(data.totalTime / data.completedCount) : 0
  }));

  // Sort by count descending
  rows.sort((a, b) => b.count - a.count);

  if (rows.length === 0) {
    const message = filterStudent ? 'No bathroom breaks for this student in this date range' : 'No bathroom breaks in this date range';
    tbody.innerHTML = `<tr><td colspan="4" class="empty-state">${message}</td></tr>`;
  } else {
    tbody.innerHTML = rows.map(row => `
      <tr>
        <td>${row.name}</td>
        <td>${row.count}</td>
        <td>${row.totalTime}</td>
        <td>${row.avgTime}</td>
      </tr>
    `).join('');
  }
}

// Display nurse visits breakdown by student
function displayNurseBreakdown() {
  const filterStudent = document.getElementById('filterStudent').value;
  const breakdown = {};

  analyticsData.nurses.forEach(visit => {
    const name = visit.student_name || 'Unknown';
    if (!breakdown[name]) {
      breakdown[name] = {
        count: 0,
        totalTime: 0,
        completedCount: 0
      };
    }
    breakdown[name].count++;
    if (visit.duration_minutes && visit.duration_minutes > 0) {
      breakdown[name].totalTime += parseInt(visit.duration_minutes);
      breakdown[name].completedCount++;
    }
  });

  const tbody = document.getElementById('nurseBreakdownBody');
  const rows = Object.entries(breakdown).map(([name, data]) => ({
    name,
    count: data.count,
    totalTime: data.totalTime,
    avgTime: data.completedCount > 0 ? Math.round(data.totalTime / data.completedCount) : 0
  }));

  // Sort by count descending
  rows.sort((a, b) => b.count - a.count);

  if (rows.length === 0) {
    const message = filterStudent ? 'No nurse visits for this student in this date range' : 'No nurse visits in this date range';
    tbody.innerHTML = `<tr><td colspan="4" class="empty-state">${message}</td></tr>`;
  } else {
    tbody.innerHTML = rows.map(row => `
      <tr>
        <td>${row.name}</td>
        <td>${row.count}</td>
        <td>${row.totalTime}</td>
        <td>${row.avgTime}</td>
      </tr>
    `).join('');
  }
}

// Export data to CSV
function exportData() {
  const startDate = document.getElementById('startDate').value;
  const endDate = document.getElementById('endDate').value;
  const filterStudent = document.getElementById('filterStudent').value;

  if (analyticsData.breaks.length === 0 && analyticsData.nurses.length === 0) {
    alert('No data to export. Please load analytics first.');
    return;
  }

  // Create CSV content
  let csv = 'Type,Student,Start Time,End Time,Duration (min)\n';

  analyticsData.breaks.forEach(breakRecord => {
    csv += `Bathroom Break,${breakRecord.student_name || 'Unknown'},${breakRecord.break_start},${breakRecord.break_end || 'Active'},${breakRecord.duration_minutes || 'N/A'}\n`;
  });

  analyticsData.nurses.forEach(visit => {
    csv += `Nurse Visit,${visit.student_name || 'Unknown'},${visit.visit_start},${visit.visit_end || 'Active'},${visit.duration_minutes || 'N/A'}\n`;
  });

  // Create filename with student name if filtered
  let filename = `hallpass_analytics_${startDate}_to_${endDate}`;
  if (filterStudent) {
    const studentName = document.getElementById('filterStudent').selectedOptions[0].textContent.split(' (')[0];
    filename += `_${studentName.replace(/\s+/g, '_')}`;
  }
  filename += '.csv';

  // Create blob and download
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
}

// Format date for display (YYYY-MM-DD)
function formatDate(timestamp) {
  if (!timestamp) return '-';
  return timestamp.substring(0, 10);
}

// Format time for display (HH:MM AM/PM)
function formatTime(timestamp) {
  if (!timestamp) return '-';
  const date = new Date(timestamp);
  return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
}

// Format full datetime for display
function formatDateTime(timestamp) {
  if (!timestamp) return '-';
  const date = new Date(timestamp);
  return date.toLocaleString('en-US', { 
    month: 'short', 
    day: 'numeric', 
    hour: 'numeric', 
    minute: '2-digit' 
  });
}

// Display detailed bathroom breaks
function displayDetailedBreaks() {
  const tbody = document.getElementById('detailedBreaksBody');
  const filterStudent = document.getElementById('filterStudent').value;
  
  if (analyticsData.breaks.length === 0) {
    const message = filterStudent ? 'No bathroom breaks for this student in this date range' : 'No bathroom breaks in this date range';
    tbody.innerHTML = `<tr><td colspan="5" class="empty-state">${message}</td></tr>`;
    return;
  }
  
  // Sort by start time (newest first)
  const sortedBreaks = [...analyticsData.breaks].sort((a, b) => {
    return new Date(b.break_start) - new Date(a.break_start);
  });
  
  tbody.innerHTML = sortedBreaks.map(breakRecord => `
    <tr>
      <td>${formatDate(breakRecord.break_start)}</td>
      <td>${breakRecord.student_name || 'Unknown'}</td>
      <td>${formatTime(breakRecord.break_start)}</td>
      <td>${breakRecord.break_end ? formatTime(breakRecord.break_end) : 'Active'}</td>
      <td>${breakRecord.duration_minutes !== null && breakRecord.duration_minutes !== undefined ? breakRecord.duration_minutes : '-'}</td>
    </tr>
  `).join('');
}

// Display detailed nurse visits
function displayDetailedNurseVisits() {
  const tbody = document.getElementById('detailedNurseBody');
  const filterStudent = document.getElementById('filterStudent').value;
  
  if (analyticsData.nurses.length === 0) {
    const message = filterStudent ? 'No nurse visits for this student in this date range' : 'No nurse visits in this date range';
    tbody.innerHTML = `<tr><td colspan="5" class="empty-state">${message}</td></tr>`;
    return;
  }
  
  // Sort by start time (newest first)
  const sortedVisits = [...analyticsData.nurses].sort((a, b) => {
    return new Date(b.visit_start) - new Date(a.visit_start);
  });
  
  tbody.innerHTML = sortedVisits.map(visit => `
    <tr>
      <td>${formatDate(visit.visit_start)}</td>
      <td>${visit.student_name || 'Unknown'}</td>
      <td>${formatTime(visit.visit_start)}</td>
      <td>${visit.visit_end ? formatTime(visit.visit_end) : 'Active'}</td>
      <td>${visit.duration_minutes !== null && visit.duration_minutes !== undefined ? visit.duration_minutes : '-'}</td>
    </tr>
  `).join('');
}

// Load data on page load
loadAnalytics();

