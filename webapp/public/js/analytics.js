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

document.getElementById('startDate').value = weekAgo.toISOString().split('T')[0];
document.getElementById('endDate').value = today.toISOString().split('T')[0];

let analyticsData = {
  breaks: [],
  nurses: []
};

// Load analytics data
async function loadAnalytics() {
  const startDate = document.getElementById('startDate').value;
  const endDate = document.getElementById('endDate').value;

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
          analyticsData.breaks.push(data);
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
          analyticsData.nurses.push(data);
        }
      }
    });

    // Calculate and display statistics
    displayStatistics();
    displayBreaksBreakdown();
    displayNurseBreakdown();

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
    if (breakRecord.duration_minutes) {
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
    tbody.innerHTML = '<tr><td colspan="4" class="empty-state">No bathroom breaks in this date range</td></tr>';
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
    if (visit.duration_minutes) {
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
    tbody.innerHTML = '<tr><td colspan="4" class="empty-state">No nurse visits in this date range</td></tr>';
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

  // Create blob and download
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `hallpass_analytics_${startDate}_to_${endDate}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
}

// Load data on page load
loadAnalytics();

