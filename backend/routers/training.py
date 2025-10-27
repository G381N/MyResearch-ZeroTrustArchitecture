from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from database import get_db, init_database
from models import Session as DBSession, Event, TrainingData, SessionResponse
from ml_engine import ml_engine
from websocket_manager import websocket_manager
import logging
from datetime import datetime
from typing import List

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/train", tags=["training"])

# Global state
current_training_session = None
# simple in-memory lock to prevent concurrent/duplicate stops
_stop_in_progress = False

@router.post("/start")
async def start_training(db: Session = Depends(get_db)):
    """Start training mode"""
    global current_training_session
    
    try:
        # Check if training is already active
        if current_training_session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Training mode is already active"
            )
        
        # Create new training session
        training_session = DBSession(
            mode="training",
            start_time=datetime.now(),
            is_active=True
        )
        
        db.add(training_session)
        db.commit()
        db.refresh(training_session)
        
        current_training_session = training_session
        
        # Broadcast session update
        await websocket_manager.broadcast_session_update({
            'mode': 'training',
            'status': 'started',
            'session_id': training_session.id,
            'start_time': training_session.start_time.isoformat()
        })
        
        logger.info(f"Training mode started - Session ID: {training_session.id}")
        
        return {
            "message": "Training mode started",
            "session_id": training_session.id,
            "start_time": training_session.start_time.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error starting training mode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start training mode: {str(e)}"
        )

@router.post("/stop")
async def stop_training(request: Request, db: Session = Depends(get_db)):
    """Stop training mode and train the model"""
    global current_training_session
    global _stop_in_progress

    # Log request metadata so we can identify callers that invoke stop
    try:
        client_host = None
        if request.client:
            client_host = request.client.host

        ua = request.headers.get('user-agent')
        referer = request.headers.get('referer')
        origin = request.headers.get('origin')
        xff = request.headers.get('x-forwarded-for')

        logger.info(
            f"Training STOP called - client={client_host} ua={ua} referer={referer} origin={origin} xff={xff}"
        )
    except Exception:
        logger.exception("Failed to log request metadata for training stop")

    # Prevent concurrent stops from racing each other
    if _stop_in_progress:
        logger.info("Stop already in progress; ignoring duplicate stop request")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stop already in progress"
        )

    _stop_in_progress = True
    
    try:
        if not current_training_session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active training session"
            )

        # Resolve the session from DB by id so this works even if the in-memory
        # `current_training_session` is a lightweight pointer or detached ORM
        session_id = getattr(current_training_session, 'id', None)
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Active training session has no id"
            )

        db_session = db.query(DBSession).filter(DBSession.id == session_id).first()
        if not db_session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Training session not found in database"
            )

        # End the training session in the database record
        db_session.end_time = datetime.now()
        db_session.is_active = False
        db.commit()

        # Get all events from training session
        training_events = db.query(Event).filter(
            Event.session_id == db_session.id
        ).all()
        
        if len(training_events) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient training data. Need at least 10 events."
            )
        
        # Convert events to training format
        training_data = []
        for event in training_events:
            training_data.append({
                'timestamp': event.timestamp.isoformat(),
                'event_type': event.event_type,
                'metadata': event.event_metadata or {}
            })
        
        # Train the model
        model_trained = ml_engine.train_model(training_data)
        
        if not model_trained:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to train model"
            )
        
        # Update session with model version
        db_session.model_version = f"model_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        db.commit()

        # Broadcast training completion
        await websocket_manager.broadcast_session_update({
            'mode': 'training',
            'status': 'completed',
            'session_id': db_session.id,
            'end_time': db_session.end_time.isoformat() if db_session.end_time else datetime.now().isoformat(),
            'events_count': len(training_events),
            'model_trained': True
        })

        logger.info(f"Training mode stopped - Session ID: {db_session.id}, Events: {len(training_events)}")

        # Reset current session
        session_id = db_session.id
        current_training_session = None
        _stop_in_progress = False

        return {
            "message": "Training mode stopped and model trained",
            "session_id": session_id,
            "end_time": datetime.now().isoformat(),
            "events_count": len(training_events),
            "model_trained": True
        }

    except HTTPException:
        _stop_in_progress = False
        raise
    except Exception as e:
        _stop_in_progress = False
        logger.error(f"Error stopping training mode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop training mode: {str(e)}"
        )

@router.get("/status")
async def get_training_status(db: Session = Depends(get_db)):
    """Get current training status"""
    global current_training_session

    if current_training_session:
        session_id = getattr(current_training_session, 'id', None)
        # Try to resolve some additional info from DB
        events_count = 0
        start_time = None
        try:
            if session_id:
                db_sess = db.query(DBSession).filter(DBSession.id == session_id).first()
                if db_sess:
                    start_time = db_sess.start_time.isoformat() if db_sess.start_time else None
                    events_count = db.query(Event).filter(Event.session_id == session_id).count()
        except Exception:
            events_count = 0

        return {
            "active": True,
            "session_id": session_id,
            "start_time": start_time,
            "mode": "training",
            "events_count": events_count
        }
    else:
        return {
            "active": False,
            "mode": None
        }

@router.get("/sessions")
async def get_training_sessions(db: Session = Depends(get_db)):
    """Get all training sessions"""
    try:
        sessions = db.query(DBSession).filter(DBSession.mode == "training").order_by(DBSession.start_time.desc()).all()
        
        return [
            SessionResponse(
                id=session.id,
                mode=session.mode,
                start_time=session.start_time,
                end_time=session.end_time,
                is_active=session.is_active
            ) for session in sessions
        ]
        
    except Exception as e:
        logger.error(f"Error getting training sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get training sessions: {str(e)}"
        )
