# Phase 6 Backend Security Audit Checklist & Assessment

## Security Evaluation Summary

| Category | Finding / Status | Risk Level | Mitigation & Verification |
| :--- | :--- | :--- | :--- |
| **SQL Injection** | **PASS** — Zero raw SQL queries; 100% parameterized SQLAlchemy ORM | None | All routes use ORM query builder (`db.query(...)`); ILIKE searches use parameterized filter arguments. |
| **CSV Formula Injection** | **FIXED** — Formula injection characters sanitized in export stream | High | Implemented `sanitize_csv_cell()` neutralizing `=, +, -, @, \t, \r` with single-quote prefix. Verified with tests. |
| **CORS Policy** | **FIXED** — Wildcard credentials vulnerability removed | Medium | Restricted to explicit local development origins (`localhost:3000`, `127.0.0.1:3000`) and configurable `ALLOWED_ORIGINS`. |
| **Payload Boundaries** | **FIXED** — Boundary limits added to Pydantic schemas | Medium | Length constraints (`max_length=128/256`), amount capped at ₹1 Crore, channel whitelisting. |
| **Privileged Operations** | **FIXED** — Administrative retraining guarded | Medium | Concurrency lock (`_IS_RETRAINING`) prevents race conditions; optional `X-Admin-Token` header enforced when configured. |
| **Database Pollution** | **FIXED** — Ephemeral WebSocket stream decoupled from SQLite tables | High | Simulated streaming transactions are scored on-the-fly and broadcast via WebSocket without persistent DB writes. |
| **Secrets Exposure** | **PASS** — No secrets or database credentials committed to Git | None | `.gitignore` excludes `.env`, `*.db`, and cache files. `.env.example` contains only placeholder URLs. |
| **Sensitive Data Logging**| **PASS** — No plain-text passwords or PII in logs | Low | No PII or authentication secrets logged; error handlers return structured JSON. |

---

## 1. Detailed Vulnerability Audits & Verifications

### 1.1 SQL Injection (CWE-89)
- **Status**: **PASS (Verified Safe)**
- **Audit Details**: A repository-wide audit for `text()`, `execute()`, and raw string formatting inside database calls confirmed zero raw SQL statements.
- **Evidence**: Every query in [`backend/app/routes/`](file:///c:/Users/udays/OneDrive/Attachments/Desktop/fraud/backend/app/routes/) utilizes SQLAlchemy ORM expressions:
  ```python
  # Parameterized query with safe ILIKE binding
  search_filter = f"%{search}%"
  query = query.filter(TransactionORM.transaction_id.ilike(search_filter))
  ```

### 1.2 CSV Formula / Spreadsheet Injection (CWE-1236)
- **Status**: **FIXED & VERIFIED**
- **Audit Details**: In `/api/export`, text fields were exported directly into CSV streams. A malicious transaction ID (e.g., `=cmd|'/C calc'!A0`) would execute arbitrary commands in spreadsheet viewers.
- **Fix**: Implemented `sanitize_csv_cell()` in [`backend/app/routes/analytics.py`](file:///c:/Users/udays/OneDrive/Attachments/Desktop/fraud/backend/app/routes/analytics.py):
  ```python
  def sanitize_csv_cell(val):
      if val is None:
          return ""
      s = str(val)
      if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
          return f"'{s}"
      return s
  ```
- **Verification**: Verified with `test_sanitize_csv_cell_formula_injection` and `test_export_endpoint_returns_sanitized_csv`.

### 1.3 Cross-Origin Resource Sharing (CORS) Misconfiguration
- **Status**: **FIXED & VERIFIED**
- **Audit Details**: `CORSMiddleware` in `backend/app/main.py` previously configured `allow_origins=["*"]` with `allow_credentials=True`.
- **Fix**: Updated [`backend/app/main.py`](file:///c:/Users/udays/OneDrive/Attachments/Desktop/fraud/backend/app/main.py) to explicitly bind allowed origins to local development URLs (`http://localhost:3000`, `http://127.0.0.1:3000`, `http://localhost:5173`, `http://127.0.0.1:5173`) with optional `ALLOWED_ORIGINS` environment override.

### 1.4 Input Validation & Payload Boundary Limits
- **Status**: **FIXED & VERIFIED**
- **Audit Details**: Unbounded string fields could allow excessive payload memory consumption, and negative or unbounded transaction amounts were possible.
- **Fix**: Added Pydantic field validators and length limits in [`backend/app/schemas/pydantic_schemas.py`](file:///c:/Users/udays/OneDrive/Attachments/Desktop/fraud/backend/app/schemas/pydantic_schemas.py):
  - `amount`: Must be non-negative and $\le ₹10,000,000$ (1 Crore).
  - String fields (`transaction_id`, `sender_id`, `device_id`): Capped at 64–128 characters.
  - `channel`: Whitelisted to valid payment channels (`UPI_P2P`, `UPI_P2M_QR`, `WALLET`, `IMPS`, `RUPAY_CARD`) with safe fallback.

### 1.5 Administrative Endpoint Protection & Race Condition Prevention
- **Status**: **FIXED & VERIFIED**
- **Audit Details**: `POST /api/models/retrain` allowed unauthenticated users to trigger CPU-intensive pipeline retraining and lacked concurrency guards.
- **Fix**: Added administrative token validation (`X-Admin-Token` header matched against `VAULTGUARD_ADMIN_TOKEN` when set in the environment) and an in-memory lock (`_IS_RETRAINING`) that returns HTTP 409 Conflict if a retraining job is already running.

### 1.6 WebSocket Resource Management & Stream Decoupling
- **Status**: **FIXED & VERIFIED**
- **Audit Details**: Continuous WebSocket streams were committing simulated transactions to the SQLite database every 3 seconds.
- **Fix**: Removed persistent database writes in [`backend/app/routes/websocket.py`](file:///c:/Users/udays/OneDrive/Attachments/Desktop/fraud/backend/app/routes/websocket.py). Stream items are scored in-memory and broadcast with `"is_simulated": True`. Connection cleanup is handled via `try ... finally: manager.disconnect()`.

---

## 2. Remaining Known Risks & Architectural Limitations

1. **Authentication Architecture**:
   - The platform does not currently implement a full multi-tenant user authentication system (e.g., JWT / OAuth2 / session cookies).
   - *Academic Limitation*: Administrative operations are protected via token headers, but individual analyst logins, role-based access control (RBAC), and session timeouts are not yet implemented. This is appropriate for an academic demonstration and local portfolio environment, but must be added before commercial deployment.
2. **Database Concurrency**:
   - SQLite uses file-level locking for writes. Under high write loads (e.g., > 100 simultaneous concurrent API predictions), SQLite may return `database is locked` errors. For production deployment, migration to PostgreSQL or MySQL with connection pooling (e.g., PgBouncer) is required.
3. **In-Memory Rate Limiting**:
   - API endpoints do not currently include IP-based token-bucket rate limiting (e.g., Redis-backed rate limiting). In a public cloud deployment, a reverse proxy (e.g., NGINX / Cloudflare) with rate limiting must be placed in front of the application.
