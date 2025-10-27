# Zero Trust Architecture System

A full-stack AI-based behavior tracking and dynamic trust scoring system that monitors user and system activity, learns normal behavior patterns, and detects anomalies in real-time.

## 🚀 Quick Start

```bash
# Clone and navigate to the project
cd ZeroTrustArch-DTSandAI

# Start the entire system
./start.sh

# Access the dashboard
open http://localhost:3000
```

## 📋 System Requirements

- **Python 3.10+** with pip
- **Node.js 18+** with npm
- **PostgreSQL 12+** (local installation)
- **Linux/macOS** (for system event monitoring)
- **Root/sudo access** (for comprehensive system monitoring)

## 🏗️ Architecture

### Tech Stack
- **Backend**: FastAPI + Python 3.10+
- **Frontend**: Next.js 14 + TailwindCSS + Recharts
- **Database**: PostgreSQL (local)
- **ML**: scikit-learn Isolation Forest
- **Real-time**: WebSockets
- **System Monitoring**: psutil, watchdog, pyinotify

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Database      │
│   (Next.js)     │◄──►│   (FastAPI)     │◄──►│   (PostgreSQL)  │
│   Port: 3000    │    │   Port: 8000    │    │   Port: 5432    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐           │
         │              │   ML Engine     │           │
         │              │   (Isolation     │           │
         │              │    Forest)       │           │
         │              └─────────────────┘           │
         │                       │                       │
         │              ┌─────────────────┐           │
         └──────────────►│  Event Collector│◄──────────┘
                        │  (psutil,       │
                        │   watchdog)     │
                        └─────────────────┘
```

## 🎯 Features

### Three Operational Modes

1. **Training Mode**
   - Collects system events for model training
   - Real-time event logging
   - Statistics and progress tracking
   - Model training on collected data

2. **Live Mode**
   - Real-time anomaly detection
   - Dynamic trust scoring (0-100)
   - Trust score visualization
   - Anomaly alerts and notifications

3. **Admin Mode**
   - Manage detected anomalies
   - Mark false positives as normal
   - System statistics and metrics
   - Full system reset capability

### Monitored Event Types

- **Process Events**: `process_start`, `process_end`
- **Network Events**: `network_connection`
- **Authentication**: `login`, `logout`, `auth_failure`
- **System Commands**: `sudo_command`
- **File System**: `file_change`

### AI/ML Features

- **Isolation Forest** for unsupervised anomaly detection
- **Feature Engineering** with behavioral patterns
- **Incremental Learning** from admin feedback
- **Confidence Scoring** for anomaly predictions
- **Model Persistence** with save/load capability

## 🛠️ Installation

### 1. System Dependencies

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib python3 python3-pip nodejs npm

# macOS
brew install postgresql python3 node
```

### 2. Database Setup

```bash
# Start PostgreSQL
sudo systemctl start postgresql  # Linux
brew services start postgresql   # macOS

# Create database
sudo -u postgres createdb zerotrust
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'password';"
```

### 3. Project Setup

```bash
# Clone the repository
git clone <repository-url>
cd ZeroTrustArch-DTSandAI

# Make scripts executable
chmod +x start.sh stop.sh

# Start the system
./start.sh
```

## 🚀 Usage

### Starting the System

```bash
./start.sh
```

This will:
- Check system requirements
- Initialize the database
- Install dependencies
- Start backend and frontend servers
- Display system status

### Accessing the Dashboard

1. **Frontend Dashboard**: http://localhost:3000
2. **API Documentation**: http://localhost:8000/docs
3. **Health Check**: http://localhost:8000/health

### Workflow

1. **Start Training Mode**
   - Click "Start Training" in the dashboard
   - Perform normal system activities
   - Let the system collect 50-100 events
   - Click "Stop Training" to train the model

2. **Switch to Live Mode**
   - Click "Start Live Mode" in the dashboard
   - System begins real-time anomaly detection
   - Monitor trust score and anomalies
   - View real-time event logs

3. **Manage in Admin Mode**
   - Review detected anomalies
   - Mark false positives as normal
   - View system statistics
   - Reset system if needed

### Stopping the System

```bash
./stop.sh
```

## 📊 API Endpoints

### Training Endpoints
- `POST /api/train/start` - Start training mode
- `POST /api/train/stop` - Stop training and train model
- `GET /api/train/status` - Get training status

### Live Mode Endpoints
- `POST /api/live/start` - Start live monitoring
- `POST /api/live/stop` - Stop live monitoring
- `GET /api/trust` - Get current trust score
- `GET /api/stats` - Get live statistics
- `GET /api/anomalies` - Get detected anomalies

### Admin Endpoints
- `POST /api/admin/mark_normal` - Mark anomaly as normal
- `POST /api/admin/reset` - Reset entire system
- `GET /api/admin/stats` - Get system statistics

### Event Endpoints
- `POST /api/events/` - Create new event
- `GET /api/events/` - Get events with filtering
- `GET /api/events/recent` - Get recent events

## 🔧 Configuration

### Backend Configuration (`backend/config.py`)

```python
# Database
DATABASE_URL = "postgresql://postgres:password@localhost:5432/zerotrust"

# Trust Score Weights
TRUST_WEIGHTS = {
    "auth_failure": -25,
    "sudo_command": -20,
    "network_connection": -15,
    "file_change": -10,
    "process_start": -10,
    "login": -5,
    "logout": -5,
    "process_end": -5
}

# ML Model
CONTAMINATION = 0.1  # Assume 10% anomalies
```

### Frontend Configuration

Environment variables in `frontend/.env.local`:
```
API_URL=http://localhost:8000
WS_URL=ws://localhost:8000/ws
```

## 📈 Trust Scoring System

### Trust Score Calculation

```
Initial Score: 100
Trust Deduction = Anomaly Confidence × Severity Weight
New Score = max(0, Current Score - Trust Deduction)
```

### Severity Weights

| Event Type | Weight | Description |
|------------|--------|-------------|
| `auth_failure` | -25 | Critical security event |
| `sudo_command` | -20 | High privilege operation |
| `network_connection` | -15 | Network activity |
| `file_change` | -10 | File system modification |
| `process_start` | -10 | New process creation |
| `login` | -5 | User authentication |
| `logout` | -5 | User session end |
| `process_end` | -5 | Process termination |

### Alert Thresholds

- **Critical Alert**: Trust Score < 20
- **Warning**: Trust Score < 50
- **Normal**: Trust Score ≥ 50

## 🧠 Machine Learning

### Feature Engineering

The system extracts numerical features from events:

```python
features = [
    hour_of_day,           # Time-based pattern
    day_of_week,           # Weekly pattern
    event_type_encoded,    # One-hot encoded event type
    process_name_hash,     # Process identification
    network_dest_hash,     # Network destination
    user_id_hash,          # User identification
    frequency_5min,        # Event frequency
    frequency_1min,        # Recent activity
    auth_success,          # Authentication success
    file_change_severity,  # File change impact
    network_type           # Network connection type
]
```

### Model Training

1. **Data Collection**: Events collected during training mode
2. **Feature Extraction**: Convert events to numerical features
3. **Model Training**: Isolation Forest with contamination=0.1
4. **Model Persistence**: Save trained model to disk
5. **Incremental Learning**: Retrain with admin feedback

### Anomaly Detection

```python
# Predict anomaly
is_anomaly, confidence = model.predict(event_features)

# Trust score update
if is_anomaly:
    trust_deduction = confidence × severity_weight[event_type]
    new_trust_score = max(0, current_trust - trust_deduction)
```

## 📝 Logging

### Log Files

- **Backend Logs**: `logs/backend.log`
- **Frontend Logs**: `logs/frontend.log`
- **System Logs**: `logs/zerotrust.log`

### Log Levels

- **INFO**: General system information
- **WARNING**: Non-critical issues
- **ERROR**: System errors
- **DEBUG**: Detailed debugging information

## 🔍 Monitoring

### System Health

```bash
# Check system status
curl http://localhost:8000/health

# View logs
tail -f logs/backend.log
tail -f logs/frontend.log
```

### Database Queries

```sql
-- View all events
SELECT * FROM events ORDER BY timestamp DESC LIMIT 10;

-- View anomalies
SELECT * FROM anomalies WHERE is_resolved = false;

-- View trust score history
SELECT * FROM events WHERE trust_impact != 0;
```

## 🚨 Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Kill processes on ports
   lsof -ti:8000 | xargs kill -9
   lsof -ti:3000 | xargs kill -9
   ```

2. **Database Connection Failed**
   ```bash
   # Check PostgreSQL status
   sudo systemctl status postgresql
   
   # Start PostgreSQL
   sudo systemctl start postgresql
   ```

3. **Permission Denied for System Monitoring**
   ```bash
   # Run with sudo for full system access
   sudo ./start.sh
   ```

4. **Frontend Build Errors**
   ```bash
   # Clear node modules and reinstall
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   ```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
./start.sh
```

## 📚 Research Features

### Accuracy Metrics

The system calculates accuracy based on admin feedback:

```python
accuracy = resolved_anomalies / total_anomalies
precision = true_positives / (true_positives + false_positives)
```

### Performance Metrics

- **Event Processing Rate**: Events per second
- **Anomaly Detection Latency**: Time to detect anomalies
- **Model Training Time**: Time to train/retrain model
- **Memory Usage**: System resource consumption

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For issues and questions:

1. Check the troubleshooting section
2. Review the logs for error messages
3. Open an issue on GitHub
4. Contact the development team

## 🔮 Future Enhancements

- [ ] Multi-user support
- [ ] Advanced ML models (LSTM, Transformer)
- [ ] Real-time dashboard updates
- [ ] Mobile application
- [ ] Cloud deployment support
- [ ] Advanced visualization
- [ ] Automated response actions
- [ ] Integration with SIEM systems

---

**Zero Trust Architecture System** - AI-powered behavior tracking for enhanced security
