# VaultGuard System Architecture

This document describes the technical architecture, data flows, components, and security trust boundaries of **VaultGuard — Fraud Detection in Small Transactions**.

---

## 1. System Architecture Diagram

```mermaid
flowchart TB
    subgraph Client["Client Browser Layer (React 18 + Vite)"]
        UI["Web Dashboard UI\n(:3000)"]
        FilterCtx["FilterContext & WebSocket Manager"]
        Drawer["TransactionDetailDrawer\n(VPA Routing & SHAP List)"]
    end

    subgraph API["Backend API Gateway (FastAPI :8000)"]
        CORS["Strict CORS Middleware\n(Trusted Origins Only)"]
        Router["FastAPI Route Handlers"]
        Pydantic["Pydantic v2 Request Validation\n(Bounds, Whitelists & Sanity)"]
    end

    subgraph MLService["ML Inference Subsystem (ml_service.py)"]
        Singleton["Singleton Model Loader\n(_MODEL_CACHE)"]
        HistContext["Historical Context Extractor\n(Prior Txns strictly < current_ts)"]
        FE["Point-in-Time Feature Engineering\n(ml/features.py, 39 features)"]
        XGBModel["XGBoost Classifier\n(Supervised Fraud Prob)"]
        ISOModel["Isolation Forest\n(Unsupervised Anomaly Score)"]
        SHAP["TreeSHAP Explainer Engine\n(Top 3 Evidence Signals)"]
        Scorer["Risk Score Aggregator\n(75% XGB + 25% ISO)"]
    end

    subgraph Stream["Real-Time Streaming Engine"]
        WS["WebSocket Stream Handler\n(/ws/transactions)"]
        SimGen["Simulated Indian Txn Generator\n(In-Memory Scoring)"]
    end

    subgraph Storage["Persistence & Artifacts"]
        SQLite[("SQLite Database\n(backend/vaultguard.db)")]
        Models["Serialized Joblib Artifacts\n(ml/saved_models/*.joblib)"]
        Dataset["Synthetic Indian Dataset\n(data/transactions.csv)"]
    end

    %% Client to API
    UI -->|REST API HTTP Calls| CORS --> Router --> Pydantic
    FilterCtx <-->|WebSocket Connection| WS

    %% In-Memory Streaming
    WS --> SimGen --> MLService
    SimGen -.->|Broadcasts In-Memory with is_simulated=True| WS
    WS -.->|Zero DB Writes| SQLite

    %% Prediction Flow
    Pydantic -->|Validated Payload| MLService
    MLService --> HistContext -->|SQL: timestamp < current_ts| SQLite
    MLService --> FE
    FE --> XGBModel & ISOModel
    Singleton --> Models
    XGBModel --> Scorer
    ISOModel --> Scorer
    XGBModel --> SHAP
    Scorer & SHAP -->|Score + Decision + Reasons| Router
    Router -->|Persists Scored Txn & Alerts| SQLite
    Router -->|JSON Response| UI
```

---

## 2. Prediction Request Lifecycle

The sequence below illustrates the end-to-end lifecycle when a transaction is submitted for scoring via `POST /api/predict`:

```mermaid
sequenceDiagram
    autonumber
    actor Client as Analyst / Frontend Client
    participant API as FastAPI Router (/api/predict)
    participant Val as Pydantic Request Validator
    participant DB as SQLite Database (vaultguard.db)
    participant MLSvc as ML Service (ml_service.py)
    participant FE as Feature Engineer (features.py)
    participant Models as XGBoost & Isolation Forest
    participant SHAP as TreeSHAP Explainer

    Client->>API: POST /api/predict (JSON payload)
    API->>Val: Validate payload (types, bounds, channel whitelist)
    alt Validation Failure
        Val-->>Client: 422 Unprocessable Entity (Structured validation error)
    end
    Val->>MLSvc: predict_single_transaction(txn_dict, db)
    MLSvc->>DB: Query historical transactions (sender_id == sender, timestamp < current_ts, limit=50)
    DB-->>MLSvc: Return prior transaction history DataFrame
    MLSvc->>FE: extract_single_txn_features(txn, history_df)
    Note over FE: Compute point-in-time velocity (1m, 10m, 1h, 24h)<br/>expanding average ratio, SIM/device flags
    FE-->>MLSvc: 1-row feature vector (39 features)
    MLSvc->>Models: Predict XGBoost probability & Isolation Forest anomaly score
    Models-->>MLSvc: xgb_prob (e.g. 0.985), iso_norm (e.g. 0.524)
    MLSvc->>SHAP: Calculate TreeSHAP values for single row
    SHAP-->>MLSvc: Top 3 positive feature attributions
    Note over MLSvc: Compute risk score = (0.75 * prob + 0.25 * iso) * 100<br/>Determine decision (Allow, Review, Block)
    MLSvc-->>API: Return scoring dictionary
    API->>DB: Persist scored record in TransactionORM (source="api")
    opt Decision is Block or Manual Review
        API->>DB: Auto-generate AlertORM and FraudAlertORM records
    end
    DB-->>API: Commit transaction
    API-->>Client: 200 OK (PredictionResponse JSON)
```

---

## 3. Model Training & Evaluation Lifecycle

The offline pipeline in [`ml/train.py`](file:///c:/Users/udays/OneDrive/Attachments/Desktop/fraud/ml/train.py) trains, tunes, evaluates, and serializes the machine learning models:

```mermaid
flowchart TD
    Raw["Raw Dataset (data/transactions.csv, 55,004 rows)"] --> ChronoSort["Sort Chronologically by Timestamp & Txn ID"]
    ChronoSort --> FE["Feature Engineering (39 features, zero leakage)"]
    FE --> Split["Chronological Split\n• Train Split: 70% (38,500 rows)\n• Val Split: 15% (8,250 rows)\n• Test Split: 15% (8,250 rows)"]

    subgraph TrainSplit["Training Phase (Train Split Only)"]
        FitScaler["Fit StandardScaler on X_train"]
        FitXGB["Fit XGBoost (scale_pos_weight=47.37, depth=5)"]
        FitRF["Fit Random Forest (100 trees, depth=10)"]
        FitLR["Fit Logistic Regression (balanced weights)"]
        FitISO["Fit Isolation Forest (contamination=0.02)"]
    end

    subgraph ValSplit["Threshold Tuning (Validation Split Only)"]
        ValProbs["Predict validation probabilities"]
        TuneT["Sweep thresholds 0.05 - 0.95 to maximize Val F1"]
        SelectedT["Select optimal threshold T* = 0.57"]
    end

    subgraph TestSplit["Final Evaluation (Untouched Test Split Only)"]
        TestProbs["Score untouched test transactions"]
        Metrics["Compute PR-AUC, ROC-AUC, F1, Recall, Precision, Confusion Matrix"]
    end

    subgraph Artifacts["Serialization (ml/saved_models/)"]
        Joblibs["Dump *.joblib (xgb, rf, lr, iso, scaler, shap, feature_names)"]
        MetricsJSON["Dump metrics.json (benchmarks, splits, confusion matrix)"]
    end

    Split --> TrainSplit
    TrainSplit --> ValSplit
    ValSplit --> TestSplit
    TrainSplit --> Artifacts
    TestSplit --> Artifacts
```

---

## 4. Persisted vs. Simulated Transactions Architecture

A critical architectural distinction in VaultGuard is the separation between **persisted database transactions** and **simulated streaming events**:

| Dimension | Persisted Transactions (`source="seed"` or `"api"`) | Simulated Stream Events (`source="websocket_simulation"`) |
| :--- | :--- | :--- |
| **Origin** | Seed CSV import or authenticated `POST /api/predict` calls | In-memory synthetic generator in `websocket.py` |
| **Storage** | Persisted in SQLite `transactions` and `alerts` tables | **Zero database writes**; broadcast strictly in-memory |
| **Database Impact** | Included in total transaction counts and analytics KPIs | Does not alter database counts or skew fraud ratios |
| **Frontend Visibility** | Transactions explorer ledger, investigation cases | Live stream ticker and floating notifications |
| **UI Flagging** | Rendered as official ledger records | Explicitly tagged with `"is_simulated": True` and visual stream badge |

---

## 5. Current Trust Boundaries & Architectural Limitations

1. **Client / Server Boundary**:
   - Client-side validation in the React UI provides immediate user feedback, but server-side validation in FastAPI via Pydantic v2 remains the authoritative security boundary.
   - All string fields, amounts, and payment channels are sanitized and validated at the API boundary before reaching the ML service.
2. **Database Concurrency & Locking**:
   - SQLite enforces database-level write locks. While read operations are concurrent, continuous high-concurrency write bursts can cause lock contention. In enterprise production, the persistence layer must be migrated to PostgreSQL.
3. **Administrative Access**:
   - The model retraining endpoint (`POST /api/models/retrain`) is guarded by a concurrency mutex lock and an optional `X-Admin-Token` header. Full multi-tenant role-based access control (RBAC) with JSON Web Tokens (JWT) is planned for future phases.
4. **CORS & Network Scope**:
   - CORS is explicitly locked to trusted local development origins (`http://localhost:3000`, `http://127.0.0.1:3000`, `http://localhost:5173`, `http://127.0.0.1:5173`) with environment variable override (`ALLOWED_ORIGINS`).
