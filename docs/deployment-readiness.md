# VaultGuard Deployment Readiness Assessment & Roadmap

This document provides a technical evaluation of VaultGuard's deployment readiness, identifies current architectural blockers, outlines suitable cloud hosting patterns, specifies necessary environment variables, and provides a staged deployment plan.

---

## 1. Executive Summary & Readiness Classification

- **Academic Demonstration / Portfolio Hosting**: **READY (with minor configuration)**.
  The frontend builds to a clean, optimized static bundle (`npm run build`). The backend runs smoothly under ASGI (Uvicorn). Local and containerized hosting for demonstration purposes is fully functional.
- **Enterprise Commercial Banking Deployment**: **NOT READY (Significant Blockers)**.
  The current architecture lacks multi-tenant JWT authentication, role-based authorization, connection-pooled relational storage (PostgreSQL), and distributed rate limiting.

---

## 2. Current Deployment Blockers & Architectural Gaps

| Blocker / Limitation | Current State | Required for Production Deployment |
| :--- | :--- | :--- |
| **Authentication & RBAC** | Token header for admin retrain; no user logins | JWT / OAuth2 analyst authentication with role-based access control (Analyst, Admin, Auditor) |
| **Database Concurrency** | SQLite (`backend/vaultguard.db`) with file-level locking | PostgreSQL or MySQL with connection pooling (PgBouncer) |
| **API Rate Limiting** | No request throttling | Redis-backed token-bucket rate limiting (e.g. `slowapi` or Cloudflare WAF) |
| **WebSocket Encryption** | Plain `ws://` in local development | Secure WebSocket (`wss://`) terminated behind reverse proxy SSL/TLS |
| **Secret Management** | Local `.env` files | Centralized secret manager (AWS Secrets Manager, HashiCorp Vault) |
| **Model Artifact Storage** | Local filesystem (`ml/saved_models/*.joblib`) | Object storage (AWS S3 / GCS) or model registry (MLflow) with versioned hashes |

---

## 3. Suitable Cloud Hosting Architecture Options

### Option A: Decoupled Cloud Hosting (Recommended for Portfolio / Demo)
- **Frontend**: Static SPA hosted on **Vercel** or **Cloudflare Pages**.
  - Built via `npm run build`.
  - Connects to backend via HTTPS and WSS.
- **Backend & ML Engine**: Containerized FastAPI service on **Render**, **Railway**, or **Fly.io**.
  - Docker container running `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`.
  - Persistent volume attached for `vaultguard.db` and model artifacts.
  - Automatic HTTPS / WSS termination.

### Option B: Cloud-Native Microservices (Enterprise Target)
- **Frontend**: Amazon S3 + CloudFront CDN (Global Edge Caching).
- **API Gateway**: AWS ALB / API Gateway with Cloudflare WAF.
- **Backend Services**: Amazon ECS / EKS (Fargate) with auto-scaling container tasks.
- **Database**: Amazon Aurora PostgreSQL (Multi-AZ with read replicas).
- **Telemetry & Cache**: Amazon ElastiCache (Redis) for session management and rate limiting.

---

## 4. Environment Variables Specification

### Backend Environment Variables
| Variable Name | Required | Default (Local) | Production Example | Description |
| :--- | :--- | :--- | :--- | :--- |
| `ALLOWED_ORIGINS` | Yes | `http://localhost:3000,...` | `https://vaultguard.yourdomain.com` | Comma-separated list of trusted CORS origins |
| `VAULTGUARD_ADMIN_TOKEN`| Yes | None (dev warning) | `c9f8a4...6b1d` (64-char hex) | Secret token required for `POST /api/models/retrain` |
| `DATABASE_URL` | No | `sqlite:///backend/vaultguard.db` | `postgresql://user:pass@host:5432/vaultguard` | Database connection string (future PostgreSQL) |
| `PORT` | No | `8000` | Provided by PaaS (`8080`) | ASGI web server listen port |

### Frontend Environment Variables
| Variable Name | Required | Default (Local) | Production Example | Description |
| :--- | :--- | :--- | :--- | :--- |
| `VITE_API_BASE_URL` | Yes | `http://localhost:8000` | `https://api.vaultguard.yourdomain.com` | Backend REST API base URL |
| `VITE_WS_URL` | Yes | `ws://localhost:8000/ws/transactions` | `wss://api.vaultguard.yourdomain.com/ws/transactions` | WebSocket stream endpoint URL |

---

## 5. Staged Deployment Roadmap

### Stage 1: Demonstration Cloud Deployment (Portfolio)
1. Configure `Dockerfile` for the FastAPI backend.
2. Deploy backend container to Render / Railway with persistent disk for `vaultguard.db`.
3. Set `ALLOWED_ORIGINS` to the Vercel frontend URL.
4. Deploy React frontend to Vercel with `VITE_API_BASE_URL` and `VITE_WS_URL` pointing to the Render domain.
5. Verify SSL/TLS and WebSocket handshake.

### Stage 2: Database Migration & Persistence Hardening
1. Add `psycopg2-binary` to `backend/requirements.txt`.
2. Update `backend/app/database.py` to parse PostgreSQL connection strings.
3. Apply SQLAlchemy schema migrations using Alembic.
4. Migrate initial 55,004 records to managed PostgreSQL instance.

### Stage 3: Security & Access Control
1. Implement JWT bearer token authentication using `python-jose` and `passlib`.
2. Add user registration, login, and analyst role assignment.
3. Protect transaction export, alert updates, and investigation endpoints with user permissions.
4. Implement IP-based token-bucket rate limiting via `slowapi` and Redis.

### Stage 4: Production ML Ops & Monitoring
1. Set up automated data drift monitoring using Evidently AI or Great Expectations.
2. Decouple pipeline retraining from the web server into asynchronous Celery / Redis workers.
3. Track model artifact lineages in MLflow.

---

## 6. Pre-Deployment Verification Checklist

Before deploying any build to an external hosting environment, execute the following local verification checks:

```powershell
# 1. Run full backend & security regression test suite
python -m pytest tests/ -v

# 2. Verify clean production bundle build
cd frontend
npm run build
cd ..

# 3. Verify health endpoint returns 'healthy'
python -c "import urllib.request, json; print(json.loads(urllib.request.urlopen('http://127.0.0.1:8000/api/health').read().decode()))"

# 4. Confirm no secrets are present in tracked files
git status --short
```
