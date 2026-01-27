"""
Database Session Management

Handles connection pooling, session lifecycle, and database initialization.
Designed for both Railway (PostgreSQL) and local development (SQLite).
"""

import os
import logging
from contextlib import contextmanager
from pathlib import Path
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
_greenfield_columns_verified = False

def get_engine():
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        _engine = create_db_engine()
    return _engine


def ensure_greenfield_columns_exist() -> bool:
    """
    Public function to ensure greenfield columns exist.

    Call this before any operation that requires the analysis_mode column.
    Returns True if columns were verified/added successfully.

    This is idempotent and safe to call multiple times.
    """
    global _greenfield_columns_verified

    if _greenfield_columns_verified:
        return True

    url = get_database_url()
    if not url.startswith("postgresql://"):
        _greenfield_columns_verified = True
        return True

    engine = get_engine()
    try:
        _ensure_greenfield_columns(engine)
        _greenfield_columns_verified = True
        logger.info("Greenfield columns verified via ensure_greenfield_columns_exist()")
        return True
    except Exception as e:
        logger.error(f"Failed to ensure greenfield columns: {e}")
        return False

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

def _ensure_enum_values(conn, enum_name: str, required_values: list) -> None:
    """
    Ensure a PostgreSQL enum has all required values.
    Adds missing values without breaking existing data.
    """
    try:
        # Get existing values
        result = conn.execute(text(f"""
            SELECT enumlabel FROM pg_enum
            WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = '{enum_name}')
        """))
        existing_values = {row[0] for row in result}

        # Add missing values
        for value in required_values:
            if value not in existing_values:
                logger.info(f"Adding missing value '{value}' to enum '{enum_name}'")
                conn.execute(text(f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS '{value}'"))

    except Exception as e:
        logger.warning(f"Could not update enum {enum_name}: {e}")


def _ensure_greenfield_columns(engine) -> None:
    """
    Ensure greenfield-related columns exist in analysis_runs table.

    This is a direct fix for the missing analysis_mode column error.
    Uses simple ALTER TABLE statements that are safe to run multiple times.

    Raises an exception if critical columns cannot be added.
    """
    logger.info("Starting greenfield column verification...")

    # First, check if the analysis_runs table exists
    with engine.connect() as conn:
        try:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'analysis_runs'
                )
            """))
            table_exists = result.scalar()
            if not table_exists:
                logger.warning("analysis_runs table does not exist yet - skipping column check")
                return
        except Exception as e:
            logger.warning(f"Could not check if analysis_runs table exists: {e}")
            return

    # Create the enum type
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE analysismode AS ENUM ('standard', 'greenfield', 'hybrid');
                EXCEPTION
                    WHEN duplicate_object THEN NULL;
                END $$
            """))
            conn.commit()
            logger.info("Ensured analysismode enum exists")
        except Exception as e:
            logger.warning(f"Could not create analysismode enum (may already exist): {e}")
            try:
                conn.rollback()
            except Exception:
                pass

    # Add each column individually with IF NOT EXISTS
    columns_to_add = [
        ("analysis_mode", "analysismode DEFAULT 'standard'"),
        ("domain_maturity_at_analysis", "VARCHAR(20)"),
        ("domain_rating_at_analysis", "INTEGER"),
        ("organic_keywords_at_analysis", "INTEGER"),
        ("organic_traffic_at_analysis", "INTEGER"),
        ("greenfield_context", "JSONB"),
    ]

    columns_added = []
    columns_failed = []

    for col_name, col_type in columns_to_add:
        with engine.connect() as conn:
            try:
                # Check if column already exists
                result = conn.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns
                        WHERE table_schema = 'public'
                        AND table_name = 'analysis_runs'
                        AND column_name = '{col_name}'
                    )
                """))
                col_exists = result.scalar()

                if col_exists:
                    logger.debug(f"Column {col_name} already exists")
                    columns_added.append(col_name)
                    continue

                # Add the column
                conn.execute(text(f"""
                    ALTER TABLE analysis_runs
                    ADD COLUMN IF NOT EXISTS {col_name} {col_type}
                """))
                conn.commit()
                logger.info(f"Added column {col_name} to analysis_runs")
                columns_added.append(col_name)

            except Exception as e:
                logger.error(f"Failed to add column {col_name}: {e}")
                columns_failed.append(col_name)
                try:
                    conn.rollback()
                except Exception:
                    pass

    # Verify the critical analysis_mode column exists
    with engine.connect() as conn:
        try:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND table_name = 'analysis_runs'
                    AND column_name = 'analysis_mode'
                )
            """))
            analysis_mode_exists = result.scalar()
            if not analysis_mode_exists:
                raise RuntimeError("Critical column 'analysis_mode' could not be added to analysis_runs")
            logger.info(f"Greenfield columns verified: {len(columns_added)} ok, {len(columns_failed)} failed")
        except Exception as e:
            logger.error(f"Failed to verify analysis_mode column: {e}")
            raise


def _run_pending_migrations(engine, conn) -> None:
    """
    Run any pending SQL migrations from the migrations/ directory.

    Migrations are tracked in the schema_migrations table.
    Only migrations that haven't been applied yet are run.
    """
    # Find migrations directory (relative to this file)
    migrations_dir = Path(__file__).parent.parent.parent / "migrations"

    if not migrations_dir.exists():
        logger.warning(f"Migrations directory not found: {migrations_dir}")
        return

    # Ensure schema_migrations table exists
    try:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(50) PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        """))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to create schema_migrations table: {e}")
        return

    # Get list of applied migrations
    try:
        result = conn.execute(text("SELECT version FROM schema_migrations"))
        applied_migrations = {row[0] for row in result}
    except Exception as e:
        logger.error(f"Failed to get applied migrations: {e}")
        applied_migrations = set()

    # Find all migration files and sort them
    migration_files = sorted(migrations_dir.glob("*.sql"))

    for migration_file in migration_files:
        version = migration_file.stem  # e.g., "001_add_greenfield_support"

        if version in applied_migrations:
            logger.debug(f"Migration {version} already applied, skipping")
            continue

        logger.info(f"Applying migration: {version}")

        try:
            # Read the migration SQL
            sql_content = migration_file.read_text()

            # Use raw DBAPI cursor to execute multi-statement SQL
            raw_conn = conn.connection.dbapi_connection
            cursor = raw_conn.cursor()
            cursor.execute(sql_content)
            raw_conn.commit()
            cursor.close()

            logger.info(f"Migration {version} applied successfully")

        except Exception as e:
            try:
                raw_conn.rollback()
            except Exception:
                pass
            logger.error(f"Failed to apply migration {version}: {e}")
            # Continue with other migrations - some may still work
            # The failed migration will be retried on next startup


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

        # Ensure enums have all required values
        logger.info("Ensuring enum values are up to date...")
        try:
            with engine.connect() as conn:
                # ValidatedCompetitorType enum values
                _ensure_enum_values(conn, "validatedcompetitortype", [
                    "direct", "seo", "content", "emerging", "aspirational", "not_competitor"
                ])
                conn.commit()
            logger.info("Enum values verified/updated")
        except Exception as e:
            logger.warning(f"Could not verify enum values: {e}")

    if drop_all:
        logger.warning("Dropping all database tables!")
        Base.metadata.drop_all(bind=engine)

    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")

    # Ensure greenfield columns exist (direct fix for missing analysis_mode)
    if is_postgres:
        logger.info("Ensuring greenfield columns exist...")
        try:
            _ensure_greenfield_columns(engine)
        except Exception as e:
            logger.error(f"Failed to ensure greenfield columns: {e}")

    # Run pending migrations (for schema changes like adding columns)
    if is_postgres:
        logger.info("Running pending migrations...")
        try:
            with engine.connect() as conn:
                _run_pending_migrations(engine, conn)
            logger.info("Migrations completed")
        except Exception as e:
            logger.error(f"Migration error: {e}")


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
