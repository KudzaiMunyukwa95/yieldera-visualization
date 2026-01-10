"""
WebSocket connection manager for real-time job progress updates
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List
import json
import logging
import asyncio
from datetime import datetime

class ConnectionManager:
    """Manages WebSocket connections for real-time job updates"""
    
    def __init__(self):
        # Dictionary mapping job_id to list of connected WebSockets
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Keep track of connection metadata
        self.connection_metadata: Dict[WebSocket, dict] = {}
        
    async def connect(self, websocket: WebSocket, job_id: str):
        """Accept a WebSocket connection and associate it with a job"""
        await websocket.accept()
        
        # Add to active connections
        if job_id not in self.active_connections:
            self.active_connections[job_id] = []
        
        self.active_connections[job_id].append(websocket)
        
        # Store metadata
        self.connection_metadata[websocket] = {
            "job_id": job_id,
            "connected_at": datetime.utcnow(),
            "last_ping": datetime.utcnow()
        }
        
        logging.info(f"WebSocket connected for job {job_id}. Total connections: {self.get_total_connections()}")
        
        # Send initial connection confirmation
        await self.send_personal_message({
            "type": "connection_established",
            "job_id": job_id,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Connected to job progress updates"
        }, websocket)
    
    def disconnect(self, websocket: WebSocket, job_id: str):
        """Remove a WebSocket connection"""
        
        # Remove from active connections
        if job_id in self.active_connections:
            try:
                self.active_connections[job_id].remove(websocket)
                
                # Clean up empty job lists
                if not self.active_connections[job_id]:
                    del self.active_connections[job_id]
            except ValueError:
                # WebSocket already removed
                pass
        
        # Remove metadata
        if websocket in self.connection_metadata:
            del self.connection_metadata[websocket]
        
        logging.info(f"WebSocket disconnected for job {job_id}. Total connections: {self.get_total_connections()}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to a specific WebSocket connection"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logging.error(f"Failed to send personal message: {e}")
            # Remove broken connection
            if websocket in self.connection_metadata:
                job_id = self.connection_metadata[websocket]["job_id"]
                self.disconnect(websocket, job_id)
    
    async def send_job_update(self, job_id: str, message: dict):
        """Send update to all connections for a specific job"""
        
        if job_id not in self.active_connections:
            logging.debug(f"No active connections for job {job_id}")
            return
        
        # Add timestamp to message
        message["timestamp"] = datetime.utcnow().isoformat()
        message["job_id"] = job_id
        
        # Send to all connected clients for this job
        broken_connections = []
        
        for websocket in self.active_connections[job_id][:]:  # Create copy to iterate over
            try:
                await websocket.send_text(json.dumps(message))
                
                # Update last communication time
                if websocket in self.connection_metadata:
                    self.connection_metadata[websocket]["last_ping"] = datetime.utcnow()
                    
            except Exception as e:
                logging.error(f"Failed to send job update to websocket: {e}")
                broken_connections.append(websocket)
        
        # Clean up broken connections
        for websocket in broken_connections:
            self.disconnect(websocket, job_id)
        
        logging.debug(f"Sent update to {len(self.active_connections.get(job_id, []))} connections for job {job_id}")
    
    async def broadcast_system_message(self, message: dict):
        """Send message to all connected clients"""
        
        message["timestamp"] = datetime.utcnow().isoformat()
        message["type"] = "system_broadcast"
        
        broken_connections = []
        total_sent = 0
        
        for job_id, websockets in self.active_connections.items():
            for websocket in websockets[:]:  # Create copy
                try:
                    await websocket.send_text(json.dumps(message))
                    total_sent += 1
                except Exception as e:
                    logging.error(f"Failed to broadcast to websocket: {e}")
                    broken_connections.append((websocket, job_id))
        
        # Clean up broken connections
        for websocket, job_id in broken_connections:
            self.disconnect(websocket, job_id)
        
        logging.info(f"Broadcast system message to {total_sent} connections")
    
    def get_total_connections(self) -> int:
        """Get total number of active WebSocket connections"""
        return sum(len(websockets) for websockets in self.active_connections.values())
    
    def get_job_connections(self, job_id: str) -> int:
        """Get number of connections for a specific job"""
        return len(self.active_connections.get(job_id, []))
    
    def get_connection_stats(self) -> dict:
        """Get connection statistics"""
        total_connections = self.get_total_connections()
        active_jobs = len(self.active_connections)
        
        # Calculate average connections per job
        avg_connections = total_connections / max(active_jobs, 1)
        
        # Get oldest connection age
        oldest_connection = None
        if self.connection_metadata:
            oldest_time = min(meta["connected_at"] for meta in self.connection_metadata.values())
            oldest_connection = (datetime.utcnow() - oldest_time).total_seconds()
        
        return {
            "total_connections": total_connections,
            "active_jobs": active_jobs,
            "average_connections_per_job": round(avg_connections, 2),
            "oldest_connection_seconds": oldest_connection
        }
    
    async def ping_all_connections(self):
        """Send ping to all connections to keep them alive"""
        
        ping_message = {
            "type": "ping",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        broken_connections = []
        
        for job_id, websockets in self.active_connections.items():
            for websocket in websockets[:]:  # Create copy
                try:
                    await websocket.ping()
                    
                    # Update metadata
                    if websocket in self.connection_metadata:
                        self.connection_metadata[websocket]["last_ping"] = datetime.utcnow()
                        
                except Exception as e:
                    logging.debug(f"Ping failed for websocket: {e}")
                    broken_connections.append((websocket, job_id))
        
        # Clean up broken connections
        for websocket, job_id in broken_connections:
            self.disconnect(websocket, job_id)
    
    async def cleanup_stale_connections(self, max_age_seconds: int = 3600):
        """Remove connections that haven't been active for too long"""
        
        cutoff_time = datetime.utcnow()
        stale_connections = []
        
        for websocket, metadata in self.connection_metadata.items():
            if (cutoff_time - metadata["last_ping"]).total_seconds() > max_age_seconds:
                stale_connections.append((websocket, metadata["job_id"]))
        
        # Clean up stale connections
        for websocket, job_id in stale_connections:
            try:
                await websocket.close(code=1000, reason="Connection timeout")
            except:
                pass
            self.disconnect(websocket, job_id)
        
        if stale_connections:
            logging.info(f"Cleaned up {len(stale_connections)} stale WebSocket connections")

# =====================================
# BACKGROUND TASKS
# =====================================

class WebSocketManager:
    """Manager class with background tasks for WebSocket maintenance"""
    
    def __init__(self):
        self.connection_manager = ConnectionManager()
        self._maintenance_task = None
    
    async def start_maintenance(self):
        """Start background maintenance tasks"""
        if self._maintenance_task is None:
            self._maintenance_task = asyncio.create_task(self._maintenance_loop())
            logging.info("Started WebSocket maintenance loop")
    
    async def stop_maintenance(self):
        """Stop background maintenance tasks"""
        if self._maintenance_task:
            self._maintenance_task.cancel()
            try:
                await self._maintenance_task
            except asyncio.CancelledError:
                pass
            self._maintenance_task = None
            logging.info("Stopped WebSocket maintenance loop")
    
    async def _maintenance_loop(self):
        """Background loop for WebSocket maintenance"""
        while True:
            try:
                # Ping all connections every 30 seconds
                await self.connection_manager.ping_all_connections()
                
                # Clean up stale connections every 5 minutes
                await self.connection_manager.cleanup_stale_connections()
                
                # Log connection statistics
                stats = self.connection_manager.get_connection_stats()
                if stats["total_connections"] > 0:
                    logging.debug(f"WebSocket stats: {stats}")
                
                # Wait before next maintenance cycle
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"WebSocket maintenance error: {e}")
                await asyncio.sleep(60)  # Wait longer on error

# =====================================
# UTILITY FUNCTIONS
# =====================================

def format_job_progress_message(progress: int, message: str, statistics: dict = None) -> dict:
    """Format a standardized job progress message"""
    
    msg = {
        "type": "progress_update",
        "progress": progress,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if statistics:
        msg["statistics"] = statistics
    
    return msg

def format_job_completion_message(statistics: dict, file_paths: dict = None) -> dict:
    """Format a standardized job completion message"""
    
    msg = {
        "type": "job_completed",
        "status": "completed",
        "progress": 100,
        "message": "Analysis completed successfully",
        "timestamp": datetime.utcnow().isoformat(),
        "statistics": statistics
    }
    
    if file_paths:
        msg["files"] = file_paths
    
    return msg

def format_job_error_message(error: str, retry_count: int = 0) -> dict:
    """Format a standardized job error message"""
    
    return {
        "type": "job_failed",
        "status": "failed",
        "message": f"Analysis failed: {error}",
        "error": error,
        "retry_count": retry_count,
        "timestamp": datetime.utcnow().isoformat()
    }

def format_system_message(message_type: str, message: str, data: dict = None) -> dict:
    """Format a standardized system message"""
    
    msg = {
        "type": f"system_{message_type}",
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if data:
        msg.update(data)
    
    return msg

# Create global manager instance
websocket_manager = WebSocketManager()
