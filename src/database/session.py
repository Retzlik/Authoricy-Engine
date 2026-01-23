"""
Database Session Management

Handles connection pooling, session lifecycle, and database initialization.
Designed for both Railway (PostgreSQL) and local development (SQLite).
"""

import os
import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from .models import Base

logger = logging.getLogger(__name__)

# =============================================================================
# DATABASE URL CONFIGURATION
# =============================================================================

def get_database_url() -> str:
    """
    Get database URL from environment.

    Priority:
    1. DATABASE_URL (Railway sets this automatically)
    2. POSTGRES_URL (alternative)
    3. SQLite fallback for local development
    """
    # Railway provides DATABASE_URL automatically
    url = os.getenv("DATABASE_URL")

    if url:
        # Railway PostgreSQL URLs use postgres:// but SQLAlchemy needs postgresql://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        logger.info("Using PostgreSQL database from DATABASE_URL")
        return url

    # Alternative environment variable
    url = os.getenv("POSTGRES_URL")
    if url:
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        logger.info("Using PostgreSQL database from POSTGRES_URL")
        return url

    # SQLite fallback for local development
    sqlite_path = os.getenv("SQLITE_PATH", "authoricy_dev.db")
    logger.warning(f"No DATABASE_URL found, using SQLite: {sqlite_path}")
    return f"sqlite:///{sqlite_path}"


# =============================================================================
# ENGINE CONFIGURATION
# =============================================================================

def create_db_engine():
    """
    Create database engine with appropriate settings.

    PostgreSQL: Connection pooling, prepared statements
    SQLite: Simpler settings, foreign key support
    """
    url = get_database_url()
    is_postgres = url.startswith("postgresql://")

    if is_postgres:
        engine = create_engine(
            url,
            poolclass=QueuePool,
            pool_size=5,                # Base connections
            max_overflow=10,            # Additional connections under load
            pool_timeout=30,            # Wait for connection
            pool_recycle=1800,          # Recycle connections after 30 min
            pool_pre_ping=True,         # Verify connections before use
            echo=os.getenv("SQL_DEBUG", "false").lower() == "true",
        )
        logger.info("Created PostgreSQL engine with connection pooling")
    else:
        # SQLite configuration
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},  # Allow multi-thread access
            echo=os.getenv("SQL_DEBUG", "false").lower() == "true",
        )

        # Enable foreign keys for SQLite
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        logger.info("Created SQLite engine")

    return engine


# Global engine (lazy initialization)
_engine = None

def get_engine():
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        _engine = create_db_engine()
    return _engine

# Alias for imports
engine = property(lambda self: get_engine())


# =============================================================================
# SESSION MANAGEMENT
# =============================================================================

# Session factory (lazy initialization)
_SessionLocal = None

def get_session_factory():
    """Get or create session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,  # Don't expire objects after commit
        )
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI-style dependency for database sessions.

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    Usage:
        with get_db_context() as db:
            db.query(Item).all()
    """
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_session() -> Session:
    """
    Get a raw session (caller responsible for lifecycle).

    Usage:
        db = get_db_session()
        try:
            # do work
            db.commit()
        finally:
            db.close()
    """
    SessionLocal = get_session_factory()
    return SessionLocal()


# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================

def init_db(drop_all: bool = False) -> None:
    """
    Initialize database - create extensions and all tables.

    Args:
        drop_all: If True, drop all tables first (USE WITH CAUTION!)
    """
    engine = get_engine()
    url = get_database_url()
    is_postgres = url.startswith("postgresql://")

    # Create PostgreSQL extensions first
    if is_postgres:
        logger.info("Creating PostgreSQL extensions...")
        try:
            with engine.connect() as conn:
                # uuid-ossp: Required for UUID generation
                conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
                # pg_trgm: For fuzzy text search on keywords
                conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pg_trgm"'))
                # btree_gin: For GIN indexes on regular columns
                conn.execute(text('CREATE EXTENSION IF NOT EXISTS "btree_gin"'))
                conn.commit()
            logger.info("PostgreSQL extensions created/verified")
        except Exception as e:
            logger.warning(f"Could not create extensions (might need superuser): {e}")

    if drop_all:
        logger.warning("Dropping all database tables!")
        Base.metadata.drop_all(bind=engine)

    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")


def get_table_count() -> int:
    """Get count of tables in database."""
    engine = get_engine()
    url = get_database_url()
    is_postgres = url.startswith("postgresql://")

    try:
        with engine.connect() as conn:
            if is_postgres:
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_schema = 'public'
                """))
            else:
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM sqlite_master WHERE type='table'
                """))
            return result.scalar() or 0
    except Exception as e:
        logger.error(f"Error counting tables: {e}")
        return -1


def get_db_info() -> dict:
    """
    Get comprehensive database information.

    Returns diagnostic info for debugging Railway deployment.
    """
    url = get_database_url()
    is_postgres = url.startswith("postgresql://")

    # Mask password in URL for logging
    safe_url = url
    if "@" in url:
        parts = url.split("@")
        safe_url = parts[0].rsplit(":", 1)[0] + ":***@" + parts[1]

    info = {
        "database_type": "postgresql" if is_postgres else "sqlite",
        "connection_url": safe_url,
        "connected": False,
        "table_count": 0,
        "extensions": [],
        "tables": [],
    }

    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            info["connected"] = True

            if is_postgres:
                # Get extensions
                result = conn.execute(text("""
                    SELECT extname FROM pg_extension WHERE extname != 'plpgsql'
                """))
                info["extensions"] = [row[0] for row in result]

                # Get tables
                result = conn.execute(text("""
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public' ORDER BY table_name
                """))
                info["tables"] = [row[0] for row in result]
            else:
                result = conn.execute(text("""
                    SELECT name FROM sqlite_master WHERE type='table' ORDER BY name
                """))
                info["tables"] = [row[0] for row in result]

            info["table_count"] = len(info["tables"])

    except Exception as e:
        info["error"] = str(e)

    return info


def check_db_connection() -> bool:
    """
    Check if database connection is working.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection verified")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


def get_db_stats() -> dict:
    """
    Get database connection statistics.

    Returns:
        Dict with pool statistics (PostgreSQL only)
    """
    engine = get_engine()
    pool = engine.pool

    return {
        "pool_size": pool.size(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "checked_in": pool.checkedin(),
    }


# =============================================================================
# TRANSACTION HELPERS
# =============================================================================

@contextmanager
def transaction(db: Session):
    """
    Explicit transaction context manager.

    Usage:
        with transaction(db):
            db.add(item1)
            db.add(item2)
            # Commits at end, rollback on exception
    """
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise


def bulk_insert(db: Session, objects: list, batch_size: int = 1000):
    """
    Bulk insert objects with batching for large datasets.

    Args:
        db: Database session
        objects: List of SQLAlchemy model instances
        batch_size: Number of objects per batch
    """
    for i in range(0, len(objects), batch_size):
        batch = objects[i:i + batch_size]
        db.bulk_save_objects(batch)
        db.flush()
    db.commit()


# =============================================================================
# CONVENIENCE EXPORTS
# =============================================================================

# For backwards compatibility and convenience
engine = get_engine()
