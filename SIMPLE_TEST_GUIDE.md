# Simple Model Testing Guide

## Problem: Your Current Low Accuracy (12.6% / 11.3%)

**Root Cause**: Training data is just "system running idly" - no real user patterns or genuine anomalies for the model to learn from.

## Solution: Generate Realistic Test Data

### 1. Start System
```bash
./start.sh
```
Open http://localhost:3000

### 2. Generate Test Data (RECOMMENDED)
1. Go to **Admin Mode** 
2. Find **"Model Accuracy Testing"** section
3. Click **"Generate Test Data"** button
4. This creates 250 realistic events:
   - **200 normal events**: login, file operations, web browsing, process starts/stops
   - **50 anomaly events**: failed logins, suspicious commands, malware, off-hours access

### 3. Run Model Test  
1. After generating test data, click **"Test 80/20 Split"**
2. Should now see **60-80% accuracy** (much better!)

## Alternative: Manual Data Collection
If you want to use real data instead:
1. **Training Mode** → Start Training → Do 1+ hours of normal computer usage → Stop Training  
2. **Live Mode** → Start Live → Simulate attacks (failed logins, suspicious commands) → Watch for anomalies
3. **Admin Mode** → Mark false positives as "Normal"

## What the Results Mean

### Expected Results After Test Data Generation
- **Accuracy: 60-85%** (much better than your current 12%)
- **Precision: 70-90%** = Low false alarms  
- **Recall: 60-80%** = Catching real threats
- **Non-zero values** in confusion matrix

### Your Current Results Problem
- **12.6% / 11.3% accuracy** = Model has no baseline
- **0% Precision/Recall** = No meaningful learning occurred
- **High false positives** = Everything flagged as anomaly

## Why Test Data Generation Helps
- **Realistic patterns**: Normal vs suspicious behavior clearly defined
- **Proper labeling**: Events correctly marked as normal/anomaly  
- **Balanced dataset**: 80% normal, 20% anomaly (realistic ratio)
- **Diverse scenarios**: Multiple attack types and normal activities

## Troubleshooting
- **Still low accuracy after test data** = System issue, check logs
- **Very high accuracy (>95%)** = Good! Test data worked
- **0% metrics** = Model training failed, try generating data again

## Quick Fix for Your Issue
1. **Generate Test Data** (creates proper training examples)
2. **Run 80/20 Test** (should see 60-80% accuracy)  
3. **Compare** with your current 12% to see improvement

The test data creates what you're missing: realistic user behavior patterns vs genuine security threats.