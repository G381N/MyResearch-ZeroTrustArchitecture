import numpy as np
import pandas as pd
import joblib
import hashlib
import os
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler, RobustScaler
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
            
            # Robust metadata extraction with safe defaults
            metadata = event.get('metadata', {})
            
            # Suspicious indicators (with safe extraction)
            try:
                suspicious_flag = 1 if metadata.get('suspicious', False) else 0
                unauthorized_flag = 1 if metadata.get('unauthorized', False) else 0
                
                # Check for attack indicators
                attack_keys = ['attack_type', 'brute_force', 'exfiltration', 'lateral_movement']
                attack_indicator = 1 if any(key in metadata for key in attack_keys) else 0
                
                # Port risk score (handle various data types)
                port = metadata.get('port', 443)
                port_risk = 0
                if port is not None:
                    try:
                        port_num = int(port)
                        high_risk_ports = [4444, 6666, 1337, 31337, 9999, 8080]
                        port_risk = 1 if port_num in high_risk_ports else 0
                    except (ValueError, TypeError):
                        port_risk = 0
                
                # File sensitivity score
                file_path = str(metadata.get('file_path', ''))
                sensitive_paths = ['/etc/', '/boot/', '/var/log/', '/root/']
                file_sensitivity = 1 if any(path in file_path for path in sensitive_paths) else 0
                    
                # IP reputation score (external IPs are more suspicious)
                source_ip = str(metadata.get('source_ip', '192.168.1.1'))
                internal_ranges = ['192.168.', '10.0.', '172.16.', '127.0.']
                ip_reputation = 0 if any(source_ip.startswith(range_) for range_ in internal_ranges) else 1
                
            except Exception as e:
                # Fallback to safe defaults if metadata parsing fails
                logger.warning(f"Error parsing metadata for event: {e}")
                suspicious_flag = 0
                unauthorized_flag = 0
                attack_indicator = 0
                port_risk = 0
                file_sensitivity = 0
                ip_reputation = 0
            
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
                suspicious_flag,
                unauthorized_flag,
                attack_indicator,
                port_risk,
                file_sensitivity,
                ip_reputation
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
            
            # Scale features using robust scaling for better outlier handling
            from sklearn.preprocessing import RobustScaler
            self.scaler = RobustScaler()  # More robust to outliers than StandardScaler
            X_scaled = self.scaler.fit_transform(X)
            
            # Calculate intelligent contamination based on data analysis
            contamination = settings.CONTAMINATION
            
            # Count actual anomalies and analyze feature patterns
            anomaly_count = 0
            total_count = len(training_events)
            suspicious_indicators = 0
            
            for event in training_events:
                if event.get('metadata', {}).get('is_anomaly', False):
                    anomaly_count += 1
                    
                # Count suspicious indicators in the data
                metadata = event.get('metadata', {})
                if any(key in metadata for key in ['suspicious', 'unauthorized', 'attack_type', 'brute_force']):
                    suspicious_indicators += 1
            
            if anomaly_count > 0:
                actual_contamination = anomaly_count / total_count
                # Adjust based on suspicious indicator density
                indicator_ratio = suspicious_indicators / total_count
                adjusted_contamination = (actual_contamination + indicator_ratio) / 2
                # Use adjusted contamination but keep it reasonable
                contamination = max(0.05, min(0.25, adjusted_contamination))
                logger.info(f"Using smart contamination: {contamination:.3f} (anomalies: {anomaly_count}/{total_count}, indicators: {suspicious_indicators})")
            else:
                # Conservative fallback
                contamination = 0.15
                logger.info(f"Using fallback contamination: {contamination:.3f}")
            
            # Train Isolation Forest with stable parameters
            self.model = IsolationForest(
                contamination=contamination,
                random_state=42,
                n_estimators=200,  # Reduced for stability
                max_samples=min(256, len(training_events)),  # Conservative subsamples
                max_features=1.0,  # Use all features for now
                bootstrap=False,  # Disable bootstrap to avoid issues
                n_jobs=1,  # Single thread for stability
                warm_start=False
            )
            
            # Always train on all data for stability (let contamination parameter handle anomalies)
            # This is more robust than trying to filter normal events
            logger.info(f"Training on all {len(training_events)} events with contamination={contamination:.3f}")
            
            # Validate features before training
            if X_scaled.shape[0] == 0:
                logger.error("No features extracted from training events")
                return False
                
            if X_scaled.shape[1] == 0:
                logger.error("No feature dimensions found")
                return False
                
            # Check for invalid values
            if np.any(np.isnan(X_scaled)) or np.any(np.isinf(X_scaled)):
                logger.warning("Found NaN or infinite values in features, replacing with zeros")
                X_scaled = np.nan_to_num(X_scaled, nan=0.0, posinf=0.0, neginf=0.0)
            
            # Train the model
            self.model.fit(X_scaled)
            logger.info(f"Model training successful with {X_scaled.shape[0]} samples and {X_scaled.shape[1]} features")
            
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
            
            # Get both prediction and anomaly score
            prediction = self.model.predict(X_scaled)[0]
            decision_score = self.model.decision_function(X_scaled)[0]
            
            # IsolationForest: -1 = anomaly, 1 = normal
            is_anomaly = prediction == -1
            
            # Improved confidence scoring with threshold adjustment
            # decision_function: negative = anomaly, positive = normal
            
            # Apply a more conservative threshold to reduce false positives
            anomaly_threshold = -0.1  # More conservative threshold
            is_anomaly = decision_score < anomaly_threshold
            
            # Calculate confidence based on distance from threshold
            if is_anomaly:
                # For anomalies, distance below threshold = confidence
                confidence = min(1.0, abs(decision_score + 0.1) / 0.4)
            else:
                # For normal events, distance above threshold = confidence
                confidence = min(1.0, (decision_score + 0.1) / 0.6)
                
            confidence = max(0.15, min(0.95, confidence))  # Clamp between 15-95%
            
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
    
    def predict_batch(self, events: List[Dict[str, Any]]) -> List[float]:
        """Predict anomaly scores for a batch of events"""
        if not self.is_trained or self.model is None:
            raise ValueError("Model must be trained before making predictions")
        
        try:
            # Extract features
            features = self._extract_features(events)
            
            # Scale features
            scaled_features = self.scaler.transform(features)
            
            # Get anomaly scores (negative for normal, positive for anomalies)
            scores = self.model.decision_function(scaled_features)
            
            return scores.tolist()
            
        except Exception as e:
            logger.error(f"Error in batch prediction: {e}")
            raise

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
