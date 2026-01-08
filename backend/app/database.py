"""
Database connection and session management for the Agentic CRM.
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import QueuePool

from app.config import settings


# Create database engine
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before use
    echo=settings.app_debug  # Log SQL in debug mode
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency that provides a database session.
    Automatically closes the session when done.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    Use this when you need a session outside of FastAPI dependencies.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def execute_query(query: str, params: dict = None) -> list:
    """
    Execute a raw SQL query and return results as a list of dicts.
    Used by the NL Query Agent.
    """
    with get_db_context() as db:
        result = db.execute(text(query), params or {})
        columns = result.keys()
        return [dict(zip(columns, row)) for row in result.fetchall()]


def execute_write(query: str, params: dict = None) -> int:
    """
    Execute a write operation (INSERT/UPDATE/DELETE).
    Returns the number of affected rows.
    """
    with get_db_context() as db:
        result = db.execute(text(query), params or {})
        db.commit()
        return result.rowcount


def test_connection() -> bool:
    """Test database connectivity."""
    try:
        with get_db_context() as db:
            db.execute(text("SELECT 1"))
            return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
