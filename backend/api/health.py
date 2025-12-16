"""
Health check and monitoring API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import redis
import logging
import os
import psutil

from ..database import get_db, test_connection
from ..models import get_system_stats, SystemHealth
from ..config import settings
from ..celery_app import get_active_tasks

router = APIRouter(tags=["health"])

# =====================================
# HEALTH CHECK ENDPOINTS
# =====================================

@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Comprehensive health check for all system components
    """
    
    health_status = {
        "service": "Yieldera Visualization System",
        "timestamp": datetime.utcnow().isoformat(),
        "status": "healthy",
        "checks": {}
    }
    
    # Database health check
    try:
        db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {
            "status": "healthy",
            "response_time_ms": 0  # Could measure actual response time
        }
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # Redis health check
    try:
        r = redis.from_url(settings.REDIS_URL)
        ping_result = r.ping()
        health_status["checks"]["redis"] = {
            "status": "healthy" if ping_result else "unhealthy",
            "ping_success": ping_result
        }
    except Exception as e:
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Earth Engine health check
    try:
        import ee
        if settings.gee_config:
            credentials = ee.ServiceAccountCredentials(None, key_data=settings.gee_config)
            ee.Initialize(credentials)
            # Simple test to verify authentication
            ee.Number(1).getInfo()  # This will fail if auth is wrong
            health_status["checks"]["earth_engine"] = {
                "status": "healthy",
                "authenticated": True
            }
        else:
            health_status["checks"]["earth_engine"] = {
                "status": "degraded",
                "authenticated": False,
                "message": "No credentials configured"
            }
    except Exception as e:
        health_status["checks"]["earth_engine"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        if health_status["status"] == "healthy":
            health_status["status"] = "degraded"
    
    # Storage health check
    try:
        storage_path = settings.VISUALIZATION_STORAGE_PATH
        if os.path.exists(storage_path):
            disk_usage = psutil.disk_usage(storage_path)
            free_space_gb = disk_usage.free / (1024**3)
            health_status["checks"]["storage"] = {
                "status": "healthy" if free_space_gb > 1 else "degraded",
                "free_space_gb": round(free_space_gb, 2),
                "total_space_gb": round(disk_usage.total / (1024**3), 2)
            }
        else:
            health_status["checks"]["storage"] = {
                "status": "unhealthy",
                "error": f"Storage path does not exist: {storage_path}"
            }
            health_status["status"] = "unhealthy"
    except Exception as e:
        health_status["checks"]["storage"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Celery worker health check
    try:
        active_tasks = get_active_tasks()
        worker_count = len(active_tasks) if active_tasks else 0
        health_status["checks"]["workers"] = {
            "status": "healthy" if worker_count > 0 else "degraded",
            "active_workers": worker_count,
            "message": "Workers available" if worker_count > 0 else "No active workers"
        }
    except Exception as e:
        health_status["checks"]["workers"] = {
            "status": "unknown",
            "error": str(e)
        }
    
    return health_status

@router.get("/health/simple")
async def simple_health_check():
    """
    Simple health check for load balancers
    """
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@router.get("/health/database")
async def database_health_check(db: Session = Depends(get_db)):
    """
    Detailed database health check
    """
    
    try:
        # Test basic connection
        start_time = datetime.utcnow()
        result = db.execute(text("SELECT 1")).scalar()
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Test table access
        job_count = db.execute(text("SELECT COUNT(*) FROM visualization_jobs")).scalar()
        
        # Check recent activity
        recent_jobs = db.execute(text("""
            SELECT COUNT(*) FROM visualization_jobs 
            WHERE created_at > NOW() - INTERVAL '1 hour'
        """)).scalar()
        
        return {
            "status": "healthy",
            "response_time_ms": round(response_time, 2),
            "connection_successful": result == 1,
            "total_jobs": job_count,
            "recent_jobs": recent_jobs,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# =====================================
# METRICS ENDPOINTS
# =====================================

@router.get("/metrics")
async def get_system_metrics(db: Session = Depends(get_db)):
    """
    Get system performance metrics
    """
    
    try:
        # Database statistics
        stats = get_system_stats(db)
        
        # System resource usage
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        # Storage usage
        storage_usage = psutil.disk_usage(settings.VISUALIZATION_STORAGE_PATH)
        
        # Active Celery tasks
        try:
            active_tasks = get_active_tasks()
            task_count = len(active_tasks) if active_tasks else 0
        except:
            task_count = 0
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "storage_used_percent": round((storage_usage.used / storage_usage.total) * 100, 2),
                "storage_free_gb": round(storage_usage.free / (1024**3), 2)
            },
            "jobs": stats,
            "workers": {
                "active_tasks": task_count
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")

@router.get("/metrics/prometheus")
async def prometheus_metrics(db: Session = Depends(get_db)):
    """
    Prometheus-formatted metrics endpoint
    """
    
    try:
        stats = get_system_stats(db)
        
        metrics = []
        
        # Job metrics
        metrics.append(f"yieldera_jobs_total {stats['total_jobs']}")
        metrics.append(f"yieldera_jobs_active {stats['active_jobs']}")
        metrics.append(f"yieldera_jobs_completed {stats['completed_jobs']}")
        metrics.append(f"yieldera_jobs_failed {stats['failed_jobs']}")
        metrics.append(f"yieldera_jobs_success_rate {stats['success_rate']}")
        metrics.append(f"yieldera_avg_processing_time_seconds {stats['average_processing_time']}")
        
        # System metrics
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            storage = psutil.disk_usage(settings.VISUALIZATION_STORAGE_PATH)
            
            metrics.append(f"yieldera_cpu_usage_percent {cpu_percent}")
            metrics.append(f"yieldera_memory_usage_percent {memory.percent}")
            metrics.append(f"yieldera_storage_usage_percent {(storage.used / storage.total) * 100}")
            
        except:
            pass
        
        # Worker metrics
        try:
            active_tasks = get_active_tasks()
            task_count = len(active_tasks) if active_tasks else 0
            metrics.append(f"yieldera_active_workers {task_count}")
        except:
            metrics.append(f"yieldera_active_workers 0")
        
        return "\n".join(metrics) + "\n"
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate metrics: {str(e)}")

# =====================================
# SYSTEM STATUS ENDPOINTS
# =====================================

@router.get("/status")
async def get_system_status(db: Session = Depends(get_db)):
    """
    Get overall system status and recent activity
    """
    
    try:
        # System statistics
        stats = get_system_stats(db)
        
        # Recent job activity
        recent_activity = db.execute(text("""
            SELECT 
                status,
                COUNT(*) as count,
                AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_duration
            FROM visualization_jobs 
            WHERE created_at > NOW() - INTERVAL '24 hours'
            GROUP BY status
        """)).fetchall()
        
        activity_summary = {}
        for row in recent_activity:
            activity_summary[row[0]] = {
                "count": row[1],
                "avg_duration_seconds": float(row[2]) if row[2] else None
            }
        
        # Storage information
        storage_stats = psutil.disk_usage(settings.VISUALIZATION_STORAGE_PATH)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT,
            "statistics": stats,
            "recent_activity": activity_summary,
            "storage": {
                "total_gb": round(storage_stats.total / (1024**3), 2),
                "used_gb": round(storage_stats.used / (1024**3), 2),
                "free_gb": round(storage_stats.free / (1024**3), 2),
                "usage_percent": round((storage_stats.used / storage_stats.total) * 100, 2)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system status: {str(e)}")

@router.get("/version")
async def get_version_info():
    """
    Get version and build information
    """
    
    return {
        "service": "Yieldera Visualization System",
        "version": "1.0.0",
        "build_date": "2024-12-16",
        "environment": settings.ENVIRONMENT,
        "python_version": "3.11",
        "dependencies": {
            "fastapi": "0.104.1",
            "celery": "5.3.4",
            "earthengine-api": "0.1.384",
            "postgresql": "supported"
        }
    }

# =====================================
# DIAGNOSTIC ENDPOINTS
# =====================================

@router.get("/diagnostics/earth-engine")
async def diagnose_earth_engine():
    """
    Diagnostic information for Earth Engine connectivity
    """
    
    try:
        import ee
        
        if not settings.gee_config:
            return {
                "status": "not_configured",
                "message": "No Earth Engine credentials configured",
                "has_credentials": False
            }
        
        try:
            # Initialize with service account
            credentials = ee.ServiceAccountCredentials(None, key_data=settings.gee_config)
            ee.Initialize(credentials)
            
            # Test basic functionality
            test_number = ee.Number(42)
            result = test_number.getInfo()
            
            # Test data access
            image = ee.Image('COPERNICUS/S2/20210109T185751_20210109T185931_T10SEG')
            image_info = image.getInfo()
            
            return {
                "status": "healthy",
                "authenticated": True,
                "basic_test_result": result,
                "data_access": "successful",
                "service_account": settings.gee_config.get('client_email', 'unknown')
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "authenticated": False,
                "error": str(e),
                "has_credentials": True
            }
            
    except ImportError:
        return {
            "status": "unavailable",
            "message": "Earth Engine library not installed"
        }

@router.get("/diagnostics/storage")
async def diagnose_storage():
    """
    Diagnostic information for storage system
    """
    
    storage_path = settings.VISUALIZATION_STORAGE_PATH
    
    try:
        # Check if path exists
        path_exists = os.path.exists(storage_path)
        
        if not path_exists:
            return {
                "status": "unhealthy",
                "path": storage_path,
                "exists": False,
                "error": "Storage path does not exist"
            }
        
        # Check permissions
        readable = os.access(storage_path, os.R_OK)
        writable = os.access(storage_path, os.W_OK)
        
        # Get disk usage
        disk_usage = psutil.disk_usage(storage_path)
        
        # Count files
        try:
            file_count = len([f for f in os.listdir(storage_path) if os.path.isfile(os.path.join(storage_path, f))])
        except:
            file_count = "unknown"
        
        return {
            "status": "healthy" if readable and writable else "degraded",
            "path": storage_path,
            "exists": path_exists,
            "permissions": {
                "readable": readable,
                "writable": writable
            },
            "disk_usage": {
                "total_gb": round(disk_usage.total / (1024**3), 2),
                "used_gb": round(disk_usage.used / (1024**3), 2),
                "free_gb": round(disk_usage.free / (1024**3), 2),
                "usage_percent": round((disk_usage.used / disk_usage.total) * 100, 2)
            },
            "file_count": file_count
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "path": storage_path,
            "error": str(e)
        }
