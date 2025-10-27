from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from datetime import datetime
from typing import Optional, Dict, Any

class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    mode = Column(String(20), nullable=False)  # 'training' or 'live'
    start_time = Column(DateTime, default=func.now())
    end_time = Column(DateTime, nullable=True)
    model_version = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    events = relationship("Event", back_populates="session")
    anomalies = relationship("Anomaly", back_populates="session")

class Event(Base):
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=func.now())
    event_type = Column(String(50), nullable=False)
    event_metadata = Column(JSON, nullable=True)  # Store event details as JSON
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)
    is_anomaly = Column(Boolean, default=False)
    trust_impact = Column(Float, default=0.0)
    confidence_score = Column(Float, nullable=True)
    
    # Relationships
    session = relationship("Session", back_populates="events")
    anomaly = relationship("Anomaly", back_populates="event", uselist=False)

class Anomaly(Base):
    __tablename__ = "anomalies"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    confidence_score = Column(Float, nullable=False)
    is_resolved = Column(Boolean, default=False)
    resolved_by = Column(String(100), nullable=True)  # 'admin' or 'system'
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    event = relationship("Event", back_populates="anomaly")
    session = relationship("Session", back_populates="anomalies")

class TrainingData(Base):
    __tablename__ = "training_data"
    
    id = Column(Integer, primary_key=True, index=True)
    feature_vector = Column(JSON, nullable=False)  # Store as JSON array
    label = Column(String(20), nullable=False)  # 'normal' or 'anomaly'
    event_type = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=func.now())
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)
    
    # Relationships
    session = relationship("Session")

# Pydantic models for API serialization
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class EventCreate(BaseModel):
    event_type: str
    event_metadata: Optional[Dict[str, Any]] = None

class EventResponse(BaseModel):
    id: int
    timestamp: datetime
    event_type: str
    event_metadata: Optional[Dict[str, Any]]
    is_anomaly: bool
    trust_impact: float
    confidence_score: Optional[float]
    
    class Config:
        from_attributes = True

class SessionResponse(BaseModel):
    id: int
    mode: str
    start_time: datetime
    end_time: Optional[datetime]
    is_active: bool
    
    class Config:
        from_attributes = True

class AnomalyResponse(BaseModel):
    id: int
    event_id: int
    confidence_score: float
    is_resolved: bool
    resolved_by: Optional[str]
    created_at: datetime
    event: EventResponse
    
    class Config:
        from_attributes = True

class TrustScoreResponse(BaseModel):
    current_score: float
    session_id: Optional[int]
    last_updated: datetime

class StatsResponse(BaseModel):
    total_events: int
    anomaly_count: int
    trust_score: float
    event_counts: Dict[str, int]
    average_confidence: Optional[float]
    session_duration: Optional[float]  # in minutes
