"""
Configuration for Yieldera Visualization System
Optimized for Render.com deployment with PostgreSQL
"""

import os
from typing import Optional
import json
import logging

class Settings:
    """Application settings with Render.com optimization"""
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Database - Render PostgreSQL
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # Redis - Render Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    
    # Google Earth Engine Authentication
    GOOGLE_APPLICATION_CREDENTIALS_JSON: Optional[str] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    
    # Storage Configuration
    VISUALIZATION_STORAGE_PATH: str = os.getenv("VISUALIZATION_STORAGE_PATH", "/tmp/visualizations")
    
    # AWS S3 (optional)
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_S3_BUCKET: Optional[str] = os.getenv("AWS_S3_BUCKET")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    
    # Celery Configuration
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", ""))
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", ""))
    
    # Performance Settings
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "4"))
    WORKER_CONCURRENCY: int = int(os.getenv("WORKER_CONCURRENCY", "1"))
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Yieldera Visualization System"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    
    # File Cleanup
    CLEANUP_DAYS: int = int(os.getenv("CLEANUP_DAYS", "7"))
    
    # CORS
    ALLOWED_HOSTS: list = os.getenv("ALLOWED_HOSTS", "*").split(",")
    
    # Monitoring
    SENTRY_DSN: Optional[str] = os.getenv("SENTRY_DSN")
    
    def __init__(self):
        """Initialize settings and validate configuration"""
        self.validate_configuration()
        self.setup_logging()
        
    def validate_configuration(self):
        """Validate required configuration"""
        
        if not self.DATABASE_URL:
            raise ValueError("DATABASE_URL is required. Please set up PostgreSQL in Render.")
            
        if self.ENVIRONMENT == "production" and not self.REDIS_URL:
            logging.warning("REDIS_URL not set. Background tasks will not function.")
            
        if self.ENVIRONMENT == "production" and not self.GOOGLE_APPLICATION_CREDENTIALS_JSON:
            logging.warning("GOOGLE_APPLICATION_CREDENTIALS_JSON not set. GEE functionality will be limited.")
            
        # Validate GEE credentials format
        if self.GOOGLE_APPLICATION_CREDENTIALS_JSON:
            try:
                json.loads(self.GOOGLE_APPLICATION_CREDENTIALS_JSON)
            except json.JSONDecodeError:
                raise ValueError("GOOGLE_APPLICATION_CREDENTIALS_JSON must be valid JSON")
                
    def setup_logging(self):
        """Configure logging based on environment"""
        
        log_level = getattr(logging, self.LOG_LEVEL.upper(), logging.INFO)
        
        if self.ENVIRONMENT == "production":
            # Production logging - structured JSON
            logging.basicConfig(
                level=log_level,
                format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(name)s", "message": "%(message)s"}',
                handlers=[logging.StreamHandler()]
            )
        else:
            # Development logging - readable format
            logging.basicConfig(
                level=log_level,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[logging.StreamHandler()]
            )
    
    @property
    def database_config(self) -> dict:
        """Get database configuration for SQLAlchemy"""
        return {
            "url": self.DATABASE_URL,
            "pool_pre_ping": True,
            "pool_recycle": 3600,  # Recycle connections after 1 hour
            "pool_size": 5,
            "max_overflow": 10,
            "echo": self.ENVIRONMENT == "development"
        }
    
    @property
    def celery_config(self) -> dict:
        """Get Celery configuration"""
        return {
            "broker_url": self.CELERY_BROKER_URL,
            "result_backend": self.CELERY_RESULT_BACKEND,
            "task_serializer": "json",
            "accept_content": ["json"],
            "result_serializer": "json",
            "timezone": "UTC",
            "enable_utc": True,
            "task_track_started": True,
            "task_acks_late": True,
            "worker_prefetch_multiplier": 1,
            "worker_max_tasks_per_child": 1000,
            "worker_concurrency": self.WORKER_CONCURRENCY,
            "result_expires": 3600,  # Results expire after 1 hour
            "task_compression": "gzip",
            "result_compression": "gzip",
        }
    
    @property
    def gee_config(self) -> Optional[dict]:
        """Get Google Earth Engine configuration"""
        
        if not self.GOOGLE_APPLICATION_CREDENTIALS_JSON:
            return None
            
        try:
            return json.loads(self.GOOGLE_APPLICATION_CREDENTIALS_JSON)
        except json.JSONDecodeError:
            logging.error("Invalid GEE credentials JSON format")
            return None
    
    @property
    def aws_config(self) -> Optional[dict]:
        """Get AWS S3 configuration if available"""
        
        if not all([self.AWS_ACCESS_KEY_ID, self.AWS_SECRET_ACCESS_KEY, self.AWS_S3_BUCKET]):
            return None
            
        return {
            "aws_access_key_id": self.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": self.AWS_SECRET_ACCESS_KEY,
            "bucket": self.AWS_S3_BUCKET,
            "region": self.AWS_REGION
        }

# Create global settings instance
settings = Settings()

# Export commonly used values
DATABASE_URL = settings.DATABASE_URL
REDIS_URL = settings.REDIS_URL
ENVIRONMENT = settings.ENVIRONMENT
