"""
VaultGuard - Main Application Entrypoint Bridge
Provides direct access to FastAPI app instance for Vercel, uvicorn, and serverless runtimes.
"""

import sys
import types
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

for path in [str(PROJECT_ROOT), str(BACKEND_DIR), str(BACKEND_DIR / "app")]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Ensure 'backend' module is resolvable in standalone/Vercel environments
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

from backend.app.main import app

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
