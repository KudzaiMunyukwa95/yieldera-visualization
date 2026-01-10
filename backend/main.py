"""
Yieldera Automated Visualization System - Main Application
Optimized for Render.com deployment with PostgreSQL
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
import asyncio
import uuid
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
import tempfile

# Database imports
from sqlalchemy.orm import Session
from .database import get_db, engine
from .models import VisualizationJob, Base
from .celery_app import process_visualization_job

# API modules
from .api.visualization import router as visualization_router
from .api.health import router as health_router
from .websocket_manager import ConnectionManager

# Configuration
from .config import settings

# Create tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Yieldera Visualization API",
    description="Automated cartographic visualization for agricultural intelligence",
    version="1.0.0",
    docs_url="/api/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/api/redoc" if settings.ENVIRONMENT == "development" else None,
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow ALL origins
    allow_credentials=False,  # Disable credentials to allow wildcard origin
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
manager = ConnectionManager()

# Include API routers
app.include_router(visualization_router, prefix="/api/v1", tags=["visualization"])
app.include_router(health_router, prefix="/api", tags=["health"])

# =====================================
# ROOT ENDPOINTS
# =====================================

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "service": "Yieldera Automated Visualization System",
        "status": "online",
        "version": "1.0.0",
        "docs": "/api/docs",
        "health": "/api/health"
    }

# =====================================
# WEBSOCKET ENDPOINTS
# =====================================

@app.websocket("/ws/visualization-jobs/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str, db: Session = Depends(get_db)):
    """WebSocket endpoint for real-time job progress updates"""
    
    await manager.connect(websocket, job_id)
    
    try:
        # Send initial job status
        job = db.query(VisualizationJob).filter(VisualizationJob.id == job_id).first()
        if job:
            await websocket.send_json({
                "type": "status_update",
                "status": job.status,
                "progress": job.progress,
                "message": job.message
            })
        
        while True:
            # Keep connection alive and handle client messages
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                
                # Handle client commands
                try:
                    command = json.loads(data)
                    if command.get('action') == 'get_status':
                        # Send current status
                        job = db.query(VisualizationJob).filter(VisualizationJob.id == job_id).first()
                        if job:
                            await websocket.send_json({
                                'type': 'status_update',
                                'status': job.status,
                                'progress': job.progress,
                                'message': job.message
                            })
                except json.JSONDecodeError:
                    pass
                    
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.ping()
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, job_id)
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, job_id)

# =====================================
# STARTUP/SHUTDOWN EVENTS
# =====================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    
    logging.info("🚀 Starting Yieldera Visualization API")
    
    # Ensure storage directory exists
    os.makedirs(settings.VISUALIZATION_STORAGE_PATH, exist_ok=True)
    
# Test database connection
    try:
        from .database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logging.info("✅ Database connection successful")
    except Exception as e:
        logging.error(f"❌ Database connection failed: {e}")
    
    # Test Redis connection
    try:
        import redis
        if settings.REDIS_URL:
            r = redis.from_url(settings.REDIS_URL)
            r.ping()
            logging.info("✅ Redis connection successful")
        else:
             logging.warning("⚠️  Redis URL not set, skipping connection test")
    except Exception as e:
        logging.error(f"❌ Redis connection failed: {e}")
    
    # Initialize Earth Engine (if credentials available)
    try:
        import ee
        if settings.GOOGLE_APPLICATION_CREDENTIALS_JSON:
            # Pass raw JSON string to ServiceAccountCredentials
            # It expects the JSON content as a string, not a dict
            credentials = ee.ServiceAccountCredentials(None, key_data=settings.GOOGLE_APPLICATION_CREDENTIALS_JSON)
            ee.Initialize(credentials)
            logging.info("✅ Google Earth Engine initialized")
        else:
            logging.warning("⚠️  No GEE credentials provided")
    except Exception as e:
        logging.error(f"❌ Earth Engine initialization failed: {e}")
    
    logging.info("🎯 Yieldera Visualization API ready for requests")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logging.info("👋 Shutting down Yieldera Visualization API")

# =====================================
# GLOBAL EXCEPTION HANDLERS
# =====================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for production"""
    
    logging.error(f"Global exception: {exc}", exc_info=True)
    
    if settings.ENVIRONMENT == "development":
        # In development, show full error details
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc),
                "type": type(exc).__name__
            }
        )
    else:
        # In production, hide error details
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred. Please try again later."
            }
        )

# =====================================
# MIDDLEWARE
# =====================================

@app.middleware("http")
async def logging_middleware(request, call_next):
    """Log all requests for monitoring"""
    
    start_time = datetime.utcnow()
    
    response = await call_next(request)
    
    process_time = (datetime.utcnow() - start_time).total_seconds()
    
    logging.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )
    
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=int(os.getenv("PORT", 8000)),
        reload=settings.ENVIRONMENT == "development"
    )
