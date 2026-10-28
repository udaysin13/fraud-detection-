"""
Vercel Serverless Function Entry Point for FastAPI Backend.
"""

import sys
import types
from pathlib import Path

# Add backend directory and project root to sys.path
API_DIR = Path(__file__).resolve().parent
BACKEND_DIR = API_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

for path in [str(BACKEND_DIR), str(PROJECT_ROOT), str(BACKEND_DIR / "app")]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Alias 'backend' if running in an environment where BACKEND_DIR is root (e.g. Vercel deployment)
if "backend" not in sys.modules:
    try:
        import backend  # noqa: F401
    except ImportError:
        import app
        backend_mod = types.ModuleType("backend")
        backend_mod.__path__ = [str(BACKEND_DIR)]
        backend_mod.app = app
        sys.modules["backend"] = backend_mod
        sys.modules["backend.app"] = app

# Import the FastAPI app instance from main.py
try:
    from main import app
except ImportError:
    try:
        from app.main import app
    except ImportError:
        from backend.app.main import app

__all__ = ["app"]
