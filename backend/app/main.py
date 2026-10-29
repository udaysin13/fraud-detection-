"""
VaultGuard - FastAPI Main Application Entrypoint
"""

import sys
from pathlib import Path

# Add project root directory and backend directory to sys.path
CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parent.parent
PROJECT_ROOT = BACKEND_DIR.parent

for path_dir in [str(PROJECT_ROOT), str(BACKEND_DIR)]:
    if path_dir not in sys.path:
        sys.path.insert(0, path_dir)

# Support standalone deployment where backend directory is root (e.g., Vercel)
if "backend" not in sys.modules:
    try:
        import backend  # noqa: F401
    except ImportError:
        import types
        backend_pkg = types.ModuleType("backend")
        backend_pkg.__path__ = [str(BACKEND_DIR)]
        sys.modules["backend"] = backend_pkg
        import app
        backend_pkg.app = app
        sys.modules["backend.app"] = app

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.app.database import get_db, verify_database_connection
from backend.app.models.orm import TransactionORM
from backend.app.schemas.pydantic_schemas import HealthResponse
from backend.app.routes.analytics import router as analytics_router
from backend.app.routes.alerts import router as alerts_router
from backend.app.routes.transactions import router as transactions_router
from backend.app.routes.entities import router as entities_router
from backend.app.routes.models_api import router as models_router
from backend.app.routes.websocket import router as websocket_router
from backend.app.routes.bulk_analysis import router as bulk_analysis_router
from backend.app.routes.rules import router as rules_router
from backend.app.routes.cases import router as cases_router
from backend.app.services.data_loader import seed_database_on_first_run
from backend.app.services.ml_service import get_model_health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager: handles startup database seeding and model cache warming.
    """
    print("[Lifespan] VaultGuard API starting up... Checking database state...")
    try:
        verify_database_connection()
        seed_database_on_first_run()
    except Exception as e:
        print(f"[Lifespan WARNING] Database initialization: {e}")
        import os
        if not os.getenv("VERCEL"):
            raise RuntimeError(
                "VaultGuard could not start because database initialization failed. "
                "No data was deleted. Resolve the database connection or apply the "
                "required migration before restarting."
            ) from e
    yield
    print("[Lifespan] VaultGuard API shutting down...")


app = FastAPI(
    title="VaultGuard - Indian Digital Payment Fraud Detection API",
    description="Real-time hybrid ML fraud detection engine for Indian UPI, QR, IMPS, and Wallets with leakage-safe velocity engineering and SHAP explainability.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS configuration: Allow all origins for Vercel full-stack deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(analytics_router)
app.include_router(alerts_router)
app.include_router(transactions_router)
app.include_router(entities_router)
app.include_router(models_router)
app.include_router(websocket_router)
app.include_router(bulk_analysis_router)
app.include_router(rules_router)
app.include_router(cases_router)


@app.get("/", tags=["Health"])
def root():
    """Root endpoint verifying backend status and linking to Swagger UI docs."""
    return {
        "status": "online",
        "service": "VaultGuard Fraud Detection Backend",
        "version": "1.0.0",
        "documentation": "/docs",
    }


@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """System health check endpoint verifying database connectivity and ML artifacts readiness."""
    health_info = get_model_health()
    try:
        txn_count = db.query(TransactionORM).count()
        db_status = "connected"
    except Exception as e:
        txn_count = 0
        db_status = f"error: {str(e)}"

    overall_status = "healthy" if health_info["status"] == "ready" and db_status == "connected" else "degraded"

    return HealthResponse(
        status=overall_status,
        service="VaultGuard Fraud Detection Backend",
        version="1.0.0",
        database=db_status,
        ml_artifacts=health_info["status"],
        model_version="v1.0.0-xgb-iso-hybrid",
        transaction_count=txn_count,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
