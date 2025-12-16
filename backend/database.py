"""
Database connection setup for PostgreSQL on Render
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from .config import settings
import logging

# Create the SQLAlchemy engine
# Create the SQLAlchemy engine
engine = create_engine(
    **settings.database_config
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()

def get_db():
    """
    Dependency to get database session
    Use with FastAPI Depends()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_connection():
    """Test database connection"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logging.error(f"Database connection test failed: {e}")
        return False
