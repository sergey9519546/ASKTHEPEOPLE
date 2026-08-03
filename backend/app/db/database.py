"""
Database initialization and session management
"""

import os
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from .models import Base

# Global engine and session factory
_engine = None
_async_session_factory = None


def init_db(database_url: str = None):
    """
    Initialize database engine and session factory.
    
    Args:
        database_url: Database URL (uses environment variable if not provided)
    """
    global _engine, _async_session_factory
    
    if database_url is None:
        database_url = os.environ.get('DATABASE_URL', 'sqlite+aiosqlite:///./askthepeople.db')
    
    # Convert postgres:// to postgresql+asyncpg://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql+asyncpg://', 1)
    elif database_url.startswith('postgresql://') and 'asyncpg' not in database_url:
        database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
    
    # Create async engine
    _engine = create_async_engine(
        database_url,
        poolclass=NullPool if 'sqlite' in database_url else None,
        echo=False,
    )
    
    # Create session factory
    _async_session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    return _engine


async def create_tables():
    """Create all tables (for development/testing only)"""
    global _engine
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables():
    """Drop all tables (for testing only)"""
    global _engine
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@asynccontextmanager
async def get_db_session() -> AsyncSession:
    """
    Get an async database session.
    
    Usage:
        async with get_db_session() as session:
            result = await session.execute(select(ProjectDB))
    """
    global _async_session_factory
    
    if _async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    session = _async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


def get_engine():
    """Get the database engine"""
    global _engine
    return _engine


def get_session_factory():
    """Get the session factory"""
    global _async_session_factory
    return _async_session_factory
