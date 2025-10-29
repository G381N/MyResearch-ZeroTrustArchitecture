# Zero Trust Architecture System - Testing Guide

## Prerequisites
- Python 3.8+
- Node.js 16+
- Git
- 2 terminal windows

## Setup Instructions

### 1. Start the System
```bash
# Navigate to project directory
cd MyResearch-ZeroTrustArchitecture

# Start both backend and frontend
./start.sh
```

Wait for both servers to start:
- Backend: http://localhost:8000
- Frontend: http://localhost:3000

### 2. Open the Application
Open your browser and go to: `http://localhost:3000`

## Testing Workflow

### Phase 1: Training Mode Testing
1. **Start Training Mode**
   - Click "Start Training" button
   - Verify status shows "Training Mode: Active"

2. **Generate Training Events**
   - Simulate various activities on your system
   - Or use the event collector to generate synthetic events
   - Monitor the event count in the stats panel

3. **Stop Training and Verify Model**
   - Click "Stop Training" after collecting 50+ events
   - Verify model training completion message
   - Check "Model Status: Trained" in stats

### Phase 2: Live Mode Testing
1. **Start Live Mode**
   - Click "Start Live Mode" button
   - Verify status shows "Live Mode: Active"

2. **Generate Anomalous Behavior**
   - Perform unusual activities:
     - Multiple failed login attempts
     - Run suspicious commands with sudo
     - Create/delete files rapidly
     - Start unusual processes

3. **Monitor Anomaly Detection**
   - Watch the "Live Events" section for real-time events
   - Look for events marked with "🚨 ANOMALY" 
   - Observe trust score changes in the gauge

4. **Verify Trust Score Alerts**
   - When trust score drops below 20, check for:
     - Browser notification (if permissions granted)
     - Red alert indicator in UI
     - Admin alert messages

### Phase 3: Admin Mode Testing
1. **Switch to Admin Mode**
   - Click "Admin Mode" tab
   - View unresolved anomalies table

2. **Test Anomaly Management**
   - Find an anomaly in the table
   - Click "Mark Normal" to resolve false positives
   - Verify the anomaly disappears from the table
   - Check that trust score is restored

3. **View Performance Metrics**
   - Click "View Performance Metrics" button
   - Verify metrics display without errors
   - Check attack category breakdown
   - Review precision, recall, and F1-scores

4. **Test System Controls**
   - Try "System Reset" (caution: deletes all data)
   - Try "Exit System" to shutdown

## Expected Behaviors

### ✅ Success Indicators
- Events appear in real-time during Training and Live modes
- Anomalies are detected and marked with 🚨
- Trust score decreases when anomalies occur
- Trust score increases when anomalies are marked as normal
- Performance metrics show real calculations (not placeholder values)
- Browser notifications appear for critical alerts
- System stats update accurately

### ❌ Error Indicators
- Events not appearing in the UI
- All events marked as anomalies (model not trained properly)
- No anomalies detected (model too permissive)
- Trust score stuck at 100 or 0
- Performance metrics showing undefined/null errors
- WebSocket connection failures

## Troubleshooting

### Frontend Issues
```bash
# Check frontend logs
# Look for console errors in browser developer tools
# Verify WebSocket connection status
```

### Backend Issues
```bash
# Check backend logs for errors
# Verify database connectivity
# Check if ML model is properly trained
```

### Common Issues and Solutions

1. **No Events Appearing**
   - Check if event collector is running
   - Verify WebSocket connection
   - Restart the system

2. **All Events Marked as Anomalies**
   - Training data insufficient (need 50+ events)
   - Retrain the model in Training Mode

3. **Performance Metrics Error**
   - Fixed in latest version with proper null checks
   - Should show "No data yet" if no anomalies exist

4. **Trust Score Not Updating**
   - Check WebSocket connection
   - Verify trust scorer is functioning
   - Look for backend errors

## Test Data Generation

### Manual Event Generation
```bash
# Generate authentication failures
sudo su - (wrong password)
ssh invalid_user@localhost

# Generate file system events  
touch /tmp/test_file
rm /tmp/test_file

# Generate network events
curl http://suspicious-domain.com

# Generate process events
python -c "import os; os.system('whoami')"
```

### Automated Testing
The system includes built-in event simulation for consistent testing results.

## Performance Validation

### Real Metrics vs Placeholder
- **Before**: Static values (0.92, 0.88, 0.90, etc.)
- **After**: Dynamic calculations based on actual admin feedback
- **Validation**: Performance metrics should change as you mark anomalies as normal

### Expected Accuracy
- **Initial**: Lower precision due to model learning
- **After Admin Feedback**: Improved precision as false positives are corrected
- **Long-term**: Stabilized metrics reflecting true system performance

## System Architecture Verification

1. **Event Flow**: Training → Model Training → Live Detection → Admin Feedback → Model Improvement
2. **WebSocket Communication**: Real-time updates between backend and frontend
3. **Trust Scoring**: Dynamic calculation based on anomaly patterns
4. **ML Pipeline**: Isolation Forest model with incremental learning

## Success Criteria

✅ **Training Mode**: Collects events and trains model successfully  
✅ **Live Mode**: Detects anomalies and updates trust score in real-time  
✅ **Admin Mode**: Manages anomalies and calculates real performance metrics  
✅ **WebSocket**: Real-time communication works across all modes  
✅ **Trust System**: Scores decrease/increase based on anomaly detection/resolution  
✅ **Error Handling**: No undefined/null errors in performance metrics  

The system should demonstrate a complete Zero Trust Architecture workflow with AI-based behavioral monitoring and dynamic trust scoring.