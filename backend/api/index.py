import sys
from pathlib import Path

# Add the repository root so the database-backed FastAPI application can be imported
# consistently by Vercel's Python runtime.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.main import app
