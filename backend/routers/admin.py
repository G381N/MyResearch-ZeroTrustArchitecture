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
        return {
            "training_active": current_training_session is not None,
            "live_active": current_live_session is not None,
            "model_trained": ml_engine.is_trained,
            "trust_score": trust_scorer.get_current_score(),
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
