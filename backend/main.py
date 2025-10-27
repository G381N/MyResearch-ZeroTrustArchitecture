from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import logging
from datetime import datetime

# Import routers
from routers import training, live, events, admin

# Import core components
from database import init_database, check_database_connection
from ml_engine import ml_engine
from event_collector import event_collector
from websocket_manager import websocket_manager
from config import settings

# Configure logging
import os
os.makedirs(os.path.dirname(settings.LOG_FILE), exist_ok=True)

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Zero Trust Architecture System",
    description="AI-based behavior tracking and dynamic trust scoring system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(training.router)
app.include_router(live.router)
app.include_router(events.router)
app.include_router(admin.router)

# Global variables for session management
# Note: training session is maintained in routers.training.current_training_session
current_live_session = None
# Global main event loop reference (set on startup)
MAIN_LOOP = None

@app.on_event("startup")
async def startup_event():
    """Initialize system on startup"""
    try:
        logger.info("Starting Zero Trust Architecture System...")
        
        # Check database connection
        if not check_database_connection():
            logger.error("Database connection failed")
            raise Exception("Database connection failed")
        
        # Initialize database
        if not init_database():
            logger.error("Database initialization failed")
            raise Exception("Database initialization failed")
        
        # Load ML model if available
        ml_engine.load_model()

        # Restore any active training session from the database so in-memory
        # pointer remains valid across backend restarts. We set a lightweight
        # pointer (with just the id) because the request-handlers will re-resolve
        # the full ORM instance from the DB when needed.
        try:
            from database import SessionLocal
            from models import Session as DBSession
            from routers import training as training_router
            from types import SimpleNamespace

            db = SessionLocal()
            try:
                active = db.query(DBSession).filter(DBSession.mode == 'training', DBSession.is_active == True).order_by(DBSession.start_time.desc()).first()
                if active:
                    training_router.current_training_session = SimpleNamespace(id=active.id)
                    logger.info(f"Restored active training session id={active.id} from DB on startup")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to restore active training session on startup: {e}")
        
        # Set up event collection callback
        event_collector.set_event_callback(handle_collected_event)
        # store main event loop for use by background threads
        global MAIN_LOOP
        try:
            MAIN_LOOP = asyncio.get_running_loop()
        except RuntimeError:
            MAIN_LOOP = None
        
        logger.info("System startup completed successfully")
        
    except Exception as e:
        logger.error(f"System startup failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        logger.info("Shutting down system...")
        
        # Stop event collection
        await event_collector.stop_collection()
        
        logger.info("System shutdown completed")
        
    except Exception as e:
        logger.error(f"System shutdown error: {e}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket_manager.connect(websocket)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        websocket_manager.disconnect(websocket)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Zero Trust Architecture System",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database
        db_healthy = check_database_connection()
        
        # Check ML model
        model_healthy = ml_engine.is_trained
        
        # Check WebSocket connections
        ws_connections = websocket_manager.get_connection_count()
        
        return {
            "status": "healthy" if db_healthy else "unhealthy",
            "database": "connected" if db_healthy else "disconnected",
            "model": "trained" if model_healthy else "not_trained",
            "websocket_connections": ws_connections,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

async def handle_collected_event(event_data):
    """Handle events collected from the system"""
    try:
        # This function will be called by the event collector.
        # Persist the event to the database and broadcast to connected clients
        logger.debug(f"Collected event: {event_data['event_type']}")

        # Synchronously write to the database in a thread to avoid blocking the event loop
        from database import SessionLocal
        from models import Event as DBEvent

        def _write_event():
            db = SessionLocal()
            try:
                session_id = None
                try:
                    # read current training session from the training router module
                    from routers import training as training_router
                    sid = training_router.current_training_session.id if training_router.current_training_session else None
                    session_id = sid
                except Exception:
                    session_id = None

                db_event = DBEvent(
                    event_type=event_data.get('event_type'),
                    event_metadata=event_data.get('metadata'),
                    session_id=session_id
                )
                db.add(db_event)
                db.commit()
                db.refresh(db_event)

                # If in training mode, broadcast as training event; otherwise broadcast generic event
                target_loop = MAIN_LOOP
                if target_loop:
                    payload = {
                        "id": db_event.id,
                        "timestamp": db_event.timestamp.isoformat(),
                        "event_type": db_event.event_type,
                        "metadata": db_event.event_metadata
                    }
                    if session_id:
                        payload["mode"] = "training"
                    try:
                        import asyncio
                        asyncio.run_coroutine_threadsafe(websocket_manager.broadcast_event(payload), target_loop)
                    except Exception as e:
                        logger.error(f"Failed to schedule broadcast in main loop: {e}")
                else:
                    logger.warning("MAIN_LOOP not available; cannot broadcast event from thread")

            except Exception as e:
                logger.error(f"Error writing collected event to DB: {e}")
            finally:
                db.close()

        import asyncio
        # offload DB write to thread
        await asyncio.to_thread(_write_event)
        
    except Exception as e:
        logger.error(f"Error handling collected event: {e}")

# Background task for event collection
async def start_event_collection():
    """Start event collection in background"""
    try:
        await event_collector.start_collection()
    except Exception as e:
        logger.error(f"Event collection failed: {e}")

# Start event collection when app starts
@app.on_event("startup")
async def start_background_tasks():
    """Start background tasks"""
    asyncio.create_task(start_event_collection())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
