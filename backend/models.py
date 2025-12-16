"""
Database models for Yieldera Visualization System
PostgreSQL setup for Render.com deployment
"""

from sqlalchemy import Column, String, DateTime, JSON, Integer, Text, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from datetime import datetime, timezone
import uuid
from .config import settings

# Create SQLAlchemy components
Base = declarative_base()

# Create engine with Render PostgreSQL configuration
# Create engine with Render PostgreSQL configuration
engine = create_engine(
    **settings.database_config
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# =====================================
# DATABASE MODELS
# =====================================

class VisualizationJob(Base):
    """Main model for visualization jobs"""
    __tablename__ = 'visualization_jobs'
    
    # Primary identification
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    
    # Analysis parameters
    region_name = Column(String, nullable=False)
    geometry = Column(JSON, nullable=False)
    start_date = Column(String, nullable=False)  # YYYY-MM-DD format
    end_date = Column(String, nullable=False)    # YYYY-MM-DD format

    analysis_type = Column(String, default='anomaly')
    
    # Region Information
    region_id = Column(String, nullable=True)
    region_type = Column(String, nullable=True)
    
    # Baseline Configuration
    baseline_type = Column(String, default='same-period')  # same-period, custom
    baseline_config = Column(JSON, nullable=True)  # {start: '...', end: '...'}
    
    # Job tracking
    status = Column(String, default='pending', index=True)  # pending, running, completed, failed, cancelled
    progress = Column(Integer, default=0)
    message = Column(Text, default='')
    celery_task_id = Column(String, index=True)
    
    # Results and statistics
    statistics = Column(JSON)
    
    # File paths
    map_image_path = Column(String)
    export_paths = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Error handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Configuration
    visualization_config = Column(JSON)
    
    # Performance metrics
    processing_time_seconds = Column(Float)
    
    def __repr__(self):
        return f"<VisualizationJob(id={self.id}, region={self.region_name}, status={self.status})>"
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'region_name': self.region_name,
            'geometry': self.geometry,
            'start_date': self.start_date,
            'end_date': self.end_date,

            'analysis_type': self.analysis_type,
            'region_id': self.region_id,
            'region_type': self.region_type,
            'baseline_type': self.baseline_type,
            'baseline_config': self.baseline_config,
            'status': self.status,
            'progress': self.progress,
            'message': self.message,
            'statistics': self.statistics,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'processing_time_seconds': self.processing_time_seconds,
            'export_paths': self.export_paths
        }

class AnalysisPreset(Base):
    """Predefined analysis regions and parameters"""
    __tablename__ = 'analysis_presets'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True)
    description = Column(Text)
    geometry = Column(JSON, nullable=False)
    default_start_date = Column(String)
    default_end_date = Column(String)
    default_analysis_type = Column(String, default='anomaly')
    
    # Metadata
    created_by = Column(String)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    is_public = Column(Boolean, default=True)
    
    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used = Column(DateTime(timezone=True))
    
    def __repr__(self):
        return f"<AnalysisPreset(id={self.id}, name={self.name})>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'geometry': self.geometry,
            'default_start_date': self.default_start_date,
            'default_end_date': self.default_end_date,
            'default_analysis_type': self.default_analysis_type,
            'usage_count': self.usage_count
        }

class JobMetrics(Base):
    """Performance metrics for monitoring"""
    __tablename__ = 'job_metrics'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, nullable=False, index=True)
    
    # Performance metrics
    queue_time_seconds = Column(Float)
    gee_processing_time_seconds = Column(Float)
    cartography_time_seconds = Column(Float)
    total_processing_time_seconds = Column(Float)
    
    # Resource usage
    memory_usage_mb = Column(Float)
    cpu_usage_percent = Column(Float)
    
    # Data size metrics
    input_geometry_area_km2 = Column(Float)
    output_file_size_mb = Column(Float)
    
    # Timestamp
    recorded_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    def __repr__(self):
        return f"<JobMetrics(job_id={self.job_id}, total_time={self.total_processing_time_seconds}s)>"

class SystemHealth(Base):
    """System health monitoring"""
    __tablename__ = 'system_health'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Service status
    api_status = Column(String, default='unknown')  # healthy, degraded, unhealthy
    database_status = Column(String, default='unknown')
    redis_status = Column(String, default='unknown')
    gee_status = Column(String, default='unknown')
    
    # Performance indicators
    active_jobs = Column(Integer, default=0)
    queued_jobs = Column(Integer, default=0)
    failed_jobs_last_hour = Column(Integer, default=0)
    
    # System resources
    storage_used_mb = Column(Float)
    storage_available_mb = Column(Float)
    
    # Timestamp
    recorded_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<SystemHealth(api={self.api_status}, db={self.database_status})>"

# =====================================
# DATABASE DEPENDENCY
# =====================================

def get_db():
    """Database dependency for FastAPI endpoints"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =====================================
# DATABASE UTILITIES
# =====================================

def create_all_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

def drop_all_tables():
    """Drop all database tables (development only)"""
    if settings.ENVIRONMENT == "development":
        Base.metadata.drop_all(bind=engine)
    else:
        raise RuntimeError("Cannot drop tables in production environment")

def get_job_by_id(db, job_id: str) -> VisualizationJob:
    """Get job by ID with error handling"""
    return db.query(VisualizationJob).filter(VisualizationJob.id == job_id).first()

def get_jobs_by_user(db, user_id: str, limit: int = 50) -> list:
    """Get jobs for a specific user"""
    return db.query(VisualizationJob)\
             .filter(VisualizationJob.user_id == user_id)\
             .order_by(VisualizationJob.created_at.desc())\
             .limit(limit)\
             .all()

def get_active_jobs(db) -> list:
    """Get currently running jobs"""
    return db.query(VisualizationJob)\
             .filter(VisualizationJob.status.in_(['pending', 'running']))\
             .all()

def cleanup_old_jobs(db, days: int = 7):
    """Clean up old completed jobs"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    old_jobs = db.query(VisualizationJob)\
                 .filter(VisualizationJob.completed_at < cutoff_date)\
                 .filter(VisualizationJob.status.in_(['completed', 'failed', 'cancelled']))\
                 .all()
    
    for job in old_jobs:
        # Delete associated files
        if job.map_image_path and os.path.exists(job.map_image_path):
            os.remove(job.map_image_path)
        
        # Delete export files
        if job.export_paths:
            for path in job.export_paths.values():
                if os.path.exists(path):
                    os.remove(path)
        
        # Delete database record
        db.delete(job)
    
    db.commit()
    return len(old_jobs)

def get_system_stats(db) -> dict:
    """Get system statistics for monitoring"""
    from sqlalchemy import func
    
    total_jobs = db.query(func.count(VisualizationJob.id)).scalar()
    active_jobs = db.query(func.count(VisualizationJob.id))\
                    .filter(VisualizationJob.status.in_(['pending', 'running']))\
                    .scalar()
    completed_jobs = db.query(func.count(VisualizationJob.id))\
                       .filter(VisualizationJob.status == 'completed')\
                       .scalar()
    failed_jobs = db.query(func.count(VisualizationJob.id))\
                    .filter(VisualizationJob.status == 'failed')\
                    .scalar()
    
    # Average processing time for completed jobs
    avg_processing_time = db.query(func.avg(VisualizationJob.processing_time_seconds))\
                           .filter(VisualizationJob.status == 'completed')\
                           .scalar()
    
    return {
        'total_jobs': total_jobs or 0,
        'active_jobs': active_jobs or 0,
        'completed_jobs': completed_jobs or 0,
        'failed_jobs': failed_jobs or 0,
        'success_rate': (completed_jobs / max(total_jobs, 1)) * 100 if total_jobs else 0,
        'average_processing_time': float(avg_processing_time) if avg_processing_time else 0
    }

# =====================================
# INITIALIZATION
# =====================================

def init_default_presets(db):
    """Initialize default analysis presets"""
    
    presets = [
        {
            'name': 'Zimbabwe',
            'description': 'Complete Zimbabwe territory',
            'geometry': {
                'type': 'Polygon',
                'coordinates': [[
                    [25.2, -22.4], [33.1, -22.4], 
                    [33.1, -15.6], [25.2, -15.6], [25.2, -22.4]
                ]]
            },
            'default_start_date': '2025-10-01',
            'default_end_date': '2025-12-15'
        },
        {
            'name': 'Mashonaland Central',
            'description': 'Mashonaland Central Province, Zimbabwe',
            'geometry': {
                'type': 'Polygon',
                'coordinates': [[
                    [30.0, -17.5], [33.0, -17.5],
                    [33.0, -15.5], [30.0, -15.5], [30.0, -17.5]
                ]]
            },
            'default_start_date': '2025-11-01',
            'default_end_date': '2025-12-31'
        },
        {
            'name': 'Matabeleland North',
            'description': 'Matabeleland North Province, Zimbabwe',
            'geometry': {
                'type': 'Polygon',
                'coordinates': [[
                    [25.5, -20.0], [29.0, -20.0],
                    [29.0, -16.5], [25.5, -16.5], [25.5, -20.0]
                ]]
            },
            'default_start_date': '2025-11-01',
            'default_end_date': '2025-12-31'
        }
    ]
    
    for preset_data in presets:
        existing = db.query(AnalysisPreset)\
                    .filter(AnalysisPreset.name == preset_data['name'])\
                    .first()
        
        if not existing:
            preset = AnalysisPreset(**preset_data)
            db.add(preset)
    
    db.commit()

if __name__ == "__main__":
    # Create tables
    create_all_tables()
    print("✅ Database tables created successfully")
    
    # Initialize default presets
    with SessionLocal() as db:
        init_default_presets(db)
        print("✅ Default presets initialized")
        
        # Show system stats
        stats = get_system_stats(db)
        print(f"📊 System stats: {stats}")
