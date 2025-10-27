Build a full-stack Zero Trust Architecture System with AI-based behavior tracking and dynamic trust scoring.
The system monitors user and system activity, learns what is considered normal behavior in Training Mode, detects anomalies in Live Mode, and allows administrative control and refinement in Admin Mode.

The project should have a single launch script (start.sh) that initializes and runs all components automatically.

1. System Overview

The system tracks the following event types:

process_start

process_end

network_connection

sudo_command

file_change

login

logout

auth_failure

These are the core monitored activities.

There are three functional modes:

Training Mode

Live Mode

Admin Mode

2. start.sh Script

This single command should automate the entire environment setup.

When ./start.sh is executed:

It launches the database (PostgreSQL or MongoDB).

Starts the backend API server (FastAPI preferred, Flask acceptable).

Starts the frontend (Next.js or React).

Initializes the ML model (loads existing trained model if available or creates a new one if first run).

Checks that all services are running and displays “System Ready” in the console.

3. Backend Specification

Use FastAPI for backend implementation.

The backend is responsible for:

Event collection and logging.

Training the machine learning model.

Performing anomaly detection.

Managing trust score updates.

Handling admin requests and reset operations.

Serving data for frontend visualization.

Backend Endpoints

POST /api/train/start

Starts training mode.

Backend begins recording all specified event types in a structured format.

Training mode ignores anomaly detection and trust scoring.

POST /api/train/stop

Stops training mode.

Triggers model training using collected data.

Model learns what “normal” looks like based on collected patterns.

POST /api/live/start

Starts live mode.

Validates that training has already been completed; if not, returns an error stating “Training not yet completed.”

Begins monitoring events and performing anomaly detection in real time.

Initializes trust score to 100 at session start.

POST /api/live/stop

Stops live mode and finalizes the current live session.

POST /api/events

Accepts incoming event logs (process_start, process_end, network_connection, sudo_command, file_change, login, logout, auth_failure).

During training mode: events are stored for model learning.

During live mode: events are evaluated using the trained model to detect anomalies and adjust trust score.

GET /api/trust

Returns current trust score in real time.

GET /api/stats

Returns numerical data about system operation such as event counts, anomalies detected, and live session statistics.

GET /api/anomalies

Returns all detected anomalies for the current live session.

POST /api/admin/mark_normal

Allows admin to mark an anomaly as “normal.”

Updates training dataset and model to recognize this event as non-anomalous in the future.

Restores any trust points that were deducted for this anomaly.

POST /api/admin/reset

Performs a full system reset.

Deletes all collected training and live session data.

Deletes or reinitializes the ML model.

Resets trust score and all stored logs.

Returns system to a clean, fresh state.

4. Backend Logic and Rules

Training Mode:

Only collects events.

No anomaly detection or trust scoring occurs.

Live event log should update in real time, showing all events of tracked types.

Once training stops, all collected data is used to train the machine learning model (Isolation Forest or similar).

Live Mode:

Uses the trained model to detect anomalies in real time.

Displays only anomalous events in the frontend log.

Calculates and updates trust score continuously.

If trust score drops below 20, triggers admin notification.

Keeps a stats section to show number of anomalies, event rates, trust score trend, and confidence metrics.

If training mode is active, live mode cannot be started (should show error).

Admin Mode:

Shows detected anomalies from the current live session.

Admin can mark anomalies as “normal.”

When marked normal:

Event pattern is added to training data.

Model is updated incrementally.

Lost trust points are restored.

Provides a “Full System Reset” button that clears all training data, live data, and resets model to fresh state.

When a new live session starts, the list of anomalies in Admin Mode and Live Mode should automatically clear.

5. Trust Score System

Trust score starts at 100 for every live session.

Anomalies reduce trust score depending on severity.

Trust penalty per anomaly can be mapped to event type severity (for example, sudo_command anomaly might reduce by 20, file_change anomaly by 10, etc.).

If admin reclassifies an event as normal, the trust penalty for that event is reversed.

If trust score < 20, admin notification is triggered (console alert, email, or dashboard message).

6. Machine Learning Component

Use Isolation Forest from scikit-learn for unsupervised anomaly detection.

Train model on data collected in training mode.

Feature extraction should convert event details into numerical feature vectors.

Example feature vector:
[time_of_day, event_type_encoded, process_name_hash, network_dest_hash, auth_success_flag]

Model persistence should be done using joblib or pickle to save/load trained models.

Incremental retraining should occur if admin marks new events as normal.

Inference phase runs continuously during live mode to classify each event as normal or anomalous.

7. Database Schema

Use PostgreSQL or MongoDB. Suggested schema:

events table

id

timestamp

event_type

metadata

session_id

is_anomaly

trust_impact

sessions table

id

mode (training or live)

start_time

end_time

model_version

anomalies table

id

event_id

confidence_score

is_resolved

resolved_by

training_data table

id

feature_vector

label

8. Frontend Specification

Use Next.js + TailwindCSS + Recharts or Chart.js.

Frontend should have three tabs:

Training Mode

Live Mode

Admin Mode

Each mode corresponds to backend endpoints and behavior.

Training Mode

Simple UI with one button: “Start Training Mode” / “Stop Training Mode”.

While training is active, all incoming events are displayed in a live-updating log.

Display statistics section with counts of each event type and summary metrics.

No trust score displayed.

When training stops, trigger backend to train model.

Live Mode

Button: “Start Live Mode” / “Stop Live Mode”.

Validates that training mode has been completed before starting.

Shows real-time trust score (numeric and graphical).

Shows only anomalous events, not normal ones.

Displays warning if trust score < 20.

Includes a stats section with:

Number of anomalies detected

Current trust score

Average anomaly confidence

Graph of trust score over time

Admin Mode

Shows table/list of all anomalies from current live session.

Admin can mark any anomaly as “normal.”

This updates model and restores lost trust points.

Provides “Full Reset” button to wipe all data and retrain model from scratch.

When new live session starts, old anomalies are cleared.

Displays notifications when trust score drops below 20.

9. Data Flow Summary

start.sh starts all services and initializes model and database.

User activates Training Mode.

Events are captured and logged.

User stops training → model is trained on collected data.

User switches to Live Mode.

Live events are analyzed; anomalies are detected and logged.

Trust score adjusts dynamically.

If trust score < 20 → admin alert is triggered.

Admin reviews anomalies in Admin Mode.

Admin can mark false positives as normal or reset entire system.

10. Additional Requirements

Real-time updates implemented via WebSockets or Server-Sent Events.

Dark minimalistic UI with clear buttons and clean layout.

Live event logs should auto-scroll like a terminal.

System should support configurable severity weights for trust deduction.

Modular design allowing future microservice separation.

Logging for all backend actions.

Accuracy metric generation: system should calculate accuracy after running live mode for some time by comparing detected anomalies vs admin-marked true/false anomalies.

11. Summary for AI Code Editor

Generate a full-stack system that includes:

Three operational modes: Training, Live, and Admin.

Automated startup via start.sh.

Backend built with FastAPI for data management and ML inference.

Frontend built with Next.js and TailwindCSS for mode control and visualization.

Isolation Forest model for behavioral anomaly detection.

Dynamic trust scoring system with real-time updates and admin notifications.

Admin interface to mark anomalies, reset system, and manage live sessions.

Database schema to persist all event, session, and anomaly data.

Real-time event tracking and log visualization.

Live updating stats and trust score graphs.

The entire system represents a Zero Trust AI Behavior Tracking architecture with adaptive learning and dynamic trust evaluation.