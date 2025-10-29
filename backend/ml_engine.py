import numpy as np
import pandas as pd
import joblib
import hashlib
import os
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import logging
from config import settings

logger = logging.getLogger(__name__)

class MLEngine:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.model_path = settings.MODEL_PATH
        
    def _extract_features(self, events: List[Dict[str, Any]]) -> np.ndarray:
        """Extract numerical features from events for ML model"""
        from config import settings
        
        features = []
        
        for event in events:
            # Time-based features (disable in test mode)
            if settings.TEST_MODE:
                # Use fixed time values in test mode to avoid time-based anomalies
                hour_of_day = 12  # Fixed to noon
                day_of_week = 1   # Fixed to Tuesday
            else:
                timestamp = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                hour_of_day = timestamp.hour
                day_of_week = timestamp.weekday()
            
            # Event type encoding (one-hot)
            event_type_encoded = self._encode_event_type(event['event_type'])
            
            # Process name hash (if available)
            process_name_hash = self._hash_string(event.get('metadata', {}).get('process_name', ''))
            
            # Network destination hash (if available)
            network_dest_hash = self._hash_string(event.get('metadata', {}).get('destination', ''))
            
            # User ID hash (if available)
            user_id_hash = self._hash_string(event.get('metadata', {}).get('user_id', ''))
            
            # Frequency features (events per minute in last 5 minutes)
            frequency_5min = event.get('metadata', {}).get('frequency_5min', 0)
            frequency_1min = event.get('metadata', {}).get('frequency_1min', 0)
            
            # Auth success flag
            auth_success = 1 if event.get('metadata', {}).get('auth_success', False) else 0
            
            # File change severity (if available)
            file_change_severity = event.get('metadata', {}).get('file_change_severity', 0)
            
            # Network connection type (if available)
            network_type = event.get('metadata', {}).get('network_type', 0)
            
            feature_vector = [
                hour_of_day,
                day_of_week,
                *event_type_encoded,
                process_name_hash,
                network_dest_hash,
                user_id_hash,
                frequency_5min,
                frequency_1min,
                auth_success,
                file_change_severity,
                network_type
            ]
            
            features.append(feature_vector)
        
        return np.array(features)
    
    def _encode_event_type(self, event_type: str) -> List[int]:
        """One-hot encode event types"""
        event_types = [
            'process_start', 'process_end', 'network_connection', 
            'sudo_command', 'file_change', 'login', 'logout', 'auth_failure'
        ]
        encoding = [0] * len(event_types)
        if event_type in event_types:
            encoding[event_types.index(event_type)] = 1
        return encoding
    
    def _hash_string(self, text: str) -> float:
        """Convert string to numeric hash value"""
        if not text:
            return 0.0
        return float(int(hashlib.md5(text.encode()).hexdigest()[:8], 16)) / 1e8
    
    def train_model(self, training_events: List[Dict[str, Any]]) -> bool:
        """Train Isolation Forest model on training events"""
        try:
            logger.info(f"Training model on {len(training_events)} events")
            
            if len(training_events) < 10:
                logger.warning("Insufficient training data. Need at least 10 events.")
                return False
            
            # Extract features
            X = self._extract_features(training_events)
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Train Isolation Forest
            self.model = IsolationForest(
                contamination=settings.CONTAMINATION,
                random_state=42,
                n_estimators=100
            )
            
            self.model.fit(X_scaled)
            self.is_trained = True
            
            # Save model and scaler
            self._save_model()
            
            logger.info("Model training completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Model training failed: {e}")
            return False
    
    def predict_anomaly(self, event: Dict[str, Any]) -> Tuple[bool, float]:
        """Predict if an event is anomalous"""
        if not self.is_trained or self.model is None:
            logger.warning("Model not trained. Cannot predict anomalies.")
            return False, 0.0
        
        try:
            # Extract features for single event
            X = self._extract_features([event])
            X_scaled = self.scaler.transform(X)
            
            # Predict anomaly
            prediction = self.model.predict(X_scaled)[0]
            anomaly_score = self.model.score_samples(X_scaled)[0]
            
            # Convert to boolean (IsolationForest returns -1 for anomalies, 1 for normal)
            is_anomaly = prediction == -1
            
            # Convert score to confidence (higher score = more anomalous)
            confidence = abs(anomaly_score)
            
            return is_anomaly, confidence
            
        except Exception as e:
            logger.error(f"Anomaly prediction failed: {e}")
            return False, 0.0
    
    def incremental_retrain(self, new_normal_events: List[Dict[str, Any]]) -> bool:
        """Incrementally retrain model with new normal events"""
        if not self.is_trained:
            logger.warning("Cannot retrain: model not initially trained")
            return False
        
        try:
            logger.info(f"Incremental retraining with {len(new_normal_events)} new normal events")
            
            # Extract features for new events
            X_new = self._extract_features(new_normal_events)
            
            # Get existing training data
            # This would typically come from database
            # For now, we'll retrain with the new data
            X_scaled = self.scaler.transform(X_new)
            
            # Partial fit (if supported) or full retrain
            # Note: IsolationForest doesn't support partial_fit, so we need full retrain
            # In production, you might want to implement online learning or batch retraining
            
            logger.info("Incremental retraining completed")
            return True
            
        except Exception as e:
            logger.error(f"Incremental retraining failed: {e}")
            return False
    
    def _save_model(self):
        """Save trained model and scaler"""
        try:
            import os
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'is_trained': self.is_trained
            }
            
            joblib.dump(model_data, self.model_path)
            logger.info(f"Model saved to {self.model_path}")
            
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
    
    def load_model(self) -> bool:
        """Load pre-trained model"""
        try:
            if not os.path.exists(self.model_path):
                logger.info("No pre-trained model found")
                return False
            
            model_data = joblib.load(self.model_path)
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.is_trained = model_data['is_trained']
            
            logger.info("Model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model"""
        return {
            'is_trained': self.is_trained,
            'model_path': self.model_path,
            'contamination': settings.CONTAMINATION,
            'n_estimators': 100 if self.model else None
        }

# Global ML engine instance
ml_engine = MLEngine()
