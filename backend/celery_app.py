"""
Celery configuration for background job processing
Optimized for Render.com deployment
"""

from celery import Celery
from celery.signals import worker_ready, task_prerun, task_postrun
import logging
import os
from datetime import datetime, timedelta
from .config import settings

# Create Celery instance
# Configure broker and backend with explicit fallbacks
broker_url = settings.CELERY_BROKER_URL
result_backend = settings.CELERY_RESULT_BACKEND

# Hard fallback if configuration is missing or looks malformed (e.g. no hostname)
if not broker_url or broker_url.strip() in ["", "redis://", "rediss://"]:
    logging.warning(f"⚠️ CELERY_BROKER_URL ({broker_url}) appears invalid! Forcing 'memory://' fallback.")
    broker_url = "memory://"
    result_backend = "rpc://"

logging.info(f"🔧 Celery final instantiation - Broker: {broker_url.split('@')[-1] if '@' in broker_url else broker_url}")

# Create Celery instance
celery_app = Celery(
    'yieldera_visualization',
    broker=broker_url,
    backend=result_backend,
    include=['backend.tasks']
)

# Configure Celery
app_config = settings.celery_config.copy()
# Ensure these are locked in
app_config["broker_url"] = broker_url
app_config["result_backend"] = result_backend

celery_app.conf.update(**app_config)

# =====================================
# CELERY TASKS
# =====================================

@celery_app.task(bind=True, max_retries=3)
def process_visualization_job(self, job_id: str, job_data: dict):
    """
    Main task for processing visualization jobs
    """
    from .models import VisualizationJob
    from .database import SessionLocal
    from .visualization.processor import VisualizationProcessor
    import traceback
    
    # Update job status to running
    with SessionLocal() as db:
        job = db.query(VisualizationJob).filter(VisualizationJob.id == job_id).first()
        if job:
            job.status = 'running'
            job.started_at = datetime.utcnow()
            job.celery_task_id = self.request.id
            job.message = 'Initializing processing...'
            job.progress = 0
            db.commit()
    
    # Define callback for processor
    def update_progress_callback(progress: int, message: str):
        """Update progress both in Celery and database"""
        # Update Celery state
        self.update_state(
            state='PROGRESS',
            meta={'progress': progress, 'message': message}
        )
        
        # Update database
        try:
            with SessionLocal() as db:
                job = db.query(VisualizationJob).filter(VisualizationJob.id == job_id).first()
                if job:
                    job.progress = progress
                    job.message = message
                    db.commit()
        except Exception as e:
            logging.error(f"Failed to update progress for job {job_id}: {e}")

    try:
        # Initialize processor
        processor = VisualizationProcessor()
        
        # Update progress
        update_progress_callback(5, 'Connecting to Google Earth Engine...')
        
        # Process the visualization
        start_time = datetime.utcnow()
        result = processor.process_job(job_id, job_data, progress_callback=update_progress_callback)
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        if not result['success']:
            raise Exception(result['error'])
        
        # Update final status
        with SessionLocal() as db:
            job = db.query(VisualizationJob).filter(VisualizationJob.id == job_id).first()
            if job:
                job.status = 'completed'
                job.completed_at = datetime.utcnow()
                job.progress = 100
                job.message = 'Processing completed successfully'
                # Combine statistics with AI commentary for storage
                stats = result.get('statistics', {})
                stats['ai_commentary'] = result.get('ai_commentary', '')
                job.statistics = stats
                job.map_image_path = result.get('map_image_path')
                job.export_paths = result.get('export_paths', {})
                job.processing_time_seconds = processing_time
                db.commit()
        
        return {
            'success': True,
            'job_id': job_id,
            'processing_time': processing_time,
            'result': result
        }
        
    except Exception as exc:
        # Log the full error for debugging
        error_details = traceback.format_exc()
        logging.error(f"Job {job_id} failed: {error_details}")
        
        # Update database with error
        with SessionLocal() as db:
            job = db.query(VisualizationJob).filter(VisualizationJob.id == job_id).first()
            if job:
                job.status = 'failed'
                job.completed_at = datetime.utcnow()
                job.error_message = str(exc)
                job.message = f'Processing failed: {str(exc)}'
                job.retry_count = getattr(job, 'retry_count', 0) + 1
                db.commit()
        
        # Retry if within retry limit
        if self.request.retries < self.max_retries:
            # Exponential backoff: 60s, 180s, 540s
            retry_delay = 60 * (3 ** self.request.retries)
            raise self.retry(countdown=retry_delay, exc=exc)
        
        # Final failure
        self.update_state(
            state='FAILURE',
            meta={
                'error': str(exc),
                'job_id': job_id,
                'retry_count': self.request.retries
            }
        )
        
        raise exc

@celery_app.task
def cleanup_old_jobs():
    """
    Periodic task to clean up old job files and records
    """
    from .models import cleanup_old_jobs
    from .database import SessionLocal
    
    try:
        with SessionLocal() as db:
            cleaned_count = cleanup_old_jobs(db, days=settings.CLEANUP_DAYS)
            logging.info(f"Cleaned up {cleaned_count} old jobs")
            return f"Cleaned {cleaned_count} jobs"
    except Exception as e:
        logging.error(f"Cleanup task failed: {e}")
        raise

@celery_app.task
def health_check():
    """
    Health check task for monitoring
    """
    from .database import test_connection
    import redis
    
    try:
        # Test database
        db_healthy = test_connection()
        
        # Test Redis
        if settings.REDIS_URL:
            r = redis.from_url(settings.REDIS_URL)
            redis_healthy = r.ping()
        else:
            redis_healthy = False  # Not configured
        
        # Test Earth Engine
        try:
            import ee
            if settings.gee_config:
                credentials = ee.ServiceAccountCredentials(None, key_data=settings.gee_config)
                ee.Initialize(credentials)
                gee_healthy = True
            else:
                gee_healthy = False
        except Exception:
            gee_healthy = False
        
        return {
            'status': 'healthy' if all([db_healthy, redis_healthy]) else 'degraded',
            'database': db_healthy,
            'redis': redis_healthy,
            'earth_engine': gee_healthy,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Health check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }

@celery_app.task
def update_system_metrics():
    """
    Update system performance metrics
    """
    from .models import SystemHealth, get_system_stats
    from .database import SessionLocal
    import psutil
    
    try:
        with SessionLocal() as db:
            # Get job statistics
            stats = get_system_stats(db)
            
            # Get system resources
            storage_stats = psutil.disk_usage(settings.VISUALIZATION_STORAGE_PATH)
            
            # Create health record
            health = SystemHealth(
                api_status='healthy',
                database_status='healthy' if test_connection() else 'unhealthy',
                redis_status='healthy',  # If we got here, Redis is working
                active_jobs=stats['active_jobs'],
                queued_jobs=0,  # Would need to query Celery for this
                storage_used_mb=storage_stats.used / (1024 * 1024),
                storage_available_mb=storage_stats.free / (1024 * 1024)
            )
            
            db.add(health)
            db.commit()
            
            return stats
            
    except Exception as e:
        logging.error(f"Metrics update failed: {e}")
        raise

# =====================================
# PERIODIC TASKS
# =====================================

from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    # Clean up old jobs every day at 2 AM
    'cleanup-old-jobs': {
        'task': 'backend.celery_app.cleanup_old_jobs',
        'schedule': crontab(hour=2, minute=0),
    },
    # Update system metrics every 5 minutes
    'update-metrics': {
        'task': 'backend.celery_app.update_system_metrics',
        'schedule': 300.0,  # 5 minutes
    },
    # Health check every minute
    'health-check': {
        'task': 'backend.celery_app.health_check',
        'schedule': 60.0,  # 1 minute
    },
}

# =====================================
# SIGNAL HANDLERS
# =====================================

@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Handler when worker is ready"""
    logging.info("🚀 Celery worker ready for processing visualization jobs")

@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Handler before task execution"""
    logging.info(f"📋 Starting task: {task.name} (ID: {task_id})")

@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, 
                        retval=None, state=None, **kwds):
    """Handler after task execution"""
    logging.info(f"✅ Completed task: {task.name} (ID: {task_id}, State: {state})")

# =====================================
# UTILITY FUNCTIONS
# =====================================

def get_task_status(task_id: str) -> dict:
    """Get status of a specific task"""
    from celery.result import AsyncResult
    
    result = AsyncResult(task_id, app=celery_app)
    
    return {
        'task_id': task_id,
        'status': result.status,
        'result': result.result,
        'traceback': result.traceback,
        'info': result.info
    }

def cancel_task(task_id: str) -> bool:
    """Cancel a running task"""
    try:
        celery_app.control.revoke(task_id, terminate=True)
        return True
    except Exception as e:
        logging.error(f"Failed to cancel task {task_id}: {e}")
        return False

def get_active_tasks() -> list:
    """Get list of currently active tasks"""
    try:
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active()
        return active_tasks or {}
    except Exception as e:
        logging.error(f"Failed to get active tasks: {e}")
        return {}

if __name__ == "__main__":
    # Start Celery worker
    celery_app.start()
