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

// Get today's date in YYYY-MM-DD format (local timezone)
function getTodayDate() {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, '0');
  const day = String(today.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
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

// Track active breaks for end all functionality
let activeBreaksData = {
  bathroom: [],
  nurse: [],
  water: []
};

// Function to update button visibility
function updateEndAllButton() {
  const totalActive = activeBreaksData.bathroom.length + 
                      activeBreaksData.nurse.length + 
                      activeBreaksData.water.length;
  const btn = document.getElementById('endAllBreaksBtn');
  if (btn) {
    btn.style.display = totalActive > 0 ? 'block' : 'none';
  }
}

// Function to end all active breaks
async function endAllActiveBreaks() {
  const totalActive = activeBreaksData.bathroom.length + 
                      activeBreaksData.nurse.length + 
                      activeBreaksData.water.length;
  
  if (totalActive === 0) {
    alert('No active breaks to end');
    return;
  }

  const confirmMsg = `Are you sure you want to end all ${totalActive} active break(s) and visit(s)?\n\n` +
    `This will end:\n` +
    `- ${activeBreaksData.bathroom.length} bathroom break(s)\n` +
    `- ${activeBreaksData.nurse.length} nurse visit(s)\n` +
    `- ${activeBreaksData.water.length} water visit(s)`;
  
  if (!confirm(confirmMsg)) {
    return;
  }

  const btn = document.getElementById('endAllBreaksBtn');
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Ending...';
  }

  const endTime = new Date().toISOString();
  let successCount = 0;
  let errorCount = 0;
  const errors = [];

  try {
    // End bathroom breaks
    for (const doc of activeBreaksData.bathroom) {
      try {
        const data = doc.data();
        const startTime = new Date(data.break_start);
        const duration = Math.floor((new Date(endTime) - startTime) / 1000 / 60);
        
        await doc.ref.update({
          break_end: endTime,
          duration_minutes: duration
        });
        successCount++;
      } catch (error) {
        errorCount++;
        errors.push(`Bathroom break (${doc.id}): ${error.message}`);
      }
    }

    // End nurse visits
    for (const doc of activeBreaksData.nurse) {
      try {
        const data = doc.data();
        const startTime = new Date(data.visit_start);
        const duration = Math.floor((new Date(endTime) - startTime) / 1000 / 60);
        
        await doc.ref.update({
          visit_end: endTime,
          duration_minutes: duration
        });
        successCount++;
      } catch (error) {
        errorCount++;
        errors.push(`Nurse visit (${doc.id}): ${error.message}`);
      }
    }

    // End water visits
    for (const doc of activeBreaksData.water) {
      try {
        const data = doc.data();
        const startTime = new Date(data.visit_start);
        const duration = Math.floor((new Date(endTime) - startTime) / 1000 / 60);
        
        await doc.ref.update({
          visit_end: endTime,
          duration_minutes: duration
        });
        successCount++;
      } catch (error) {
        errorCount++;
        errors.push(`Water visit (${doc.id}): ${error.message}`);
      }
    }

    if (errorCount > 0) {
      alert(`Ended ${successCount} break(s)/visit(s) successfully.\n\n` +
            `Failed to end ${errorCount}:\n${errors.join('\n')}`);
    } else {
      alert(`Successfully ended all ${successCount} active break(s) and visit(s).`);
    }
  } catch (error) {
    console.error('Error ending all breaks:', error);
    alert(`Error ending breaks: ${error.message}`);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'End All Active Breaks';
    }
  }
}

// Attach click handler to button (script runs after DOM is loaded)
const endAllBreaksBtn = document.getElementById('endAllBreaksBtn');
if (endAllBreaksBtn) {
  endAllBreaksBtn.addEventListener('click', endAllActiveBreaks);
}

// Function to update students out display
function updateStudentsOutDisplay() {
  const studentsOut = [];
  
  // Add bathroom breaks
  activeBreaksData.bathroom.forEach((doc) => {
    const data = doc.data();
    studentsOut.push({
      name: data.student_name,
      type: 'Bathroom',
      start: data.break_start,
      duration: calculateDuration(data.break_start)
    });
  });
  
  // Add nurse visits
  activeBreaksData.nurse.forEach((doc) => {
    const data = doc.data();
    studentsOut.push({
      name: data.student_name,
      type: 'Nurse',
      start: data.visit_start,
      duration: calculateDuration(data.visit_start)
    });
  });
  
  // Add water visits
  activeBreaksData.water.forEach((doc) => {
    const data = doc.data();
    studentsOut.push({
      name: data.student_name,
      type: 'Water',
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

  // Update button visibility
  updateEndAllButton();
}

// Listen for students currently on bathroom breaks
db.collection('bathroom_breaks')
  .where('break_end', '==', null)
  .onSnapshot((snapshot) => {
    activeBreaksData.bathroom = [];
    snapshot.forEach((doc) => {
      activeBreaksData.bathroom.push(doc);
    });
    updateStudentsOutDisplay();
  });

// Listen for nurse visits
db.collection('nurse_visits')
  .where('visit_end', '==', null)
  .onSnapshot((snapshot) => {
    activeBreaksData.nurse = [];
    snapshot.forEach((doc) => {
      activeBreaksData.nurse.push(doc);
    });
    updateStudentsOutDisplay();
  });

// Listen for water visits
db.collection('water_visits')
  .where('visit_end', '==', null)
  .onSnapshot((snapshot) => {
    activeBreaksData.water = [];
    snapshot.forEach((doc) => {
      activeBreaksData.water.push(doc);
    });
    updateStudentsOutDisplay();
  });

// Get today's statistics
const today = getTodayDate();
console.log('[DASHBOARD] Today\'s date:', today);

// Total bathroom breaks today
db.collection('bathroom_breaks')
  .onSnapshot((snapshot) => {
    console.log('[DASHBOARD] Bathroom breaks snapshot received, total docs:', snapshot.size);
    const todayBreaks = [];
    snapshot.forEach((doc) => {
      const data = doc.data();
      console.log('[DASHBOARD] Break doc:', doc.id, 'data:', data);
      // Check if break_start exists and matches today's date
      if (data.break_start) {
        const breakDate = data.break_start.substring(0, 10); // Extract YYYY-MM-DD
        console.log('[DASHBOARD] Break date:', breakDate, 'vs today:', today, 'match:', breakDate === today);
        if (breakDate === today) {
          todayBreaks.push(data);
        }
      }
    });
    console.log('[DASHBOARD] Today\'s breaks count:', todayBreaks.length);

    document.getElementById('totalBreaksToday').textContent = todayBreaks.length;

    // Calculate average duration (excluding null and 0 durations)
    const completedBreaks = todayBreaks.filter(b => b.duration_minutes && b.duration_minutes > 0);
    if (completedBreaks.length > 0) {
      const avgDuration = completedBreaks.reduce((sum, b) => sum + parseInt(b.duration_minutes), 0) / completedBreaks.length;
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
      if (data.visit_start) {
        const visitDate = data.visit_start.substring(0, 10); // Extract YYYY-MM-DD
        if (visitDate === today) {
          todayVisits++;
        }
      }
    });

    document.getElementById('totalNurseVisits').textContent = todayVisits;
  });

// Recent activity
function loadRecentActivity() {
  console.log('[DASHBOARD] Loading recent activity for date:', today);
  const recentActivityBody = document.getElementById('recentActivityBody');
  const activities = [];

  // Get bathroom breaks
  db.collection('bathroom_breaks')
    .get()
    .then((snapshot) => {
      console.log('[DASHBOARD] Recent activity - bathroom breaks count:', snapshot.size);
      snapshot.forEach((doc) => {
        const data = doc.data();
        console.log('[DASHBOARD] Recent activity - break:', doc.id, data);
        // Check if break_start exists and matches today's date
        if (data.break_start) {
          const breakDate = data.break_start.substring(0, 10); // Extract YYYY-MM-DD
          console.log('[DASHBOARD] Recent activity - break date:', breakDate, 'vs today:', today);
          if (breakDate === today) {
            activities.push({
              name: data.student_name || 'Unknown',
              type: 'Bathroom',
              start: data.break_start,
              end: data.break_end,
              duration: data.duration_minutes,
              status: data.break_end ? 'Ended' : 'Active'
            });
          }
        }
      });
      console.log('[DASHBOARD] Recent activity - activities after breaks:', activities.length);

      // Get nurse visits
      db.collection('nurse_visits')
        .get()
        .then((nurseSnapshot) => {
          nurseSnapshot.forEach((doc) => {
            const data = doc.data();
            if (data.visit_start) {
              const visitDate = data.visit_start.substring(0, 10); // Extract YYYY-MM-DD
              if (visitDate === today) {
                activities.push({
                  name: data.student_name || 'Unknown',
                  type: 'Nurse',
                  start: data.visit_start,
                  end: data.visit_end,
                  duration: data.duration_minutes,
                  status: data.visit_end ? 'Ended' : 'Active'
                });
              }
            }
          });

          // Sort by start time (newest first)
          activities.sort((a, b) => new Date(b.start) - new Date(a.start));
          console.log('[DASHBOARD] Recent activity - final activities:', activities.length, activities);

          // Display activities
          if (activities.length === 0) {
            recentActivityBody.innerHTML = '<tr><td colspan="6" class="empty-state">No activity today</td></tr>';
          } else {
            recentActivityBody.innerHTML = activities.slice(0, 10).map(activity => {
              console.log('[DASHBOARD] Rendering activity:', activity);
              const endTime = activity.end ? formatTime(activity.end) : '-';
              const duration = (activity.duration !== null && activity.duration !== undefined) ? activity.duration + ' min' : '-';
              const statusBadge = activity.status === 'Active' ? 'badge-active' : 'badge-ended';
              console.log('[DASHBOARD] Formatted - end:', endTime, 'duration:', duration, 'status:', activity.status);
              
              return `
                <tr>
                  <td>${activity.name}</td>
                  <td>${activity.type}</td>
                  <td>${formatTime(activity.start)}</td>
                  <td>${endTime}</td>
                  <td>${duration}</td>
                  <td><span class="badge ${statusBadge}">${activity.status}</span></td>
                </tr>
              `;
            }).join('');
          }
        })
        .catch((error) => {
          console.error('Error loading nurse visits:', error);
          recentActivityBody.innerHTML = '<tr><td colspan="6" class="empty-state">Error loading activities</td></tr>';
        });
    })
    .catch((error) => {
      console.error('Error loading bathroom breaks:', error);
      recentActivityBody.innerHTML = '<tr><td colspan="6" class="empty-state">Error loading activities</td></tr>';
    });
}

loadRecentActivity();

