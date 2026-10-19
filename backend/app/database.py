# VaultGuard - Database Configuration & Session Management

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, String
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.compiler import compiles

# Load environment variables from .env file
load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL must be configured in the environment or a local .env file."
    )

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
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI Dependency for database session management."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()