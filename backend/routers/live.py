from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import Session as DBSession, Event, Anomaly, TrustScoreResponse, StatsResponse
from ml_engine import ml_engine
from trust_scorer import trust_scorer
from websocket_manager import websocket_manager
import logging
from datetime import datetime
from typing import Dict, Any, List
from collections import Counter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/live", tags=["live"])

# Global state
current_live_session = None

@router.post("/start")
async def start_live_mode(db: Session = Depends(get_db)):
    """Start live mode"""
    global current_live_session
    
    try:
        # Check if live mode is already active
        if current_live_session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Live mode is already active"
            )
        
        # Check if model is trained
        if not ml_engine.is_trained:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Training not yet completed. Please complete training first."
            )
        
        # Create new live session
        live_session = DBSession(
            mode="live",
            start_time=datetime.now(),
            is_active=True
        )
        
        db.add(live_session)
        db.commit()
        db.refresh(live_session)
        
        current_live_session = live_session
        
        # Initialize trust score
        trust_scorer.initialize_session(live_session.id)
        
        # Broadcast session update
        await websocket_manager.broadcast_session_update({
            'mode': 'live',
            'status': 'started',
            'session_id': live_session.id,
            'start_time': live_session.start_time.isoformat(),
            'trust_score': trust_scorer.get_current_score()
        })
        
        logger.info(f"Live mode started - Session ID: {live_session.id}")
        
        return {
            "message": "Live mode started",
            "session_id": live_session.id,
            "start_time": live_session.start_time.isoformat(),
            "trust_score": trust_scorer.get_current_score()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting live mode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start live mode: {str(e)}"
        )

@router.post("/stop")
async def stop_live_mode(db: Session = Depends(get_db)):
    """Stop live mode"""
    global current_live_session
    
    try:
        if not current_live_session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active live session"
            )
        
        # End the live session
        current_live_session.end_time = datetime.now()
        current_live_session.is_active = False
        db.commit()
        
        # Broadcast session update
        await websocket_manager.broadcast_session_update({
            'mode': 'live',
            'status': 'stopped',
            'session_id': current_live_session.id,
            'end_time': current_live_session.end_time.isoformat(),
            'final_trust_score': trust_scorer.get_current_score()
        })
        
        logger.info(f"Live mode stopped - Session ID: {current_live_session.id}")
        
        # Reset current session
        session_id = current_live_session.id
        current_live_session = None
        
        return {
            "message": "Live mode stopped",
            "session_id": session_id,
            "end_time": datetime.now().isoformat(),
            "final_trust_score": trust_scorer.get_current_score()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping live mode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop live mode: {str(e)}"
        )

@router.get("/trust")
async def get_trust_score():
    """Get current trust score"""
    try:
        return TrustScoreResponse(
            current_score=trust_scorer.get_current_score(),
            session_id=current_live_session.id if current_live_session else None,
            last_updated=datetime.now()
        )
    except Exception as e:
        logger.error(f"Error getting trust score: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trust score: {str(e)}"
        )

@router.get("/stats")
async def get_live_stats(db: Session = Depends(get_db)):
    """Get live mode statistics"""
    try:
        if not current_live_session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active live session"
            )
        
        # Get events from current session
        events = db.query(Event).filter(Event.session_id == current_live_session.id).all()
        
        # Get anomalies from current session
        anomalies = db.query(Anomaly).filter(
            Anomaly.session_id == current_live_session.id,
            Anomaly.is_resolved == False
        ).all()
        
        # Calculate statistics
        event_counts = Counter(event.event_type for event in events)
        anomaly_count = len(anomalies)
        average_confidence = sum(anomaly.confidence_score for anomaly in anomalies) / len(anomalies) if anomalies else None
        
        # Calculate session duration
        session_duration = None
        if current_live_session.start_time:
            duration = datetime.now() - current_live_session.start_time
            session_duration = duration.total_seconds() / 60  # in minutes
        
        return StatsResponse(
            total_events=len(events),
            anomaly_count=anomaly_count,
            trust_score=trust_scorer.get_current_score(),
            event_counts=dict(event_counts),
            average_confidence=average_confidence,
            session_duration=session_duration
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting live stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get live stats: {str(e)}"
        )

@router.get("/anomalies")
async def get_anomalies(db: Session = Depends(get_db)):
    """Get anomalies from current live session"""
    try:
        if not current_live_session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active live session"
            )
        
        anomalies = db.query(Anomaly).filter(
            Anomaly.session_id == current_live_session.id,
            Anomaly.is_resolved == False
        ).order_by(Anomaly.created_at.desc()).all()
        
        return [
            {
                "id": anomaly.id,
                "event_id": anomaly.event_id,
                "confidence_score": anomaly.confidence_score,
                "is_resolved": anomaly.is_resolved,
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

@router.get("/status")
async def get_live_status():
    """Get current live mode status"""
    global current_live_session
    
    if current_live_session:
        return {
            "active": True,
            "session_id": current_live_session.id,
            "start_time": current_live_session.start_time.isoformat(),
            "mode": "live",
            "trust_score": trust_scorer.get_current_score()
        }
    else:
        return {
            "active": False,
            "mode": None,
            "trust_score": None
        }
