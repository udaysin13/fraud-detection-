# VaultGuard — Fraud Detection in Small Transactions

[![VaultGuard License: MIT](https://img.shields.io/badge/License-MIT-teal.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/React-18.2-61DAFB.svg?logo=react&logoColor=black)](https://react.dev/)
[![Vite 5](https://img.shields.io/badge/Vite-5.4-646CFF.svg?logo=vite&logoColor=white)](https://vitejs.dev/)
[![Tailwind CSS 3.4](https://img.shields.io/badge/Tailwind_CSS-3.4-38B2AC.svg?logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![XGBoost](https://img.shields.io/badge/XGBoost-2.0%2B-eb4924.svg)](https://xgboost.readthedocs.io/)
[![SHAP](https://img.shields.io/badge/SHAP-Explainability-brightgreen.svg)](https://shap.readthedocs.io/)

> **Academic & Portfolio Demonstration Project**: An end-to-end, real-time fraud detection and decision-support intelligence platform specifically designed for high-velocity Indian digital payments (UPI P2P, UPI P2M QR, IMPS, Wallets, and RuPay).

---

## 1. Problem Statement & Motivation

India's retail payment ecosystem—spearheaded by the Unified Payments Interface (UPI)—processes over **14 billion transactions monthly**, with low-value peer-to-peer (P2P) transfers and merchant QR payments (P2M) accounting for more than 75% of total volume. While instant digital clearing has revolutionized financial inclusion, it has also introduced attack surfaces tailored to small-value transactions:

- **UPI Micro-Testing Probes**: Automated bots executing rapid, sub-₹100 transactions to test compromised payment handles before launching larger account-draining operations.
- **SIM Swap Account Takeover (ATO)**: Fraudsters obtaining fraudulent duplicate SIM cards to intercept SMS OTPs and authorizing UPI transfers from new, unauthorized device IDs.
- **Mule QR Terminal Spikes**: Inactive or newly created merchant QR terminals experiencing sudden, abnormal transaction velocity surges to launder stolen funds.
- **Regulatory Amount Structuring (Smurfing)**: Splitting illicit funds into amounts positioned just below regulatory surveillance thresholds (e.g., ₹990–₹999, ₹1,990–₹1,999, ₹4,950–₹4,999, or ₹9,900–₹9,999).

Legacy rule engines relying on static thresholds either suffer from high false-positive rates that disrupt legitimate users or miss sophisticated multi-signal attacks entirely. **VaultGuard** demonstrates how hybrid machine learning combined with leakage-free temporal feature engineering and real-time explainability provides effective decision support for fraud operations teams.

---

## 2. Project Objectives & Scope

- **Hybrid Inference Architecture**: Combine supervised classification (class-weighted XGBoost) with unsupervised anomaly detection (Isolation Forest) into a calibrated 0–100 risk score.
- **Leakage-Safe Feature Engineering**: Compute point-in-time entity velocity and expanding baseline averages without future-data contamination or temporal leakage.
- **Local Explainability**: Return model-provided reason strings, which can include SHAP-derived signals, rule checks, and baseline labels; they are not legal proof of fraud.
- **Demonstration Application**: Provide a responsive white financial-analytics dashboard with teal and blue accents, Indian Rupee (`₹`) formatting, a clearly simulated WebSocket feed, and documented REST APIs.
- **Explicit Project Scope**: VaultGuard is designed as an **academic prototype and technical portfolio demonstration**. It operates on a synthetic dataset modeled after Indian digital payment workflows and acts as a decision-support advisor—not an authorized banking gateway.

---

## 3. Feature Matrix

### Implemented Features
- [x] **Hybrid ML Risk Scoring**: Supervised XGBoost (75% weight) + Unsupervised Isolation Forest (25% weight) yielding a calibrated 0–100 score.
- [x] **Dynamic TreeSHAP Explanations**: Real-time calculation of top feature contributors pushing scores toward suspicion.
- [x] **Leakage-Free Time-Series Features**: 39 point-in-time features using `closed="left"` rolling windows and expanding historical statistics.
- [x] **FastAPI REST API**: 16 endpoints for predictions, analytics, alerts, transactions, entities, metrics, and CSV exports.
- [x] **Simulated WebSocket Stream**: Live payment stream (`/ws/transactions`) broadcasting newly scored events every 3 seconds without polluting database storage.
- [x] **Analyst Demonstration UI**: Light-themed Overview, Transactions, Fraud Analysis, Alerts, Investigations, and Model Insights, with secondary customer, merchant, report, compliance, and admin routes.
- [x] **Indian Payment Localization**: Native support for VPA routing, SIM swap flags, device ATO signals, and Indian numbering (`₹1,24,500.00`).
- [x] **Security Hardening**: Formula injection sanitization on CSV exports (CWE-1236), bounded payload validators, CORS origin restrictions, and retrain concurrency guards.
- [x] **Automated Test Suite**: Pytest unit, integration, dataset, ML pipeline, and security regression checks; see the verification record below for the current run.

### Planned / Roadmap Features
- [ ] Multi-tenant JWT authentication and Role-Based Access Control (RBAC).
- [ ] Database migration from SQLite to PostgreSQL with PgBouncer connection pooling.
- [ ] Distributed Redis-backed token-bucket API rate limiting.
- [ ] Webhook dispatcher for real-time SMS/WhatsApp customer step-up challenge verification.
- [ ] Automated drift detection and pipeline retraining via Apache Airflow / Celery workers.

---

## 4. Technology Stack

| Layer | Technologies | Purpose |
| :--- | :--- | :--- |
| **Frontend UI** | React 18, Vite 5, Tailwind CSS 3.4, Recharts, Lucide Icons | Responsive fintech dashboard, charts, inspection drawers |
| **Backend API** | FastAPI, Starlette, Pydantic v2, Uvicorn | Async REST API, request validation, WebSocket broadcasting |
| **Data & ORM** | SQLite, SQLAlchemy 2.0 | Transaction ledger, entity profiles, alert tracking |
| **Machine Learning** | XGBoost, scikit-learn, SHAP, Joblib, NumPy, Pandas | Leakage-free velocity engineering, hybrid scoring, explainability |
| **Testing & QA** | Pytest, FastAPI TestClient, Vite Build Pipeline | Unit, integration, security regression tests, bundle compilation |

---

## 5. System Architecture Overview

```mermaid
flowchart TD
    subgraph Client["Frontend Layer (React 18 + Vite)"]
        UI["VaultGuard Web App (:3000)"]
        WSClient["WebSocket Stream Listener"]
    end

    subgraph API["Backend API Layer (FastAPI :8000)"]
        Router["API Gateway / Routers"]
        Validator["Pydantic v2 Request Validation"]
        CORS["Strict CORS Policy"]
    end

    subgraph ML["ML Inference Service (Python)"]
        FE["Point-in-Time Feature Engineering\n(ml/features.py)"]
        History["Bounded Historical Context\n(Prior Txns strictly < current_ts)"]
        XGB["XGBoost Classifier (75%)"]
        ISO["Isolation Forest (25%)"]
        SHAPEngine["TreeSHAP Explainer"]
    end

    subgraph Storage["Persistence & Artifacts"]
        DB[("SQLite Database\n(vaultguard.db)")]
        Models["Serialized Models\n(ml/saved_models/*.joblib)"]
    end

    UI -->|REST API Requests| CORS --> Router --> Validator
    WSClient <-->|Live Stream /ws/transactions| Router
    Validator --> ML
    ML --> History --> DB
    ML --> FE --> XGB & ISO
    XGB --> SHAPEngine
    Validator --> DB
    XGB & ISO & SHAPEngine -->|Risk Score + Reasons| Router --> UI
```

For complete technical diagrams and request lifecycles, see [`docs/architecture.md`](docs/architecture.md).

---

## 6. Project Directory Structure

```text
fraud/
├── backend/
│   ├── app/
│   │   ├── database.py              # SQLAlchemy engine & session factory
│   │   ├── main.py                  # FastAPI entrypoint, lifespan, CORS configuration
│   │   ├── models/orm.py            # ORM models (Transaction, FraudAlert, Entity profiles)
│   │   ├── routes/
│   │   │   ├── alerts.py            # GET, POST, PATCH /api/alerts
│   │   │   ├── analytics.py         # GET /api/analytics/overview, /api/trend, /api/export
│   │   │   ├── entities.py          # GET /api/customers, /api/merchants, /api/cases
│   │   │   ├── models_api.py        # GET /api/models/metrics, POST /api/models/retrain
│   │   │   ├── transactions.py      # GET /api/transactions, POST /api/predict
│   │   │   └── websocket.py         # WS /ws/transactions simulated stream
│   │   ├── schemas/
│   │   │   └── pydantic_schemas.py  # Request & response validation schemas
│   │   └── services/
│   │       ├── data_loader.py       # Auto-seeding on initial startup
│   │       └── ml_service.py        # ML singleton loader & historical context query
│   └── requirements.txt             # Backend dependencies
├── data/
│   ├── transactions.csv             # 55,004 synthetic Indian payment records
│   ├── transactions_backup_legacy.csv # Phase 2 benchmark backup
│   └── DATASET_SCHEMA.md            # Detailed dataset schema and provenance
├── docs/
│   ├── api.md                       # Comprehensive API endpoint reference
│   ├── architecture.md              # System design, data flows, and trust boundaries
│   ├── deployment-readiness.md      # Deployment readiness, blockers, and checklist
│   └── ml-methodology.md            # ML pipeline, feature leakage audit, and metrics
├── frontend/
│   ├── .env.example                 # Frontend configuration template
│   ├── package.json                 # React, Vite, Tailwind dependencies
│   ├── vite.config.js               # Chunk splitting & dev server configuration
│   ├── tailwind.config.js           # Light theme and risk color tokens
│   └── src/
│       ├── api/client.js            # Centralized API client with ApiError handling
│       ├── components/              # Header, Sidebar, Drawers, Modals, KpiCards
│       ├── context/FilterContext.jsx# WebSocket manager & global filter state
│       ├── pages/                   # Core workflows and retained secondary routes
│       └── utils/formatters.js      # INR currency, dates, and risk styling
├── ml/
│   ├── features.py                  # Leakage-safe feature extraction (39 features)
│   ├── generate_data.py             # Synthetic Indian digital payment generator
│   ├── predict.py                   # Scoring module & SHAP reason generator
│   ├── train.py                     # Chronological training, threshold tuning, benchmarks
│   ├── requirements.txt             # ML dependencies (xgboost, shap, scikit-learn)
│   └── saved_models/                # Serialized model joblibs and metrics.json
├── reports/
│   ├── phase6_audit_report.md       # Full-stack QA & contract audit findings
│   ├── phase6_ml_reliability.md     # Feature leakage analysis & metric root cause
│   ├── phase6_security_checklist.md # Vulnerability audit & mitigations
│   └── phase6_test_results.md       # Pytest logs and production build outputs
├── tests/
│   ├── test_api.py                  # API endpoint integration tests
│   ├── test_audit_security.py       # Security, boundary, and edge-case regression tests
│   ├── test_dataset.py              # Dataset schema and integrity tests
│   ├── test_ml_pipeline.py          # Temporal feature leakage & split tests
│   └── test_scoring.py              # Inference function & threshold tests
├── .gitignore                       # Git exclusion rules (.env, *.db, cache)
└── README.md                        # Primary project documentation
```

---

## 7. Dataset & Synthetic Provenance

VaultGuard utilizes a deterministic synthetic dataset containing **55,004 transactions** spanning 30 consecutive days (2026-09-12 to 2026-10-12):

- **Synthetic Disclosure**: All records, Virtual Payment Addresses (VPAs), customer IDs, and merchant entities are synthetically generated for academic demonstration. **This dataset is NOT sourced from NPCI, RBI, or commercial banks.**
- **Fraud Prevalence**: ~2.36% overall (1,301 flagged transactions).
- **Payment Channels**: UPI P2M QR (45%), UPI P2P (35%), Wallets (10%), IMPS (5%), RuPay (5%).
- **Modeled Fraud Scenarios**:
  1. *SIM Swap Account Takeover (ATO)*: Immediate high-value transfer following SIM card change and new device authorization.
  2. *UPI Micro-Testing Probes*: Sub-₹100 rapid velocity transfers verifying account validity.
  3. *Mule QR Velocity Spikes*: Abnormal merchant terminal volume surge (>3x 24h baseline).
  4. *Regulatory Structuring*: Amounts clustered within 2% below Indian surveillance thresholds (₹990–₹999, ₹1,990–₹1,999, ₹4,950–₹4,999, ₹9,900–₹9,999).
  5. *New Beneficiary Bursts*: Successive transfers to unfamiliar recipient VPAs within minutes.
  6. *Phishing Collect Requests*: Unauthorized incoming collect-request approvals.

Detailed field definitions and statistical distributions are documented in [`data/DATASET_SCHEMA.md`](data/DATASET_SCHEMA.md).

---

## 8. Machine Learning Pipeline & Evaluation

### Feature Engineering & Zero-Leakage Guarantee
Feature engineering in [`ml/features.py`](ml/features.py) extracts **39 point-in-time features**:
1. **Rolling Velocity Counts** (`txn_count_1min`, `txn_count_10min`, `txn_count_1hour`, `txn_count_24h`): Computed per sender using `rolling(window, closed="left")`, strictly excluding the transaction being scored.
2. **Expanding Historical Baseline** (`amount_to_avg_ratio`): Computed as prior cumulative sum divided by prior count, strictly excluding the current row's amount.
3. **Temporal Features**: `hour_of_day`, `day_of_week`, `is_night`.
4. **Security Signals**: `sim_change_flag`, `is_new_device`, `high_risk_device_action`.
5. **Merchant Dynamics**: `merchant_spike_ratio` comparing 1-hour volume to expanding 24-hour baseline.

### Chronological Splitting & Preprocessing
- **Train Split (70%)**: 38,500 transactions (2026-09-12 to 2026-10-03).
- **Validation Split (15%)**: 8,250 transactions (2026-10-03 to 2026-10-08).
- **Untouched Test Split (15%)**: 8,250 transactions (2026-10-08 to 2026-10-12).
- **Isolation**: `StandardScaler` is fitted strictly on the training split. Decision threshold ($T^* = 0.57$) is tuned exclusively on the validation split to maximize $F_1$. The test set remains untouched until final benchmarking.

### Model Benchmarks on Untouched Test Set (8,250 Transactions)

| Model Architecture | PR-AUC | ROC-AUC | F1-Score | Recall | Precision | FPR |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **XGBoost Classifier** (Selected) | **0.9986** | **1.0000** | **0.9861** | **0.9834** | **0.9889** | **0.02%** |
| **Random Forest** (100 Trees, Depth 10) | 0.9969 | 0.9999 | 0.9777 | 0.9669 | 0.9887 | 0.02% |
| **Logistic Regression** (Balanced Weights) | 0.9648 | 0.9979 | 0.9183 | 0.9006 | 0.9368 | 0.14% |
| **Isolation Forest** (Unsupervised) | 0.5642 | 0.8959 | 0.5714 | 0.4751 | 0.7167 | 0.42% |

> [!NOTE]
> **Why are test metrics so high?**  
> The synthetic data generation rules inject clean, distinct behavioral patterns for fraud (e.g. SIM swaps rarely occur in benign synthetic records). The high metrics prove the ML pipeline correctly captures these signals without leakage, but **do not imply equivalent real-world accuracy**, where noisy user behavior, delayed chargebacks, and adversarial adaptation reduce real-world PR-AUC to 0.35–0.75. See [`docs/ml-methodology.md`](docs/ml-methodology.md).

### Decision Thresholds & Risk Mapping
$$\text{Risk Score} = 0.75 \times (\text{XGBoost Probability}) + 0.25 \times (\text{Isolation Forest Score}) \times 100$$
- **0.0 – 40.0**: `Allow` / `LOW_RISK` (Green)
- **40.1 – 70.0**: `Manual Review` / `REVIEW` (Amber)
- **70.1 – 100.0**: `Block` / `HIGH_RISK` (Red)

---

## 9. Backend API Overview

The FastAPI backend exposes 16 documented REST endpoints and 1 WebSocket stream:

- `GET /api/health` — System status, DB connectivity, model artifact readiness, record count.
- `GET /api/analytics/overview` — High-level metrics (`total_transactions`, `fraud_rate_pct`, `avg_risk_score`).
- `GET /api/risk-score` — Total flagged transaction counts and dynamic SHAP risk contributor weights.
- `GET /api/trend?range=24h|7d|30d` — Historical time-series points for volume and flagged counts.
- `GET /api/transactions` — Paginated transactions with multi-attribute filtering (`channel`, `decision`, `search`).
- `GET /api/transactions/{id}` — Single transaction lookup with complete metadata and routing details.
- `POST /api/predict` — Real-time scoring payload using Indian UPI/ATO attributes, returning score, decision, and SHAP reasons.
- `GET /api/alerts` — Incident feed with filtering by status and segment.
- `POST /api/alerts` — Create security alerts.
- `PATCH /api/alerts/{id}` — Update alert status (`Monitoring`, `Investigating`, `Resolved`).
- `GET /api/customers` — Customer risk profiles and cumulative spend.
- `GET /api/merchants` — Merchant volume spike ratios and anomaly alerts.
- `GET /api/cases` — Analyst investigation case roster.
- `GET /api/models/metrics` — Serialized model performance metrics and confusion matrix.
- `POST /api/models/retrain` — Pipeline retraining trigger (protected by concurrency lock and admin token).
- `GET /api/export?type=csv` — Sanitized CSV streaming export (formula injection protected).
- `WS /ws/transactions` — Real-time simulated Indian payment stream.

Detailed request/response schemas are documented in [`docs/api.md`](docs/api.md). Interactive Swagger UI is available at `http://127.0.0.1:8000/docs`.

---

## 10. Frontend Application Workflows

Built with React 18, Vite, and Tailwind CSS, the UI provides a professional fintech security dashboard:

1. **Overview Dashboard**: Database-backed transaction and label counts, saved model F1, decision distribution, trend data, and a separately labeled simulated stream.
2. **Transactions Explorer**: Full transaction ledger with search, filtering by channel and risk tier, sorting, pagination, and a slide-over transaction detail drawer with VPA routing and SHAP attributions.
3. **Fraud Analysis**: Interactive prediction form with 4 sample scenarios; the returned score and reasons are estimates, and the app does not process or block payments.
4. **Alerts & Case Management**: Security incident feed with live status transitions (`Investigating`, `Resolved`).
5. **Entity Directories**: Customer risk tiers and merchant volume spike ratio tracking.
6. **Model Insights**: Saved model benchmarks, confusion matrix, validation threshold, and a read-only summary of modeled input signals. Metrics are from synthetic data.
7. **Reports & Compliance**: CSV export and database counts; compliance references are explicitly informational and are not an assessment or certification.
8. **System Administration**: Infrastructure health telemetry and runtime environment diagnostics.

---

## 11. Step-by-Step Installation & Local Setup

### Prerequisites
- **Python**: Version 3.10, 3.11, 3.12, or 3.14 installed with `pip`.
- **Node.js**: Version 18.0 or higher with `npm`.
- **Git**: Installed and available on your system path.

### Step 1: Clone Repository
```powershell
git clone https://github.com/your-username/fraud-detection-small-transactions.git
cd fraud-detection-small-transactions
```

### Step 2: Set Up Python Backend Environment
```powershell
# Create and activate Python virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install backend and ML dependencies
pip install -r backend/requirements.txt
pip install -r ml/requirements.txt
```

Configure the MySQL 8 database URL locally. Keep credentials in an ignored root `.env` file or a session environment variable; do not commit credentials:
```powershell
$env:DATABASE_URL = "mysql+pymysql://USER:PASSWORD@localhost:3306/vaultguard_db"
```
Create the `vaultguard_db` database in MySQL before starting the API. SQLite can also be selected for local tests with `DATABASE_URL=sqlite:///backend/vaultguard.db`.

### Step 3: Set Up React Frontend Environment
```powershell
cd frontend
npm install
cd ..
```

### Step 4: Configure Environment Variables
Copy the frontend environment placeholder:
```powershell
cp frontend/.env.example frontend/.env
```
Default contents:
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws/transactions
```

---

## 12. Running the Application Locally

### Terminal 1: Start FastAPI Backend
From the project root with the virtual environment activated:
```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API Server: `http://127.0.0.1:8000`
- Interactive API Docs (Swagger): `http://127.0.0.1:8000/docs`

> *Note: On first startup, the backend automatically seeds `backend/vaultguard.db` from `data/transactions.csv`.*

### Terminal 2: Start React Frontend
In a separate terminal:
```powershell
cd frontend
npm run dev
```
- Web Application: `http://localhost:3000`

---

## 13. Running Automated Tests & Production Builds

### Run Backend & Security Tests
From the project root:
```powershell
python -m pytest tests/ -v
```
Test counts and warnings vary by environment; record the output from the current run rather than relying on a historical count.

### Run Frontend Production Build
From the `frontend` directory:
```powershell
cd frontend
npm run build
```
The build compiles the production bundle; consult the current build output for module counts and bundle sizes.

### Current Verification Record
- Backend suite: `49 passed, 5 warnings` (`tests/`). Warnings came from Starlette/httpx deprecation, SHAP colormap deprecations, and a single-class scikit-learn metric edge case.
- Frontend production build: passed with Vite 5.4.21; 2,382 modules transformed.
- Browser smoke checks: overview loaded real database/model API values; prediction returned a score and recommendation; CSV endpoint returned HTTP 200 with a CSV header.
- Responsive check: at a 385px document viewport, document and body widths matched; mobile menu behavior could not be confirmed consistently because the browser viewport emulator reset to desktop during interaction.
- Not manually verified: every route at tablet/mobile sizes, every transaction filter combination, keyboard-only modal operation, and browser console cleanliness.

### Interface and reporting scope
The default palette uses canvas `#F5F8FC`, white surfaces, primary text `#17243A`, teal `#0F766E`, blue `#2563EB`, and border `#E3EAF2`. CSV export is implemented; scheduled audit reports, loss-prevention estimates, regulatory enforcement, and rule-toggle controls are not claimed as working features.

---

## 14. Limitations, Ethics & Future Improvements

1. **Synthetic Data Modeling**: Trained exclusively on synthetic records; does not reflect complex real-world fraud adaptations or adversarial evasion.
2. **Explainability Boundaries**: SHAP attributions reflect statistical model contributions, not legal proof of fraud. High scores indicate elevated suspicion requiring human operational review.
3. **Database Architecture**: SQLite file locking limits high write concurrency. Production deployments require PostgreSQL.
4. **Authentication**: Admin operations are guarded via token headers; multi-tenant user authentication with JWT/OAuth2 is a planned improvement.
5. **Privacy by Design**: Sensitive customer VPAs and identifiers in demonstration payloads are fictional and sanitized.

---

## 15. Academic Project Disclaimer & License

**Disclaimer**: This project is developed as an academic demonstration and engineering portfolio piece. It is not affiliated with, endorsed by, or authorized by the National Payments Corporation of India (NPCI), the Reserve Bank of India (RBI), or any commercial financial institution. Do not use this software for processing live financial transactions or making automated blocking decisions on real payment rails.

**License**: Distributed under the [MIT License](LICENSE).
