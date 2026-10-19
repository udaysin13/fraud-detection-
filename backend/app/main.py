"""
VaultGuard - FastAPI Main Application Entrypoint
"""

import sys
from pathlib import Path

# Add project root directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.orm import TransactionORM
from backend.app.schemas.pydantic_schemas import HealthResponse
from backend.app.routes.analytics import router as analytics_router
from backend.app.routes.alerts import router as alerts_router
from backend.app.routes.transactions import router as transactions_router
from backend.app.routes.entities import router as entities_router
from backend.app.routes.models_api import router as models_router
from backend.app.routes.websocket import router as websocket_router
from backend.app.services.data_loader import seed_database_on_first_run
from backend.app.services.ml_service import get_model_health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager: handles startup database seeding and model cache warming.
    """
    print("[Lifespan] VaultGuard API starting up... Checking database state...")
    try:
        seed_database_on_first_run()
    except Exception as e:
        print(f"[Lifespan ERROR] Database initialization failed: {e}")
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

# Secure CORS configuration: Explicit trusted origins for Vite development and production
import os

default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
env_origins = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = [o.strip() for o in env_origins.split(",") if o.strip()] if env_origins else default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+)(:\d+)?$",
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
