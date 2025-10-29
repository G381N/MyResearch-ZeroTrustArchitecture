# Testing Guide for Bug Fixes

## Quick Test Checklist

### 🔧 **Fix 1: Anomaly Status Display**
**Test**: Mark anomalies as normal should show greyed out with "Marked as Normal by Admin" label

**Steps**:
1. Start system: `./start.sh`
2. Go to Training Mode → Start Training → Generate events → Stop Training
3. Go to Live Mode → Start Live → Generate anomalous events (see trust score drop)
4. Go to Admin Mode → Find anomalies in table
5. Click "Mark Normal" on any anomaly
6. **Expected**: Anomaly row becomes greyed out, shows "Marked as Normal by Admin" badge, button changes to "Marked Normal"

### 🧪 **Fix 2: Test Mode Switch**  
**Test**: Disable time-based anomaly detection for testing

**Steps**:
1. In Admin Mode, find "Test Mode" section in System Controls
2. Click "Enable Test Mode" 
3. **Expected**: Button turns orange, shows warning message "Test mode enabled. Time-based anomaly detection disabled."
4. Start Live Mode → Generate events at unusual times
5. **Expected**: Should not flag time-based anomalies (events at 3 AM won't be anomalous)

### 🛠️ **Fix 3: Undefined Metadata Error**
**Test**: Admin Mode should not crash when viewing anomalies

**Steps**:
1. Generate some anomalies in Live Mode
2. Go to Admin Mode while Live Mode is still running
3. **Expected**: No "Cannot read properties of undefined (reading 'metadata')" error
4. All anomalies display properly with event details

### 📊 **Fix 4: Concurrent Admin/Live View & Trust Restoration**
**Test**: Can view both Admin and Live simultaneously, trust score updates when marking anomalies as normal

**Steps**:
1. Start Live Mode (keep it running)
2. Generate anomalies (watch trust score drop)
3. Switch to Admin Mode (Live Mode still active in background)
4. Mark anomalies as normal in Admin Mode
5. Switch back to Live Mode
6. **Expected**: 
   - Trust score should have increased (points restored)
   - Live Mode should still be active and collecting events
   - No errors switching between modes

## Expected Behaviors After Fixes

### ✅ **Anomaly Table Improvements**
- Resolved anomalies appear greyed out with strikethrough text
- "Marked as Normal by Admin" badge visible on resolved items  
- Button changes from "Mark Normal" to "Marked Normal" (disabled)
- Header shows "X unresolved / Y total anomalies"

### ✅ **Test Mode Features**
- Orange toggle button in Admin System Controls
- Warning message when enabled
- Time-based anomaly detection disabled (no 3 AM alerts)
- Can be toggled on/off as needed

### ✅ **Error Resolution**
- No crashes when viewing anomalies with missing metadata
- Safe handling of undefined event properties
- Graceful fallbacks for missing data

### ✅ **Multi-Mode Operation**
- Can switch between Admin and Live modes freely
- Trust score updates in real-time across modes
- Marking anomalies as normal restores trust points immediately
- Live Mode continues running while in Admin Mode

## Testing Commands

```bash
# Start the system
./start.sh

# Generate test events (from another terminal)
# Authentication failures
sudo su - (enter wrong password)

# File operations  
touch /tmp/test_$(date +%s).txt
rm /tmp/test_*.txt

# Network requests
curl -s http://example.com > /dev/null

# Process events
python3 -c "import os; print(os.getcwd())"
```

## Validation Checklist

- [ ] Anomalies show proper status (resolved/unresolved)
- [ ] Test mode toggle works without errors
- [ ] No undefined metadata crashes
- [ ] Can view Admin while Live Mode runs
- [ ] Trust score restores when marking anomalies as normal
- [ ] Performance metrics still work correctly
- [ ] WebSocket communication intact

## Common Issues Fixed

1. **React "Objects not valid as child"**: Fixed error handling in anomaly table
2. **Time-based false positives**: Test mode disables time features  
3. **Undefined metadata access**: Added null safety checks
4. **Single-mode limitation**: Removed restrictions on concurrent mode access
5. **Trust score inconsistency**: Real-time updates across all modes

All fixes maintain backward compatibility and don't break existing functionality.