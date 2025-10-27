from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import Event, Anomaly, EventCreate, EventResponse
from ml_engine import ml_engine
from trust_scorer import trust_scorer
from websocket_manager import websocket_manager
from routers import training as training_router, live as live_router
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/events", tags=["events"])

@router.post("/")
async def create_event(event: EventCreate, db: Session = Depends(get_db)):
    """Create a new event"""
    try:
        # Determine session association: prefer training session, otherwise live session
        session_id = None
        try:
            if getattr(training_router, 'current_training_session', None):
                session_id = getattr(training_router.current_training_session, 'id', None)
            elif getattr(live_router, 'current_live_session', None):
                session_id = getattr(live_router.current_live_session, 'id', None)
        except Exception:
            session_id = None

        # Create event record
        db_event = Event(
            event_type=event.event_type,
            event_metadata=event.event_metadata,
            session_id=session_id
        )
        
        db.add(db_event)
        db.commit()
        db.refresh(db_event)
        
        # Handle based on current mode (use module-level pointers to get up-to-date values)
        if getattr(training_router, 'current_training_session', None):
            # Training mode - just store the event
            await _handle_training_event(db_event, db)
        elif getattr(live_router, 'current_live_session', None):
            # Live mode - analyze for anomalies
            await _handle_live_event(db_event, db)
        
        # Broadcast event to all connected clients
        await websocket_manager.broadcast_event({
            "id": db_event.id,
            "timestamp": db_event.timestamp.isoformat(),
            "event_type": db_event.event_type,
                "metadata": db_event.event_metadata,
            "is_anomaly": db_event.is_anomaly,
            "trust_impact": db_event.trust_impact,
            "confidence_score": db_event.confidence_score
        })
        
        return EventResponse(
            id=db_event.id,
            timestamp=db_event.timestamp,
            event_type=db_event.event_type,
            event_metadata=db_event.event_metadata,
            is_anomaly=db_event.is_anomaly,
            trust_impact=db_event.trust_impact,
            confidence_score=db_event.confidence_score
        )
        
    except Exception as e:
        logger.error(f"Error creating event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create event: {str(e)}"
        )

async def _handle_training_event(event: Event, db: Session):
    """Handle event during training mode"""
    try:
        # In training mode, we just store events for later model training
        logger.debug(f"Training event stored: {event.event_type}")
        
        # Broadcast training event
        await websocket_manager.broadcast_event({
            "id": event.id,
            "timestamp": event.timestamp.isoformat(),
            "event_type": event.event_type,
            "metadata": event.event_metadata,
            "mode": "training"
        })
        
    except Exception as e:
        logger.error(f"Error handling training event: {e}")

async def _handle_live_event(event: Event, db: Session):
    """Handle event during live mode"""
    try:
        # Prepare event data for ML analysis
        event_data = {
            'timestamp': event.timestamp.isoformat(),
            'event_type': event.event_type,
            'metadata': event.event_metadata or {}
        }
        
        # Analyze event for anomalies
        is_anomaly, confidence = ml_engine.predict_anomaly(event_data)
        
        # Update event with anomaly information
        event.is_anomaly = is_anomaly
        event.confidence_score = confidence
        
        if is_anomaly:
            # Create anomaly record
            anomaly = Anomaly(
                event_id=event.id,
                session_id=current_live_session.id,
                confidence_score=confidence,
                is_resolved=False
            )
            
            db.add(anomaly)
            
            # Update trust score
            trust_update = trust_scorer.update_trust_score(
                event.id, event.event_type, confidence, is_anomaly
            )
            
            event.trust_impact = trust_update['deduction']
            
            # Broadcast anomaly
            await websocket_manager.broadcast_anomaly({
                "id": anomaly.id,
                "event_id": event.id,
                "confidence_score": confidence,
                "event_type": event.event_type,
                "timestamp": event.timestamp.isoformat(),
                "metadata": event.event_metadata
            })
            
            # Check for trust score alert
            if trust_update['alert_triggered']:
                await websocket_manager.broadcast_alert({
                    "type": "trust_score_low",
                    "message": f"Trust score dropped to {trust_scorer.get_current_score()}",
                    "trust_score": trust_scorer.get_current_score(),
                    "threshold": 20
                })
        
        # Update trust score
        await websocket_manager.broadcast_trust_update({
            "current_score": trust_scorer.get_current_score(),
            "change": trust_update.get('change', 0) if is_anomaly else 0,
            "session_id": current_live_session.id,
            "timestamp": datetime.now().isoformat()
        })
        
        # Commit changes
        db.commit()
        
        logger.info(f"Live event processed: {event.event_type}, Anomaly: {is_anomaly}, Trust: {trust_scorer.get_current_score()}")
        
    except Exception as e:
        logger.error(f"Error handling live event: {e}")
        db.rollback()

@router.get("/")
async def get_events(
    session_id: int = None,
    event_type: str = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get events with optional filtering"""
    try:
        query = db.query(Event)
        
        if session_id:
            query = query.filter(Event.session_id == session_id)
        
        if event_type:
            query = query.filter(Event.event_type == event_type)
        
        events = query.order_by(Event.timestamp.desc()).limit(limit).all()
        
        return [
            EventResponse(
                id=event.id,
                timestamp=event.timestamp,
                event_type=event.event_type,
                event_metadata=event.event_metadata,
                is_anomaly=event.is_anomaly,
                trust_impact=event.trust_impact,
                confidence_score=event.confidence_score
            ) for event in events
        ]
        
    except Exception as e:
        logger.error(f"Error getting events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get events: {str(e)}"
        )

@router.get("/recent")
async def get_recent_events(limit: int = 50, db: Session = Depends(get_db)):
    """Get recent events for real-time display"""
    try:
        events = db.query(Event).order_by(Event.timestamp.desc()).limit(limit).all()

        # Build a JSON-safe list of events (sanitize metadata)
        import json
        result = []
        for event in events:
            meta = event.event_metadata
            try:
                # Ensure metadata is JSON-serializable
                meta_json = json.loads(json.dumps(meta, default=str))
            except Exception:
                meta_json = {}

            result.append({
                "id": event.id,
                "timestamp": event.timestamp.isoformat(),
                "event_type": event.event_type,
                "metadata": meta_json,
                "is_anomaly": event.is_anomaly,
                "trust_impact": event.trust_impact,
                "confidence_score": event.confidence_score
            })

        return result
        
    except Exception as e:
        logger.error(f"Error getting recent events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recent events: {str(e)}"
        )
