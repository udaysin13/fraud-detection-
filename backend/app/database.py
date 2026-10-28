# VaultGuard - Database Configuration & Session Management

import os
from urllib.parse import urlsplit, urlunsplit
from dotenv import load_dotenv
from sqlalchemy import create_engine, String, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.compiler import compiles

# Load environment variables from .env file
load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not SQLALCHEMY_DATABASE_URL:
    if os.getenv("VERCEL"):
        SQLALCHEMY_DATABASE_URL = "sqlite:////tmp/vaultguard.db"
    else:
        from pathlib import Path
        db_file = Path(__file__).resolve().parent.parent / "vaultguard.db"
        if db_file.exists():
            SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_file.as_posix()}"
        else:
            SQLALCHEMY_DATABASE_URL = "sqlite:///backend/vaultguard.db"


class DatabaseConnectionError(RuntimeError):
    """Raised without exposing credentials when a configured database is unavailable."""


def safe_database_url(database_url: str = SQLALCHEMY_DATABASE_URL) -> str:
    """Return a log-safe database URL with any password removed."""
    parsed = urlsplit(database_url)
    if not parsed.scheme or not parsed.netloc:
        return database_url
    host = parsed.hostname or ""
    if parsed.port:
        host = f"{host}:{parsed.port}"
    if parsed.username:
        host = f"{parsed.username}:***@{host}"
    return urlunsplit((parsed.scheme, host, parsed.path, parsed.query, parsed.fragment))


def validate_database_url(database_url: str = SQLALCHEMY_DATABASE_URL) -> None:
    """Validate supported connection schemes before any database operation."""
    if database_url.startswith("sqlite:"):
        return
    if database_url.startswith("mysql+pymysql:"):
        parsed = urlsplit(database_url)
        if not parsed.hostname or not parsed.path or parsed.path == "/":
            raise DatabaseConnectionError(
                "DATABASE_URL must include a MySQL host and database name; "
                f"received {safe_database_url(database_url)}."
            )
        return
    raise DatabaseConnectionError(
        "Unsupported DATABASE_URL scheme. VaultGuard supports sqlite:///... and "
        "mysql+pymysql://...; received "
        f"{safe_database_url(database_url)}."
    )


validate_database_url()

# Automatically give a default length to un-sized String types in MySQL
@compiles(String, "mysql")
def get_string_spec(element, compiler, **kw):
    if element.length is None:
        element.length = 255
    return compiler.visit_VARCHAR(element, **kw)

# Configure engine based on whether it's SQLite or MySQL
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},  # Needed for SQLite
        echo=False,
    )
else:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def verify_database_connection() -> None:
    """Verify connectivity without logging secrets or changing database state."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise DatabaseConnectionError(
            "Unable to connect to the configured database "
            f"({safe_database_url()}). Check that the server is running, the database "
            "exists, and the account has access."
        ) from exc


def get_db():
    """FastAPI Dependency for database session management."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
