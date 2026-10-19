# VaultGuard REST API Reference

The VaultGuard backend provides RESTful endpoints built with FastAPI and an asynchronous WebSocket stream for live telemetry.

- **Base URL**: `http://127.0.0.1:8000`
- **Interactive Swagger Documentation**: `http://127.0.0.1:8000/docs`
- **ReDoc Documentation**: `http://127.0.0.1:8000/redoc`

---

## 1. System Health & Infrastructure

### `GET /`
- **Description**: Root status verification endpoint.
- **Headers**: None required.
- **Response** (`200 OK`):
  ```json
  {
    "status": "online",
    "service": "VaultGuard Fraud Detection Backend",
    "version": "1.0.0",
    "documentation": "/docs"
  }
  ```

### `GET /api/health`
- **Description**: System health check verifying database connectivity, total transaction count, and serialized ML model artifact readiness.
- **Headers**: None required.
- **Response** (`200 OK`):
  ```json
  {
    "status": "healthy",
    "service": "VaultGuard Fraud Detection Backend",
    "version": "1.0.0",
    "database": "connected",
    "ml_artifacts": "ready",
    "model_version": "v1.0.0-xgb-iso-hybrid",
    "transaction_count": 55009
  }
  ```

---

## 2. Analytics & Reporting

### `GET /api/analytics/overview`
- **Description**: Computes high-level aggregated fraud statistics across all transactions in the database.
- **Headers**: None required.
- **Response** (`200 OK`):
  ```json
  {
    "total_transactions": 55009,
    "dataset_fraud_labels": 1301,
    "total_fraud_flagged": 1301,
    "total_blocked": 1289,
    "total_review": 12,
    "total_allowed": 53708,
    "fraud_rate_pct": 2.37,
    "avg_risk_score": 2.65
  }
  ```
  `dataset_fraud_labels` counts stored ground-truth labels (`is_fraud = 1`). `total_fraud_flagged` counts scored records with risk score above 40; the metrics are not interchangeable. Example counts vary with the local database.

### `GET /api/risk-score`
- **Description**: Returns summary count of transactions with risk score $> 40$, percentage prevalence, and top contributing risk reasons.
- **Headers**: None required.
- **Response** (`200 OK`):
  ```json
  {
    "flagged_count": 1301,
    "pct_change": 2.4,
    "top_contributors": []
  }
  ```
  Contributors are derived from reason strings stored on flagged transactions. The list is empty if there are no stored reasons; the endpoint does not substitute a sample distribution.

### `GET /api/trend`
- **Description**: Returns time-series trend aggregation for suspicious, blocked, and manual review transactions.
- **Query Parameters**:
  - `range` (*string, optional*): Time range window (`24h`, `7d`, or `30d`). Default: `24h`.
- **Response** (`200 OK`):
  ```json
  [
    {
      "timestamp": "2026-10-12 11:00",
      "suspicious": 4,
      "blocked": 4,
      "manual_review": 0
    }
  ]
  ```

### `GET /api/export`
- **Description**: Streams transaction data as a downloadable CSV file with sanitization against formula injection (CWE-1236).
- **Query Parameters**:
  - `type` (*string, required*): Format identifier (`csv`).
- **Response** (`200 OK`):
  - `Content-Type`: `text/csv; charset=utf-8`
  - `Content-Disposition`: `attachment; filename="vaultguard_transactions.csv"`

---

## 3. Real-Time Scoring & Predictions

### `POST /api/predict`
- **Description**: Evaluates an incoming payment transaction using the hybrid ML pipeline (XGBoost + Isolation Forest + TreeSHAP), pulls bounded historical sender context from the database, persists the scored transaction, and auto-generates alerts if the decision is `Block` or `Manual Review`.
- **Headers**:
  - `Content-Type: application/json`
- **Request Body** (`TransactionPredictRequest`):
  ```json
  {
    "transaction_id": "TXN_LIVE_90210",
    "amount_inr": 8500.0,
    "channel": "UPI_P2P",
    "transaction_type": "P2P_TRANSFER",
    "sender_id": "CUST_IND_9099",
    "sender_vpa": "victim.user@okhdfcbank",
    "beneficiary_id": "BEN_IND_3021",
    "beneficiary_vpa": "mule.account@paytm",
    "device_id": "DEV_NEW_9999",
    "is_new_device": 1,
    "sim_change_flag": 1,
    "ip_location_state": "Maharashtra"
  }
  ```
- **Validation Rules**:
  - `amount_inr` / `amount`: Must be $\ge 0.0$ and $\le ₹10,000,000.0$ (1 Crore).
  - `channel`: Must be one of `UPI_P2P`, `UPI_P2M_QR`, `WALLET`, `IMPS`, `RUPAY_CARD`, `web`, `pos`, `app`, `mobile`.
  - String fields: Maximum 128 characters.
- **Response** (`200 OK`):
  ```json
  {
    "transaction_id": "TXN_LIVE_90210",
    "risk_score": 87.0,
    "decision": "Block",
    "risk_category": "HIGH_RISK",
    "reasons": [
      "High-risk device takeover: simultaneous new device & recent SIM swap",
      "Recent SIM card change detected on account",
      "First-time transfer to unfamiliar beneficiary VPA"
    ],
    "xgb_probability": 0.9856,
    "anomaly_score": 0.524,
    "fraud_probability": 0.9856,
    "model_version": "v1.0.0-xgb-iso-hybrid",
    "scoring_timestamp": "2026-10-13T16:15:30.123456Z"
  }
  ```
- **Error Responses**:
  - `422 Unprocessable Entity`: Negative amount, excessive amount, or invalid field types.

---

## 4. Transactions Explorer

### `GET /api/transactions`
- **Description**: Returns paginated transactions with multi-attribute filtering.
- **Query Parameters**:
  - `page` (*integer, ge=1*): Page number (default: `1`).
  - `limit` (*integer, ge=1, le=100*): Page size (default: `50`).
  - `decision` (*string, optional*): Filter by decision (`Allow`, `Manual Review`, `Block`).
  - `risk_category` (*string, optional*): Filter by risk tier (`LOW_RISK`, `REVIEW`, `HIGH_RISK`).
  - `channel` (*string, optional*): Payment channel filter.
  - `search` (*string, optional*): Substring search across Txn ID, Sender, Beneficiary, VPA.
  - `min_amount`, `max_amount` (*float, optional*): Amount filter.
- **Response** (`200 OK`):
  ```json
  [
    {
      "id": 55009,
      "transaction_id": "TXN_LIVE_90210",
      "timestamp": "2026-10-13 16:15:30",
      "amount": 8500.0,
      "currency": "INR",
      "channel": "UPI_P2P",
      "risk_score": 87.0,
      "decision": "Block",
      "risk_category": "HIGH_RISK",
      "reasons": [
        "High-risk device takeover: simultaneous new device & recent SIM swap"
      ],
      "status": "Declined"
    }
  ]
  ```

### `GET /api/transactions/{transaction_id}`
- **Description**: Retrieves full metadata for a specific transaction by its unique identifier.
- **Response** (`200 OK`): Returns extended `TransactionDetailResponse` including VPA routing, SIM change flags, and device identifiers.
- **Error Responses**:
  - `404 Not Found`: Transaction ID does not exist.

---

## 5. Alerts & Incident Management

### `GET /api/alerts`
- **Description**: Returns paginated security incident alerts.
- **Query Parameters**: `status` (`Monitoring`, `Investigating`, `Resolved`), `segment`, `search`, `page`, `limit`.
- **Response** (`200 OK`):
  ```json
  [
    {
      "id": 1,
      "alert_code": "ALT-001234",
      "title": "Device Takeover / SIM Swap on TXN_LIVE_90210",
      "segment": "UPI Payments",
      "time_ago": "Just now",
      "status": "Investigating",
      "assignee": "Risk Engine"
    }
  ]
  ```

### `POST /api/alerts`
- **Description**: Creates a new security alert manually.
- **Response** (`201 Created`): Returns created `AlertResponse`.

### `PATCH /api/alerts/{alert_id}`
- **Description**: Updates an existing alert's status or assigned analyst.
- **Request Body**:
  ```json
  {
    "status": "Resolved",
    "assignee": "Priya Nair"
  }
  ```
- **Response** (`200 OK`): Returns updated `AlertResponse`.
- **Error Responses**:
  - `404 Not Found`: Alert ID does not exist.

---

## 6. Entity Intelligence (Customers, Merchants, Cases)

### `GET /api/customers`
- **Description**: Retrieves paginated customer profiles with risk levels and cumulative spend.
- **Query Parameters**: `risk_level` (`Low`, `Medium`, `High`), `search`, `page`, `limit`.

### `GET /api/merchants`
- **Description**: Retrieves paginated merchant profiles with hourly volume spike ratios.
- **Query Parameters**: `category`, `risk_level`, `search`, `page`, `limit`.

### `GET /api/cases`
- **Description**: Retrieves analyst investigation case files.
- **Query Parameters**: `status` (`Open`, `In Review`, `Closed`), `search`, `page`, `limit`.

### `GET /api/cases/active`
- **Description**: Returns active persisted cases and fraud alerts. Fraud alert rows include transaction amount, channel, timestamp, risk score, and stored reason strings when a matching transaction exists. Simulated WebSocket events are not included.
- **Query Parameters**: `search`, `limit` (1-100).
- **Response** (`200 OK`): `{ "cases": [...], "alerts": [...] }`.
- Terminal outcomes (`False Positive`, `Confirmed Fraud`, `Resolved`, and dismissed alerts) are excluded.

### `PATCH /api/cases/{case_id}/status`
- **Description**: Updates a persisted investigation case status and commits the change.

### `PATCH /api/fraud-alerts/{alert_id}/status`
- **Description**: Updates a persisted fraud-alert review status and commits the change.
- **Request Body**:
  ```json
  { "status": "Under Review" }
  ```
- **Allowed statuses**: `Open`, `Under Review`, `Escalated`, `False Positive`, `Confirmed Fraud`, `Resolved`.
- Invalid statuses return `422`; missing records return `404`; database write errors are rolled back and return `500`.

---

## 7. Model Governance & Administrative Controls

### `GET /api/models/metrics`
- **Description**: Returns serialized model performance metrics, confusion matrix, and chronological dataset split summary.
- **Response** (`200 OK`):
  ```json
  {
    "precision": 0.9889,
    "recall": 0.9834,
    "f1_score": 0.9861,
    "roc_auc": 1.0,
    "pr_auc": 0.9986,
    "confusion_matrix": [[8067, 2], [3, 178]],
    "test_sample_count": 8250,
    "fraud_count_test": 181,
    "selected_threshold": 0.57,
    "selected_model": "xgboost"
  }
  ```

### `POST /api/models/retrain`
- **Description**: Triggers retraining of the XGBoost and Isolation Forest pipeline on the dataset and reloads the memory cache.
- **Headers**:
  - `X-Admin-Token` (*string, optional*): Required when `VAULTGUARD_ADMIN_TOKEN` is configured in the backend environment.
- **Response** (`200 OK`): Returns updated `ModelMetricsResponse`.
- **Error Responses**:
  - `401 Unauthorized`: Token is missing or invalid when `VAULTGUARD_ADMIN_TOKEN` is enforced.
  - `409 Conflict`: Retraining is already in progress (concurrency lock).

---

## 8. WebSocket Live Telemetry

### `WS /ws/transactions`
- **Description**: Live WebSocket stream broadcasting simulated Indian payment transactions scored on-the-fly.
- **Broadcast Frequency**: Approximately every 3 seconds.
- **Storage Behavior**: Strictly decoupled from persistent database tables (zero database writes).
- **Message Payload**:
  ```json
  {
    "transaction_id": "TXN_WS_123456",
    "timestamp": "2026-10-13 16:20:00",
    "amount_inr": 2450.0,
    "channel": "UPI_P2P",
    "sender_id": "CUST_IND_4012",
    "sender_vpa": "rohan.patel22@okhdfcbank",
    "beneficiary_id": "BEN_IND_1092",
    "beneficiary_vpa": "priya.nair44@paytm",
    "risk_score": 12.0,
    "decision": "Allow",
    "risk_category": "LOW_RISK",
    "reasons": [
      "Verified customer baseline parameters",
      "Established beneficiary history"
    ],
    "status": "Approved",
    "is_simulated": true,
    "source": "websocket_simulation"
  }
  ```
