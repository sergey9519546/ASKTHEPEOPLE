import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool
from app.db.schema import (
    Base,
    Project,
    Graph,
    Ontology,
    Simulation,
    Source,
    Report,
)

# Global session factory - initialized in create_app()
_db_session_factory = None


def get_engine(database_url: str = None):
    """
    Get SQLAlchemy engine. Uses SQLite for local dev if not specified.
    Supports PostgreSQL for production.
    """
    if database_url is None:
        database_url = os.environ.get("DATABASE_URL", "sqlite:///./local_dev.db")

    connect_args = {}
    # SQLite needs special handling for thread safety
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    
    # For SQLite, use StaticPool to maintain a single connection
    # This avoids "database is locked" errors in multi-threaded contexts
    poolclass = StaticPool if database_url.startswith("sqlite") else None

    engine = create_engine(
        database_url, 
        connect_args=connect_args,
        poolclass=poolclass,
        echo=False,  # Set to True for SQL debugging
    )
    
    # Enable foreign key support for SQLite
    if database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    
    return engine


def init_session_factory(engine):
    """Initialize the global session factory."""
    global _db_session_factory
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    # scoped_session provides thread-local sessions
    _db_session_factory = scoped_session(SessionLocal)
    return _db_session_factory


def get_db_session():
    """Get a database session from the scoped session factory."""
    if _db_session_factory is None:
        raise RuntimeError(
            "Database session factory not initialized. "
            "Call init_session_factory() during app startup."
        )
    return _db_session_factory()


def close_db_session(exception=None):
    """Remove the current thread's session (call at end of request)."""
    if _db_session_factory is not None:
        _db_session_factory.remove()


def get_session_factory(engine):
    """Get SQLAlchemy session factory (legacy - use init_session_factory instead)."""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(engine):
    """Initialize database tables for local testing."""
    Base.metadata.create_all(bind=engine)


def drop_db(engine):
    """Drop all tables, mostly for test cleanup."""
    Base.metadata.drop_all(bind=engine)
