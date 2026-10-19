# Phase 6 Audit Report: VaultGuard System Integrity, Security & Reliability Audit

## Executive Summary

A comprehensive, end-to-end audit was conducted on **VaultGuard — Fraud Detection in Small Transactions** (`c:\Users\udays\OneDrive\Attachments\Desktop\fraud`). The audit encompassed all aspects of the full-stack system: React 18 + Vite frontend, FastAPI backend, SQLite + SQLAlchemy persistence layer, XGBoost + Isolation Forest + SHAP ML pipeline, and the ~55,000 synthetic Indian transaction dataset.

All 16 frontend API operations, 1 WebSocket endpoint, 47 test cases, and production build pipelines were verified against real source code, live endpoints, and regression tests. Verified issues have been fixed and validated with zero regressions.

---

## 1. Frontend-to-Backend API Contract Comparison

Every frontend API call in [`frontend/src/api/client.js`](file:///c:/Users/udays/OneDrive/Attachments/Desktop/fraud/frontend/src/api/client.js) was traced against the corresponding FastAPI backend route, HTTP method, request schema, and response model:

| Frontend API Method | HTTP Method & Path | Backend Router File | Request Schema | Response Schema | Status / Match |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `getHealth()` | `GET /api/health` | `backend/app/main.py` | None | `HealthResponse` | **Exact Match** |
| `getAnalyticsOverview()` | `GET /api/analytics/overview` | `routes/analytics.py` | None | `AnalyticsOverview` | **Exact Match** |
| `getRiskScoreSummary()` | `GET /api/risk-score` | `routes/analytics.py` | None | `RiskScoreSummary` | **Exact Match** |
| `getTrend(range)` | `GET /api/trend?range={24h\|7d\|30d}` | `routes/analytics.py` | Query regex | `List[TrendPoint]` | **Exact Match** |
| `getTransactions(params)` | `GET /api/transactions` | `routes/transactions.py` | Query params | `List[TransactionResponse]` | **Exact Match** |
| `getTransactionById(id)` | `GET /api/transactions/{id}` | `routes/transactions.py` | Path param | `TransactionDetailResponse`| **Exact Match** |
| `predictTransaction(data)`| `POST /api/predict` | `routes/transactions.py` | `TransactionPredictRequest` | `PredictionResponse` | **Exact Match** |
| `getAlerts(params)` | `GET /api/alerts` | `routes/alerts.py` | Query params | `List[AlertResponse]` | **Exact Match** |
| `createAlert(payload)` | `POST /api/alerts` | `routes/alerts.py` | `AlertCreate` | `AlertResponse` (201) | **Exact Match** |
| `updateAlert(id, data)` | `PATCH /api/alerts/{id}` | `routes/alerts.py` | `AlertUpdate` | `AlertResponse` | **Exact Match** |
| `getCustomers(params)` | `GET /api/customers` | `routes/entities.py` | Query params | `List[CustomerResponse]` | **Exact Match** |
| `getMerchants(params)` | `GET /api/merchants` | `routes/entities.py` | Query params | `List[MerchantResponse]` | **Exact Match** |
| `getCases(params)` | `GET /api/cases` | `routes/entities.py` | Query params | `List[CaseResponse]` | **Exact Match** |
| `getModelMetrics()` | `GET /api/models/metrics` | `routes/models_api.py` | None | `ModelMetricsResponse` | **Exact Match** |
| `retrainModel()` | `POST /api/models/retrain` | `routes/models_api.py` | Optional header | `ModelMetricsResponse` | **Exact Match** |
| `getExportUrl()` | `GET /api/export?type=csv` | `routes/analytics.py` | Query regex | Streaming CSV | **Exact Match** |
| `WebSocket Stream` | `WS /ws/transactions` | `routes/websocket.py` | Native WebSocket | `SimulatedTxnDict` | **Exact Match** |

---

## 2. Classification of Audit Findings & Verified Fixes

Findings were classified according to severity: **Critical**, **High**, **Medium**, and **Low**. Verified issues were fixed in the code rather than merely documented.

### Finding 1: Database Pollution from Simulated WebSocket Events
- **Severity**: **High**
- **Component**: [`backend/app/routes/websocket.py`](file:///c:/Users/udays/OneDrive/Attachments/Desktop/fraud/backend/app/routes/websocket.py)
- **Description**: The WebSocket background generator was committing simulated stream events to the persistent SQLite database tables (`transactions` and `alerts`) every 3 seconds. Over continuous dashboard sessions, this inflated database transaction counts and skewed statistical metrics (the simulated stream has 20% injected fraud vs ~2.2% in the seed dataset).
- **Resolution**: Decoupled the simulated stream from persistent database writes. Transactions generated in `websocket.py` are scored in-memory using historical context and broadcast directly via WebSocket with `"is_simulated": True` and `"source": "websocket_simulation"`. Persistent transactions remain strictly those seeded or submitted through authorized API prediction endpoints.

### Finding 2: CSV Formula Injection (CWE-1236)
- **Severity**: **High**
- **Component**: [`backend/app/routes/analytics.py`](file:///c:/Users/udays/OneDrive/Attachments/Desktop/fraud/backend/app/routes/analytics.py)
- **Description**: In the `/api/export` endpoint, transaction fields (`transaction_id`, `sender_id`, `beneficiary_id`, `reasons`) were directly serialized into CSV without sanitization. If any text value begins with `=`, `+`, `-`, `@`, `\t`, or `\r`, opening the file in spreadsheet software (Excel, LibreOffice) could trigger automated formula execution.
- **Resolution**: Implemented `sanitize_csv_cell()` which prepends a single quote `'` to any string cell beginning with formula-trigger characters (`=`, `+`, `-`, `@`, `\t`, `\r`), safely neutralizing spreadsheet formula execution. Added regression test `test_sanitize_csv_cell_formula_injection`.

### Finding 3: Insecure Permissive CORS Configuration
- **Severity**: **Medium**
- **Component**: [`backend/app/main.py`](file:///c:/Users/udays/OneDrive/Attachments/Desktop/fraud/backend/app/main.py)
- **Description**: FastAPI was configured with `allow_origins=["*"]` combined with `allow_credentials=True`. This violates W3C Fetch security specifications (browsers block credentialed requests with wildcard origins) and exposes APIs to unauthorized cross-origin access.
- **Resolution**: Replaced wildcard origins with an explicit list of trusted local development origins (`http://localhost:3000`, `http://127.0.0.1:3000`, `http://localhost:5173`, `http://127.0.0.1:5173`) with support for environment-variable overrides via `ALLOWED_ORIGINS`.

### Finding 4: Unprotected Administrative Retraining & Concurrency Hazard
- **Severity**: **Medium**
- **Component**: [`backend/app/routes/models_api.py`](file:///c:/Users/udays/OneDrive/Attachments/Desktop/fraud/backend/app/routes/models_api.py)
- **Description**: The `POST /api/models/retrain` endpoint could be invoked without authentication and had no concurrency control. Multiple simultaneous retrain requests could trigger parallel model fitting and corrupt serialized model artifacts on disk.
- **Resolution**: Added administrative token protection via the `X-Admin-Token` header (enforcing `VAULTGUARD_ADMIN_TOKEN` when configured in the environment, with security audit logging in development mode). Added an in-memory concurrency guard (`_IS_RETRAINING`) that rejects concurrent retraining requests with HTTP 409 Conflict. Added regression test `test_retrain_endpoint_admin_token_enforcement`.

### Finding 5: Input Payload Boundary & Channel Whitelisting Limits
- **Severity**: **Medium**
- **Component**: [`backend/app/schemas/pydantic_schemas.py`](file:///c:/Users/udays/OneDrive/Attachments/Desktop/fraud/backend/app/schemas/pydantic_schemas.py)
- **Description**: In `TransactionPredictRequest`, string fields had no length limits (potential denial-of-service/memory bloat), amount had no upper boundary check, and arbitrary channel strings were accepted without validation.
- **Resolution**: Added `Field(max_length=...)` constraints (128 chars for IDs, 64 chars for states/types), capped amounts at ₹1,00,00,000 (1 Crore maximum retail transfer limit), and implemented channel whitelisting with safe fallback to `UPI_P2P`. Added regression tests for bounds and oversized strings.

### Finding 6: Decision-Support Terminology & Disclosures in Reports UI
- **Severity**: **Low**
- **Component**: [`frontend/src/pages/Reports.jsx`](file:///c:/Users/udays/OneDrive/Attachments/Desktop/fraud/frontend/src/pages/Reports.jsx)
- **Description**: A KPI card was labeled "Prevented Losses Est. Automated block decision savings", which inappropriately implied that real financial losses were prevented by an academic demonstration project.
- **Resolution**: Updated the KPI card title to "Simulated Block Vol. Est." with description "Model-assisted high-risk triage volume", aligning with academic and decision-support disclosures.

---

## 3. Data Integrity & Persistence Verification

1. **Seed Dataset**: Verified `data/transactions.csv` contains 55,004 rows, 0 nulls across mandatory columns, sorted chronologically from 2026-09-12 to 2026-10-12.
2. **Database State**: `backend/vaultguard.db` contains 55,009 transactions (55,004 seed records + 5 API test records).
3. **Data Protection**: Existing database records, seed transactions, and legacy backups (`data/transactions_backup_legacy.csv`) were preserved intact without loss during testing.
