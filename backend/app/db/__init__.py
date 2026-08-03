import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.schema import Base

def get_engine(database_url: str = None):
    """
    Get SQLAlchemy engine. Uses SQLite for local dev if not specified.
    Supports PostgreSQL for production.
    """
    if database_url is None:
        database_url = os.environ.get("DATABASE_URL", "sqlite:///./local_dev.db")
        
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        
    engine = create_engine(database_url, connect_args=connect_args)
    return engine

def get_session_factory(engine):
    """Get SQLAlchemy session factory."""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db(engine):
    """Initialize database tables for local testing."""
    Base.metadata.create_all(bind=engine)

def drop_db(engine):
    """Drop all tables, mostly for test cleanup."""
    Base.metadata.drop_all(bind=engine)
