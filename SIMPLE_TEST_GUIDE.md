# Simple Model Testing Guide

## Quick Steps

### 1. Start System
```bash
./start.sh
```
Open http://localhost:3000

### 2. Collect Data (Need 50+ Events)
1. **Training Mode** → Start Training → Do normal activities → Stop Training
2. **Live Mode** → Start Live → Do suspicious activities → Watch for anomalies
3. **Admin Mode** → Mark obvious false positives as "Normal"

### 3. Run Model Test
1. Go to **Admin Mode**
2. Find **"Model Accuracy Testing"** section  
3. Click **"Test 80/20 Split"** (recommended) or **"Test 70/30 Split"**
4. Wait for results

## What the Results Mean

### Good Results
- **Accuracy > 80%** = System working well
- **Precision > 75%** = Low false alarms
- **Recall > 70%** = Catching real threats

### If Results Are Poor
- **Low Accuracy** = Need more training data
- **Low Precision** = Too many false alarms, mark more as normal
- **Low Recall** = Missing threats, need more anomaly examples

## Minimum Requirements
- At least **50 total events** in database
- Mix of **normal** and **anomalous** events
- Some admin feedback (mark false positives as normal)

## Troubleshooting
- **"Need at least 10 events"** = Collect more data first
- **"Model training failed"** = Check if you have both normal and anomaly events
- **Very high accuracy (>95%)** = Might need more diverse data

## Expected Accuracy Levels
- **New system**: 60-75%
- **Some training**: 75-85% 
- **Well-trained**: 85-95%

That's it! The test gives you real accuracy instead of fake placeholder numbers.