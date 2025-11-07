# Online-First Database Migration Guide

## Overview
The system has been migrated from a hybrid (SQLite + Firebase sync) approach to an **online-first** architecture where Firebase Firestore is the primary database.

## Key Changes

### Database Architecture

**OLD: Hybrid Database**
- Always used local SQLite as primary
- Synced to Firebase every 10 minutes
- Bidirectional sync (complex)
- Local database always active

**NEW: Online-First Database**
- Uses Firebase Firestore as primary when online
- Only uses SQLite when offline
- One-way sync (local → cloud) when connection restored
- Local database cleared after sync

### How It Works

#### Online Mode (Default)
1. All operations go directly to Firebase Firestore
2. Real-time updates across all devices
3. No local database overhead
4. Immediate sync

#### Offline Mode (Fallback)
1. Automatically activates when no internet detected
2. Creates local SQLite database
3. Syncs all students from Firebase (if available)
4. Records all activity locally

#### Connection Restoration
1. Monitors connectivity every 30 seconds
2. Detects when internet returns
3. Automatically syncs all local data to Firebase
4. Clears local activity data (keeps students for next offline period)

### Startup Behavior

**With Internet:**
```
[ONLINE-FIRST] Checking internet connectivity... (5s timeout)
[ONLINE-FIRST] Internet detected - Initializing Firebase (10s timeout)...
[ONLINE-FIRST] ✓ Online mode - Using Firebase Firestore as primary database
[ONLINE-FIRST] 🔍 Checking for offline data...
[ONLINE-FIRST] Found existing offline data on startup!
[ONLINE-FIRST] Syncing offline data to Firebase...
[ONLINE-FIRST] ✓ Startup sync completed
```

**Without Internet:**
```
[ONLINE-FIRST] Checking internet connectivity... (5s timeout)
[ONLINE-FIRST] ⚠ No internet detected - Starting in offline mode
[ONLINE-FIRST] Initializing local SQLite database...
[ONLINE-FIRST] ✓ Local database initialized
```

### Data Format Changes

#### Timestamps
- **Before**: Stored as formatted strings `"2025-11-06 19:30:46.123456"`
- **After**: Stored as native timestamps, synced to Firebase as ISO format `"2025-11-06T19:30:46.123456"`

#### Duration Calculation
- Fixed to handle both ISO format (with T) and space format
- Uses `datetime.fromisoformat()` as primary parsing method
- Backward compatible with old string formats

### Webapp Changes

#### Fixed Issues:
1. ✅ Nurse visits query: Changed from `where('visit_end', '==', '')` to `where('visit_end', '==', null)`
2. ✅ Date comparison: Changed from `.startsWith()` to `.substring(0, 10)` for more reliable date extraction
3. ✅ Duration filtering: Excludes 0 and null durations from averages
4. ✅ Error handling: Added try-catch blocks for better error messages
5. ✅ Console debugging: Added detailed logging for troubleshooting

#### Debug Console Logs
Open browser console to see:
- `[DASHBOARD] Today's date: YYYY-MM-DD`
- `[DASHBOARD] Bathroom breaks snapshot received, total docs: X`
- `[DASHBOARD] Break doc: ID data: {...}`
- `[DASHBOARD] Break date: YYYY-MM-DD vs today: YYYY-MM-DD match: true/false`
- `[DASHBOARD] Today's breaks count: X`

### Code Changes

#### Main Application
```python
# OLD
from hybrid_db import HybridDatabase
self.db = HybridDatabase(sync_interval_minutes=10)

# NEW
from online_first_db import OnlineFirstDatabase
self.db = OnlineFirstDatabase(connectivity_check_interval=30)
```

#### API Compatibility
All existing methods work the same:
- `check_in()`, `start_bathroom_break()`, `end_bathroom_break()`
- `start_nurse_visit()`, `end_nurse_visit()`
- `is_checked_in()`, `is_on_break()`, `is_at_nurse()`
- `has_students_out()` - now works in offline mode too
- `force_sync()` - triggers sync if offline with data
- `get_sync_status()` - returns mode info

### Benefits

| Feature | Before | After |
|---------|--------|-------|
| Primary Database | SQLite | Firebase Firestore |
| Offline Support | Always on | Only when needed |
| Sync Delay | 10 minutes | Immediate (online) |
| Data Conflicts | Possible | Eliminated |
| Storage Usage | Always uses disk | Minimal disk usage |
| Multi-device | Delayed updates | Real-time updates |
| Startup Time | ~3-5 seconds | ~2 seconds (online), ~7 seconds (offline) |

### Troubleshooting

#### App Won't Start
- Wait 5-10 seconds for timeout
- Check console for `[ONLINE-FIRST]` messages
- Should automatically fall back to offline mode

#### Webapp Shows "No Activity"
- Open browser console (F12)
- Look for `[DASHBOARD]` debug messages
- Check if dates are matching correctly
- Verify data exists in Firestore Console

#### Offline Data Not Syncing
- Wait 30 seconds for connectivity check
- Check console for sync messages
- Look for `[ONLINE-FIRST] Found offline data: X attendance, Y breaks, Z visits`
- Or restart app with internet to trigger startup sync

### Files Changed
- `main/online_first_db.py` - New online-first database class
- `main/nfc_reader_gui.py` - Updated to use OnlineFirstDatabase
- `main/student_db.py` - Fixed timestamp storage and parsing
- `main/hybrid_db.py` - Fixed sync issues and duplicate prevention
- `webapp/public/js/dashboard.js` - Fixed date filtering and null checks
- All files copied to root directory for production

### Testing Checklist
- [ ] Start app with internet (online mode)
- [ ] Start app without internet (offline mode)
- [ ] Start bathroom break in offline mode
- [ ] End bathroom break in offline mode
- [ ] Verify LED changes in offline mode
- [ ] Reconnect internet while app running
- [ ] Verify auto-sync within 30 seconds
- [ ] Restart app with internet after offline use
- [ ] Verify startup sync
- [ ] Check webapp displays all activities
- [ ] Verify duration calculations

### Duration = 0 Note
If you see `duration_minutes: 0` in Firestore, this is **correct** if the break was less than 1 minute. The duration is calculated in whole minutes and rounds down:
- 0-59 seconds = 0 minutes
- 60-119 seconds = 1 minute
- etc.

This is expected behavior for quick bathroom break tests!

