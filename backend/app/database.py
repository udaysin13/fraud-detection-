# VaultGuard - Database Configuration & Session Management

import os
from pathlib import Path
from urllib.parse import quote_plus, urlsplit, urlunsplit
from dotenv import load_dotenv
from sqlalchemy import create_engine, String, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.compiler import compiles

load_dotenv()

def _build_database_url() -> str:
    # Explicit SQLAlchemy URL takes precedence.
    configured_url = (
        os.getenv("DATABASE_URL", "").strip()
        or os.getenv("SQLALCHEMY_DATABASE_URL", "").strip()
    )
    if configured_url:
        # Some providers supply mysql://; SQLAlchemy needs the PyMySQL driver.
        if configured_url.startswith("mysql://"):
            return configured_url.replace("mysql://", "mysql+pymysql://", 1)
        return configured_url

    # Use the individual MySQL variables configured for Aiven/Vercel.
    mysql_host = os.getenv("MYSQL_HOST", "").strip()
    mysql_port = os.getenv("MYSQL_PORT", "3306").strip()
    mysql_user = os.getenv("MYSQL_USER", "").strip()
    mysql_password = os.getenv("MYSQL_PASSWORD", "")
    mysql_database = os.getenv("MYSQL_DATABASE", "").strip()

    if all([mysql_host, mysql_port, mysql_user, mysql_password, mysql_database]):
        return (
            "mysql+pymysql://"
            f"{quote_plus(mysql_user)}:{quote_plus(mysql_password)}"
            f"@{mysql_host}:{mysql_port}/{quote_plus(mysql_database)}"
        )

    # SQLite fallback is for local development only. Vercel must not silently
    # use ephemeral SQLite when MySQL variables are missing.
    if os.getenv("VERCEL"):
        raise RuntimeError(
            "Database is not configured: set DATABASE_URL or all of "
            "MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE."
        )

    db_file = Path(__file__).resolve().parent.parent / "vaultguard.db"
    if db_file.exists():
        return f"sqlite:///{db_file.as_posix()}"
    return "sqlite:///backend/vaultguard.db"


SQLALCHEMY_DATABASE_URL = _build_database_url()


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


@compiles(String, "mysql")
def get_string_spec(element, compiler, **kw):
    if element.length is None:
        element.length = 255
    return compiler.visit_VARCHAR(element, **kw)


# Configure SSL for Aiven when MYSQL_SSL_CA is provided. The variable may contain
# either a filesystem path or the PEM certificate text copied into Vercel.
connect_args = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    ca_value = os.getenv("MYSQL_SSL_CA", "").strip()
    if ca_value:
        if "-----BEGIN CERTIFICATE-----" in ca_value:
            ca_path = "/tmp/vaultguard-aiven-ca.pem" if os.getenv("VERCEL") else str(
                Path.cwd() / ".vaultguard-aiven-ca.pem"
            )
            Path(ca_path).write_text(ca_value, encoding="utf-8")
        else:
            ca_path = ca_value
        connect_args = {
            "connect_timeout": 5,
            "ssl": {"ca": ca_path},
        }
    else:
        connect_args = {"connect_timeout": 5}

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args=connect_args,
        echo=False,
    )
else:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        connect_args=connect_args,
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
