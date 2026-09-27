# VaultGuard — Small Transaction Fraud Detection System

![VaultGuard Banner](https://img.shields.io/badge/VaultGuard-v1.0.0-orange?style=for-the-badge&logo=shield)
![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=for-the-badge&logo=fastapi)
![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react)
![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-3.4-38B2AC?style=for-the-badge&logo=tailwind-css)

**VaultGuard** is an enterprise-grade, real-time micro-transaction fraud detection system designed to detect and block sub-$50 fraud attacks: card testing, micro-payment velocity surges, regulatory structuring ($9.90 / $49.50 limits), geographic mismatches, high-risk BIN usage, and merchant volume anomalies.

---

## 🌟 Key Features

- ⚡ **Hybrid Machine Learning Engine**: Combines **Supervised XGBoost Classifier** (75% weight) with **Unsupervised Isolation Forest** (25% weight) to score transactions from **0 to 100**.
- 🔍 **Real-Time SHAP Explainability**: Returns the **top 3 human-readable risk reasons** for every flagged transaction (e.g. *"Card testing pattern"*, *"Geo mismatch"*, *"New device surge"*).
- 📡 **Live WebSocket Telemetry**: Real-time streaming WebSocket feed (`ws://localhost:8000/ws/transactions`) broadcasting newly scored transactions every 3 seconds.
- 🎯 **Automated Decision Engine**:
  - **0 – 40**: `Allow` (Green)
  - **41 – 70**: `Manual Review` (Amber)
  - **71 – 100**: `Block` (Rose)
- 📊 **Executive Dashboard**: Donut health charts, time-series velocity trend lines, interactive alert drawers, customer risk levels, and merchant volume spike tracking.

---

## 📁 Project Folder Structure

```text
fraud-detection-small-transactions/
├── data/
│   └── transactions.csv            # 55,000 synthetic transaction dataset (~90% < $50, ~2% fraud)
├── ml/
│   ├── saved_models/              # Serialized XGBoost, Isolation Forest, SHAP, and metrics.json
│   ├── generate_data.py           # Synthetic dataset generator with 7 micro-fraud patterns
│   ├── features.py                # Domain feature engineering (velocity, z-scores, device count)
│   ├── train.py                   # Model training script with class weighting & evaluation
│   ├── predict.py                 # Real-time scoring function with SHAP explainability
│   └── requirements.txt           # Machine learning dependencies
├── backend/
│   ├── vaultguard.db              # SQLite database (auto-seeded on first launch)
│   ├── requirements.txt           # FastAPI & SQLAlchemy backend dependencies
│   └── app/
│       ├── main.py                # FastAPI entrypoint & CORS middleware
│       ├── database.py            # SQLAlchemy SQLite connection session manager
│       ├── models/
│       │   └── orm.py             # ORM models (Transactions, Alerts, Customers, Merchants, Cases)
│       ├── schemas/
│       │   └── pydantic_schemas.py# Request/Response validation schemas
│       ├── services/
│       │   ├── data_loader.py     # Database seeder & bulk dataset importer
│       │   └── ml_service.py      # Python ML service wrapper
│       └── routes/
│           ├── analytics.py       # GET /api/risk-score, /api/trend, /api/export
│           ├── alerts.py          # GET, POST, PATCH /api/alerts
│           ├── transactions.py    # GET /api/transactions, POST /api/predict
│           ├── entities.py        # GET /api/customers, /api/merchants, /api/cases
│           ├── models_api.py      # GET /api/models/metrics, POST /api/models/retrain
│           └── websocket.py       # WebSocket /ws/transactions real-time feed
├── frontend/
│   ├── package.json               # React, Vite, Tailwind, Recharts, Lucide-react dependencies
│   ├── vite.config.js             # Vite dev server configuration
│   ├── tailwind.config.js         # Custom VaultGuard design tokens & colors
│   ├── index.html                 # Main HTML with Google Fonts (Outfit & Inter)
│   └── src/
│       ├── index.css              # Custom scrollbars & global styles
│       ├── main.jsx               # React DOM root entrypoint
│       ├── App.jsx                # React Router DOM navigation router
│       ├── context/
│       │   └── FilterContext.jsx  # Global filter state & WebSocket streaming context
│       ├── components/
│       │   ├── Header.jsx         # VaultGuard Header with search, filters & alert badge
│       │   ├── Sidebar.jsx        # Collapsible dark navigation sidebar
│       │   ├── CreateAlertModal.jsx# Create alert modal popup
│       │   ├── AlertDetailDrawer.jsx# Slide-over alert detail drawer
│       │   └── Layout.jsx         # Main application shell
│       └── pages/
            ├── Overview.jsx       # Risk Overview dashboard with donut chart & Recharts timeline
            ├── Transactions.jsx   # Live transaction ledger & WebSocket streaming ticker
            ├── FraudDetection.jsx # Interactive ML scoring simulator with SHAP gauge
            ├── Investigations.jsx # Analyst case management & case notes
            ├── Customers.jsx      # Customer risk level profiles
            ├── Merchants.jsx      # Merchant volume spike ratio monitoring
            ├── RulesModels.jsx    # Model metrics, confusion matrix & rule toggles
            ├── Reports.jsx        # Telemetry reports & CSV data exporter
            ├── Compliance.jsx     # AML structuring & SAR compliance checks
            └── AdminPanel.jsx     # Master system controls & API keys
├── tests/
│   ├── test_scoring.py            # Unit tests for feature engineering & model scoring
│   └── test_api.py                # Integration tests for FastAPI endpoints
└── README.md
```

---

## 🛠️ Setup Instructions

### 1. Prerequisites
- **Python 3.10+**
- **Node.js 18+** & **npm 9+**

### 2. Machine Learning & Backend Setup
```bash
# Install Python dependencies
pip install -r ml/requirements.txt
pip install -r backend/requirements.txt
```

### 3. Frontend Setup
```bash
# Install React dependencies
cd frontend
npm install
cd ..
```

---

## 🚀 Sequential Execution Order

Follow these steps in order to initialize the dataset, train models, and run the system:

```bash
# Step 1: Generate Synthetic Dataset (55,000 rows in data/transactions.csv)
python ml/generate_data.py

# Step 2: Train Machine Learning Pipeline (Saves models & metrics in ml/saved_models/)
python ml/train.py

# Step 3: Run Automated Test Suite (Optional verification)
pytest

# Step 4: Start FastAPI Backend Server (Runs on http://localhost:8000)
python -m uvicorn backend.app.main:app --reload --port 8000

# Step 5: Start Frontend Dev Server (in a new terminal window)
cd frontend
npm run dev
```

Open **`http://localhost:3000`** in your browser to access the **VaultGuard** application.

---

## 🔗 API Endpoint Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | API Health & status check |
| `GET` | `/docs` | Interactive Swagger UI Documentation |
| `GET` | `/api/risk-score` | Summary metrics: total flagged count, % change, top contributors |
| `GET` | `/api/trend?range=24h` | Time series trend points (`24h`, `7d`, `30d`) |
| `GET` | `/api/alerts` | Paginated alerts feed (supports `status`, `segment`, `search`) |
| `POST` | `/api/alerts` | Create a new security alert |
| `PATCH` | `/api/alerts/{id}` | Update alert status or assigned analyst |
| `GET` | `/api/transactions` | Paginated transactions ledger (filters: `decision`, `segment`, `search`) |
| `POST` | `/api/predict` | Score a real-time transaction payload with hybrid ML engine |
| `GET` | `/api/customers` | Customer profiles & risk levels |
| `GET` | `/api/merchants` | Merchant risk profiles & volume spike ratios |
| `GET` | `/api/cases` | Analyst investigation cases |
| `GET` | `/api/models/metrics` | Model evaluation metrics & confusion matrix |
| `POST` | `/api/models/retrain` | Trigger pipeline retraining on latest dataset |
| `GET` | `/api/export?type=csv` | Download scored transaction ledger as CSV attachment |
| `WS` | `/ws/transactions` | WebSocket stream emitting a newly scored transaction every 3s |

---

## 🤖 Model Explanation & Performance Metrics

VaultGuard uses a **hybrid ensemble architecture**:
1. **Supervised XGBoost Classifier** (`scale_pos_weight=49.0`): Trained on 34 domain-engineered features (rolling 1min/10min/1h velocity counts, historical card z-scores, device count in 24h, structuring indicators, geo mismatch flags).
2. **Unsupervised Isolation Forest** (`contamination=0.02`): Detects novel out-of-distribution anomaly patterns without ground truth labels.
3. **Hybrid Score Fusion**: 
   $$\text{Risk Score} = \text{Clip}\left(\left(0.75 \cdot P_{\text{xgb}} + 0.25 \cdot S_{\text{iso}}\right) \times 100, 0, 100\right)$$

### Evaluation Results (11,000 Test Set Transactions)

- **Precision**: `62.83%` (minimizes false positive customer friction on small charges)
- **Recall**: `96.82%` (**catches 96.8% of all micro-fraud attacks**)
- **F1 Score**: `76.21%`
- **ROC-AUC**: `0.9977`
- **Confusion Matrix**:
  - True Negatives (Legitimate): `10,654`
  - False Positives (Manual Review): `126`
  - False Negatives (Missed Fraud): `7`
  - True Positives (Blocked Fraud): `213`

---

## ⚡ Single Command Quick-Start

To run the entire VaultGuard system from scratch:

```bash
python ml/generate_data.py && python ml/train.py && python -m uvicorn backend.app.main:app --reload --port 8000
```
*(Then run `cd frontend && npm run dev` in a secondary terminal to launch the interface).*

---

## 🔮 Future Improvements

- 🕸️ **Graph Neural Networks (GNN)**: Implement PyTorch Geometric graph networks to map ring-based card testing across shared device fingerprints.
- ⚡ **Apache Kafka Integration**: Replace simulated WebSocket streamer with Kafka topic consumers for high-throughput payment gateway ingestion (>10,000 TPS).
- 📜 **Automated SAR Filing**: Direct integration with FinCEN API for automatic e-filing of Suspicious Activity Reports on blocked structuring clusters.

---

### Developed for VaultGuard Micro-Transaction Security
