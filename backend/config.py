import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Database configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/zerotrust")
    
    # API configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_PREFIX: str = "/api"
    
    # WebSocket configuration
    WS_PATH: str = "/ws"
    
    # ML Model configuration
    MODEL_PATH: str = "models/isolation_forest_model.joblib"
    CONTAMINATION: float = 0.1  # Assume 10% of events are anomalies
    
    # Trust Score Configuration
    TRUST_WEIGHTS: Dict[str, int] = {
        "auth_failure": -25,
        "sudo_command": -20,
        "network_connection": -15,
        "file_change": -10,
        "process_start": -10,
        "login": -5,
        "logout": -5,
        "process_end": -5
    }
    
    # Alert thresholds
    TRUST_ALERT_THRESHOLD: int = 20
    INITIAL_TRUST_SCORE: int = 100
    
    # Event collection configuration
    EVENT_POLL_INTERVAL: float = 1.0  # seconds
    MAX_EVENTS_PER_BATCH: int = 100
    
    # Logging configuration
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/zerotrust.log"
    
    # Frontend configuration
    FRONTEND_URL: str = "http://localhost:3000"
    
    # CORS origins
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

settings = Settings()
