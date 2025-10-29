# Model Accuracy Testing Guide

## Overview

The new Model Accuracy Testing feature provides real performance metrics by splitting your collected data into training and testing sets. This gives you genuine accuracy measurements instead of placeholder values.

## How It Works

### 🔄 **Data Splitting Process**
1. **Data Collection**: Uses all events from your database (normal + anomalous)
2. **Random Split**: Divides data into training (70-80%) and testing (20-30%) sets
3. **Stratified Split**: Maintains proportion of normal vs anomalous events in both sets
4. **Model Training**: Trains a fresh Isolation Forest model on training data
5. **Testing**: Evaluates the trained model on unseen testing data
6. **Metrics Calculation**: Provides comprehensive performance metrics

### 📊 **Metrics Provided**

#### **Core Performance Metrics**
- **Accuracy**: Overall correctness (TP + TN) / (TP + TN + FP + FN)
- **Precision**: Anomaly detection accuracy TP / (TP + FP)  
- **Recall**: Anomaly detection completeness TP / (TP + FN)
- **F1-Score**: Harmonic mean of precision and recall

#### **Confusion Matrix**
- **True Positives (TP)**: Correctly identified anomalies
- **True Negatives (TN)**: Correctly identified normal events  
- **False Positives (FP)**: Normal events flagged as anomalies
- **False Negatives (FN)**: Anomalies missed by the model

#### **Error Rates**
- **False Positive Rate**: FP / (FP + TN) - Normal events wrongly flagged
- **False Negative Rate**: FN / (FN + TP) - Anomalies missed

## Testing Workflow

### **Step 1: Data Preparation**
```bash
# Start the system
./start.sh

# Navigate to http://localhost:3000
```

### **Step 2: Collect Training Data**
1. **Training Mode**: Start training and collect diverse events
   - Normal user activities (login, file operations, etc.)
   - Various event types across different times
   - Aim for 100+ events for meaningful results

2. **Live Mode**: Generate some anomalies
   - Suspicious activities (multiple failed logins, unusual commands)
   - Let the system detect and flag anomalies
   - Mark obvious false positives as "normal" in Admin Mode

### **Step 3: Run Model Tests**
1. **Go to Admin Mode** → Find "Model Accuracy Testing" section

2. **Choose Split Ratio**:
   - **80/20 Split**: 80% training, 20% testing (recommended for larger datasets)
   - **70/30 Split**: 70% training, 30% testing (better for smaller datasets)

3. **Click Test Button**: System will automatically:
   - Split your data randomly
   - Train a new model on training set
   - Test the model on unseen testing set
   - Calculate all performance metrics

### **Step 4: Interpret Results**

#### **Good Performance Indicators**
- **Accuracy > 85%**: Model correctly classifies most events
- **Precision > 80%**: Low false positive rate
- **Recall > 75%**: Catches most real anomalies
- **F1-Score > 80%**: Balanced precision and recall

#### **Common Issues and Solutions**

**High False Positive Rate (Low Precision)**
- **Cause**: Model too sensitive, flagging normal events as anomalies
- **Solution**: Collect more diverse normal training data
- **Action**: Run more training sessions with varied normal activities

**High False Negative Rate (Low Recall)**  
- **Cause**: Model missing real anomalies
- **Solution**: Include more varied anomaly examples in training
- **Action**: Generate more diverse suspicious activities during training

**Low Overall Accuracy**
- **Cause**: Insufficient or poor quality training data
- **Solution**: Collect more data with better normal/anomaly examples
- **Action**: Restart training process with more systematic data collection

## Testing Scenarios

### **Scenario 1: New System (Cold Start)**
```bash
# Minimum viable dataset
- 50+ normal events (varied activities)
- 20+ anomalous events (various attack types)  
- Use 70/30 split for testing
- Expected accuracy: 70-85%
```

### **Scenario 2: Established System**
```bash  
# Mature dataset
- 200+ normal events (comprehensive user behavior)
- 50+ anomalous events (diverse attack patterns)
- Use 80/20 split for testing
- Expected accuracy: 85-95%
```

### **Scenario 3: Production Validation**
```bash
# Production-ready validation
- 500+ normal events (full behavioral baseline)
- 100+ anomalous events (complete attack spectrum)
- Use 80/20 split for testing
- Target accuracy: 90%+
```

## Best Practices

### **Data Collection**
1. **Diverse Normal Activities**: Include various user behaviors, times, and event types
2. **Realistic Anomalies**: Generate genuine suspicious activities, not just random events
3. **Balanced Dataset**: Maintain ~10-20% anomaly ratio (matches real-world scenarios)
4. **Quality over Quantity**: Better to have fewer high-quality labeled examples

### **Testing Strategy**
1. **Iterative Improvement**: Run tests after collecting new data
2. **Compare Splits**: Try both 70/30 and 80/20 to see consistency
3. **Track Progress**: Monitor metrics improvement over time
4. **Validate Changes**: Re-test after making system modifications

### **Interpreting Results**
1. **Context Matters**: Consider your specific security requirements
2. **Trade-offs**: Balance between false positives (user annoyance) and false negatives (missed threats)
3. **Baseline Comparison**: Compare against initial placeholder metrics
4. **Real-world Validation**: Supplement with manual security review

## API Integration

### **Programmatic Access**
```bash
# Run model test via API
curl -X POST http://localhost:8000/api/admin/run_model_test \
  -H "Content-Type: application/json" \
  -d '{"train_percentage": 80}'
```

### **Response Format**
```json
{
  "overall": {
    "accuracy": 0.87,
    "precision": 0.83,
    "recall": 0.79,
    "f1_score": 0.81
  },
  "confusion_matrix": {
    "true_positives": 23,
    "true_negatives": 89, 
    "false_positives": 12,
    "false_negatives": 6
  },
  "data_split": {
    "training_size": 104,
    "testing_size": 26,
    "train_percentage": 80,
    "test_percentage": 20
  }
}
```

## Troubleshooting

### **Error: "Need at least 10 events"**
- **Cause**: Insufficient data in database
- **Solution**: Collect more events in Training/Live modes

### **Error: "Model training failed"**
- **Cause**: Poor data quality or system issues  
- **Solution**: Check event data, restart system if needed

### **Inconsistent Results**
- **Cause**: Small dataset with high variance
- **Solution**: Collect more data, multiple test runs

### **Very High Accuracy (>98%)**
- **Cause**: Possible data leakage or overfitting
- **Solution**: Verify data collection process, check for duplicates

## Success Metrics

### **Development Phase**
- ✅ Accuracy > 70%
- ✅ Test runs complete without errors
- ✅ Results show improvement over time

### **Production Phase**  
- ✅ Accuracy > 85%
- ✅ Precision > 80% (acceptable false positive rate)
- ✅ Recall > 75% (catching most real threats)
- ✅ Consistent results across multiple test runs

This testing framework provides scientific validation of your Zero Trust system's effectiveness with real performance metrics based on your actual data and use cases.