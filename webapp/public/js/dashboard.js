// Dashboard Logic

// Require authentication
requireAuth();

// Display user email
checkAuthState((user) => {
  if (user) {
    document.getElementById('userEmail').textContent = user.email;
  }
});

// School periods configuration
const PERIODS = [
  { name: 'Period 1', start: { h: 7, m: 25 }, end: { h: 8, m: 8 } },
  { name: 'Period 2', start: { h: 8, m: 12 }, end: { h: 8, m: 55 } },
  { name: 'Homeroom', start: { h: 8, m: 55 }, end: { h: 9, m: 1 } },
  { name: 'Period 3', start: { h: 9, m: 5 }, end: { h: 9, m: 48 } },
  { name: 'Period 4', start: { h: 9, m: 52 }, end: { h: 10, m: 35 } },
  { name: 'Period 5', start: { h: 10, m: 39 }, end: { h: 11, m: 22 } },
  { name: 'Period 6', start: { h: 11, m: 26 }, end: { h: 12, m: 9 } },
  { name: 'Period 7', start: { h: 12, m: 13 }, end: { h: 12, m: 56 } },
  { name: 'Period 8', start: { h: 13, m: 0 }, end: { h: 13, m: 43 } },
  { name: 'Period 9', start: { h: 13, m: 47 }, end: { h: 14, m: 30 } }
];

function getCurrentPeriod() {
  const now = new Date();
  const currentMinutes = now.getHours() * 60 + now.getMinutes();

  for (let i = 0; i < PERIODS.length; i++) {
    const period = PERIODS[i];
    const startMinutes = period.start.h * 60 + period.start.m;
    const endMinutes = period.end.h * 60 + period.end.m;

    if (currentMinutes >= startMinutes && currentMinutes < endMinutes) {
      return period.name;
    }

    // Check for passing period
    if (i < PERIODS.length - 1) {
      const nextPeriod = PERIODS[i + 1];
      const nextStartMinutes = nextPeriod.start.h * 60 + nextPeriod.start.m;
      if (currentMinutes >= endMinutes && currentMinutes < nextStartMinutes) {
        return 'Passing Period';
      }
    }
  }

  // Before school starts
  const firstPeriodStart = PERIODS[0].start.h * 60 + PERIODS[0].start.m;
  if (currentMinutes < firstPeriodStart) {
    return 'Before School';
  }

  // After school ends
  return 'After School';
}

// Update current period
function updateCurrentPeriod() {
  const period = getCurrentPeriod();
  document.getElementById('currentPeriod').textContent = period;
}

// Update period every minute
updateCurrentPeriod();
setInterval(updateCurrentPeriod, 60000);

// Get today's date in YYYY-MM-DD format
function getTodayDate() {
  const today = new Date();
  return today.toISOString().split('T')[0];
}

// Format time for display
function formatTime(timestamp) {
  if (!timestamp) return '-';
  const date = new Date(timestamp);
  return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
}

// Calculate duration in minutes
function calculateDuration(start, end = null) {
  const startTime = new Date(start);
  const endTime = end ? new Date(end) : new Date();
  return Math.floor((endTime - startTime) / 1000 / 60);
}

// Listen for students currently on bathroom breaks
db.collection('bathroom_breaks')
  .where('break_end', '==', '')
  .onSnapshot((snapshot) => {
    const studentsOut = [];
    snapshot.forEach((doc) => {
      const data = doc.data();
      studentsOut.push({
        name: data.student_name,
        type: 'Bathroom',
        start: data.break_start,
        duration: calculateDuration(data.break_start)
      });
    });

    // Also get nurse visits
    db.collection('nurse_visits')
      .where('visit_end', '==', '')
      .onSnapshot((nurseSnapshot) => {
        nurseSnapshot.forEach((doc) => {
          const data = doc.data();
          studentsOut.push({
            name: data.student_name,
            type: 'Nurse',
            start: data.visit_start,
            duration: calculateDuration(data.visit_start)
          });
        });

        // Update students out count
        document.getElementById('studentsOutCount').textContent = studentsOut.length;

        // Update students out list
        const listContainer = document.getElementById('studentsOutList');
        if (studentsOut.length === 0) {
          listContainer.innerHTML = '<div class="empty-state"><p>No students currently out</p></div>';
        } else {
          listContainer.innerHTML = studentsOut.map(student => `
            <div style="padding: 0.75rem; border-bottom: 1px solid var(--border-color);">
              <strong>${student.name}</strong> - ${student.type}<br>
              <small>Out for ${student.duration} minutes</small>
            </div>
          `).join('');
        }
      });
  });

// Get today's statistics
const today = getTodayDate();

// Total bathroom breaks today
db.collection('bathroom_breaks')
  .onSnapshot((snapshot) => {
    const todayBreaks = [];
    snapshot.forEach((doc) => {
      const data = doc.data();
      if (data.break_start && data.break_start.startsWith(today)) {
        todayBreaks.push(data);
      }
    });

    document.getElementById('totalBreaksToday').textContent = todayBreaks.length;

    // Calculate average duration
    const completedBreaks = todayBreaks.filter(b => b.duration_minutes);
    if (completedBreaks.length > 0) {
      const avgDuration = completedBreaks.reduce((sum, b) => sum + parseInt(b.duration_minutes || 0), 0) / completedBreaks.length;
      document.getElementById('avgBreakDuration').textContent = Math.round(avgDuration);
    } else {
      document.getElementById('avgBreakDuration').textContent = '0';
    }
  });

// Total nurse visits today
db.collection('nurse_visits')
  .onSnapshot((snapshot) => {
    let todayVisits = 0;
    snapshot.forEach((doc) => {
      const data = doc.data();
      if (data.visit_start && data.visit_start.startsWith(today)) {
        todayVisits++;
      }
    });

    document.getElementById('totalNurseVisits').textContent = todayVisits;
  });

// Recent activity
function loadRecentActivity() {
  const recentActivityBody = document.getElementById('recentActivityBody');
  const activities = [];

  // Get bathroom breaks
  db.collection('bathroom_breaks')
    .orderBy('break_start', 'desc')
    .limit(10)
    .get()
    .then((snapshot) => {
      snapshot.forEach((doc) => {
        const data = doc.data();
        if (data.break_start && data.break_start.startsWith(today)) {
          activities.push({
            name: data.student_name,
            type: 'Bathroom',
            start: data.break_start,
            status: data.break_end ? 'Ended' : 'Active'
          });
        }
      });

      // Get nurse visits
      db.collection('nurse_visits')
        .orderBy('visit_start', 'desc')
        .limit(10)
        .get()
        .then((nurseSnapshot) => {
          nurseSnapshot.forEach((doc) => {
            const data = doc.data();
            if (data.visit_start && data.visit_start.startsWith(today)) {
              activities.push({
                name: data.student_name,
                type: 'Nurse',
                start: data.visit_start,
                status: data.visit_end ? 'Ended' : 'Active'
              });
            }
          });

          // Sort by start time
          activities.sort((a, b) => new Date(b.start) - new Date(a.start));

          // Display activities
          if (activities.length === 0) {
            recentActivityBody.innerHTML = '<tr><td colspan="4" class="empty-state">No activity today</td></tr>';
          } else {
            recentActivityBody.innerHTML = activities.slice(0, 10).map(activity => `
              <tr>
                <td>${activity.name}</td>
                <td>${activity.type}</td>
                <td>${formatTime(activity.start)}</td>
                <td><span class="badge ${activity.status === 'Active' ? 'badge-active' : 'badge-ended'}">${activity.status}</span></td>
              </tr>
            `).join('');
          }
        });
    });
}

loadRecentActivity();

