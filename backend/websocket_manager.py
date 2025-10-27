import asyncio
import json
from typing import Dict, Any, List
from fastapi import WebSocket, WebSocketDisconnect
import logging

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_count = 0
    
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_count += 1
        logger.info(f"WebSocket connected. Total connections: {self.connection_count}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.connection_count -= 1
            logger.info(f"WebSocket disconnected. Total connections: {self.connection_count}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to specific WebSocket connection"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: str):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            self.disconnect(connection)
    
    async def broadcast_event(self, event: Dict[str, Any]):
        """Broadcast event data to all clients"""
        message = json.dumps({
            'type': 'event',
            'data': event
        })
        await self.broadcast(message)
    
    async def broadcast_trust_update(self, trust_data: Dict[str, Any]):
        """Broadcast trust score update to all clients"""
        message = json.dumps({
            'type': 'trust_update',
            'data': trust_data
        })
        await self.broadcast(message)
    
    async def broadcast_anomaly(self, anomaly: Dict[str, Any]):
        """Broadcast anomaly detection to all clients"""
        message = json.dumps({
            'type': 'anomaly',
            'data': anomaly
        })
        await self.broadcast(message)
    
    async def broadcast_session_update(self, session_data: Dict[str, Any]):
        """Broadcast session status update to all clients"""
        message = json.dumps({
            'type': 'session_update',
            'data': session_data
        })
        await self.broadcast(message)
    
    async def broadcast_stats(self, stats: Dict[str, Any]):
        """Broadcast statistics update to all clients"""
        message = json.dumps({
            'type': 'stats',
            'data': stats
        })
        await self.broadcast(message)
    
    async def broadcast_alert(self, alert_data: Dict[str, Any]):
        """Broadcast alert to all clients"""
        message = json.dumps({
            'type': 'alert',
            'data': alert_data
        })
        await self.broadcast(message)
    
    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return self.connection_count
    
    async def send_system_status(self):
        """Send current system status to all clients"""
        status = {
            'connections': self.connection_count,
            'timestamp': asyncio.get_event_loop().time()
        }
        
        message = json.dumps({
            'type': 'system_status',
            'data': status
        })
        await self.broadcast(message)

# Global WebSocket manager instance
websocket_manager = WebSocketManager()
