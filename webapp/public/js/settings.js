// Settings Logic

// Require authentication
requireAuth();

// Display user email
checkAuthState((user) => {
  if (user) {
    document.getElementById('userEmail').textContent = user.email;
  }
});

let periods = [];

// Default periods
const defaultPeriods = [
  { name: 'Period 1', start_hour: 7, start_minute: 25, end_hour: 8, end_minute: 8 },
  { name: 'Period 2', start_hour: 8, start_minute: 12, end_hour: 8, end_minute: 55 },
  { name: 'Homeroom', start_hour: 8, start_minute: 55, end_hour: 9, end_minute: 1 },
  { name: 'Period 3', start_hour: 9, start_minute: 5, end_hour: 9, end_minute: 48 },
  { name: 'Period 4', start_hour: 9, start_minute: 52, end_hour: 10, end_minute: 35 },
  { name: 'Period 5', start_hour: 10, start_minute: 39, end_hour: 11, end_minute: 22 },
  { name: 'Period 6', start_hour: 11, start_minute: 26, end_hour: 12, end_minute: 9 },
  { name: 'Period 7', start_hour: 12, start_minute: 13, end_hour: 12, end_minute: 56 },
  { name: 'Period 8', start_hour: 13, start_minute: 0, end_hour: 13, end_minute: 43 },
  { name: 'Period 9', start_hour: 13, start_minute: 47, end_hour: 14, end_minute: 30 }
];

// Load periods from Firestore
async function loadPeriods() {
  try {
    const doc = await db.collection('settings').doc('periods').get();
    
    if (doc.exists) {
      const data = doc.data();
      periods = data.periods || defaultPeriods;
    } else {
      // No settings exist, use defaults
      periods = [...defaultPeriods];
      // Save defaults to Firestore
      await db.collection('settings').doc('periods').set({ periods: periods });
    }
    
    renderPeriods();
  } catch (error) {
    console.error('Error loading periods:', error);
    alert('Failed to load periods: ' + error.message);
    // Use defaults if error
    periods = [...defaultPeriods];
    renderPeriods();
  }
}

// Render periods in the UI
function renderPeriods() {
  const container = document.getElementById('periodsContainer');
  
  container.innerHTML = periods.map((period, index) => `
    <div class="card" style="margin-bottom: 1rem; padding: 1rem; background: var(--background);">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
        <h3 style="margin: 0;">Period ${index + 1}</h3>
        <button class="btn btn-small btn-danger" onclick="removePeriod(${index})">Remove</button>
      </div>
      <div style="display: grid; grid-template-columns: 2fr 1fr 1fr 1fr 1fr; gap: 1rem; align-items: end;">
        <div class="form-group" style="margin: 0;">
          <label>Period Name</label>
          <input type="text" value="${period.name}" onchange="updatePeriod(${index}, 'name', this.value)">
        </div>
        <div class="form-group" style="margin: 0;">
          <label>Start Hour</label>
          <input type="number" min="0" max="23" value="${period.start_hour}" onchange="updatePeriod(${index}, 'start_hour', parseInt(this.value))">
        </div>
        <div class="form-group" style="margin: 0;">
          <label>Start Min</label>
          <input type="number" min="0" max="59" value="${period.start_minute}" onchange="updatePeriod(${index}, 'start_minute', parseInt(this.value))">
        </div>
        <div class="form-group" style="margin: 0;">
          <label>End Hour</label>
          <input type="number" min="0" max="23" value="${period.end_hour}" onchange="updatePeriod(${index}, 'end_hour', parseInt(this.value))">
        </div>
        <div class="form-group" style="margin: 0;">
          <label>End Min</label>
          <input type="number" min="0" max="59" value="${period.end_minute}" onchange="updatePeriod(${index}, 'end_minute', parseInt(this.value))">
        </div>
      </div>
      <div style="color: var(--text-light); font-size: 0.875rem; margin-top: 0.5rem;">
        ${formatTime(period.start_hour, period.start_minute)} - ${formatTime(period.end_hour, period.end_minute)}
      </div>
    </div>
  `).join('');
}

// Format time for display
function formatTime(hour, minute) {
  const h = hour % 12 || 12;
  const m = minute.toString().padStart(2, '0');
  const ampm = hour >= 12 ? 'PM' : 'AM';
  return `${h}:${m} ${ampm}`;
}

// Update a period
window.updatePeriod = function(index, field, value) {
  periods[index][field] = value;
  renderPeriods();
}

// Add a new period
window.addPeriod = function() {
  const lastPeriod = periods[periods.length - 1];
  const newPeriod = {
    name: `Period ${periods.length + 1}`,
    start_hour: lastPeriod ? lastPeriod.end_hour : 14,
    start_minute: lastPeriod ? lastPeriod.end_minute + 5 : 0,
    end_hour: lastPeriod ? lastPeriod.end_hour + 1 : 15,
    end_minute: lastPeriod ? lastPeriod.end_minute : 0
  };
  periods.push(newPeriod);
  renderPeriods();
}

// Remove a period
window.removePeriod = function(index) {
  if (confirm('Are you sure you want to remove this period?')) {
    periods.splice(index, 1);
    renderPeriods();
  }
}

// Save periods to Firestore
window.savePeriods = async function() {
  const saveMessage = document.getElementById('saveMessage');
  saveMessage.innerHTML = '<div class="loading" style="width: 20px; height: 20px;"></div>';
  
  try {
    await db.collection('settings').doc('periods').set({
      periods: periods,
      updated_at: new Date().toISOString()
    });
    
    saveMessage.innerHTML = '<div class="alert alert-success">✅ Periods saved successfully! Changes will be applied on next app restart.</div>';
    setTimeout(() => {
      saveMessage.innerHTML = '';
    }, 5000);
  } catch (error) {
    console.error('Error saving periods:', error);
    saveMessage.innerHTML = `<div class="alert alert-error">❌ Failed to save: ${error.message}</div>`;
  }
}

// Save bathroom restrictions
window.saveRestrictions = async function() {
  const restrictFirstLast = document.getElementById('restrictFirstLast').checked;
  
  try {
    await db.collection('settings').doc('restrictions').set({
      restrict_first_last_10_minutes: restrictFirstLast,
      updated_at: new Date().toISOString()
    });
    
    alert('✅ Restrictions saved successfully!');
  } catch (error) {
    console.error('Error saving restrictions:', error);
    alert('❌ Failed to save restrictions: ' + error.message);
  }
}

// Load restrictions
async function loadRestrictions() {
  try {
    const doc = await db.collection('settings').doc('restrictions').get();
    
    if (doc.exists) {
      const data = doc.data();
      document.getElementById('restrictFirstLast').checked = data.restrict_first_last_10_minutes !== false;
    }
  } catch (error) {
    console.error('Error loading restrictions:', error);
  }
}

// Initialize
loadPeriods();
loadRestrictions();

