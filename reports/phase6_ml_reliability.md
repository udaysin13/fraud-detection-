# Phase 6 ML Leakage, Reproducibility & Reliability Audit

## 1. Feature-by-Feature Temporal Leakage Audit

Every feature engineered in [`ml/features.py`](file:///c:/Users/udays/OneDrive/Attachments/Desktop/fraud/ml/features.py) was audited from raw transaction input through point-in-time calculation, model training, and real-time inference:

| Feature Name | Calculation Methodology | Temporal Window Guarantee | Leakage Assessment |
| :--- | :--- | :--- | :--- |
| `amount` | Transaction value normalized to INR | Available at transaction initiation | **Zero Leakage** |
| `is_small_amount` | Binary flag (`amount < 100.0`) | Instantaneous check | **Zero Leakage** |
| `is_just_below_threshold`| Proximity test (within 2% below 1k, 2k, 5k, 10k) | Instantaneous check | **Zero Leakage** |
| `hour_of_day`, `day_of_week` | Derived from transaction timestamp | Known at initiation | **Zero Leakage** |
| `is_night` | Night hours flag (23:00 - 05:00) | Known at initiation | **Zero Leakage** |
| `is_new_device` | Device authorization flag from payload | Known at transaction initiation | **Zero Leakage** |
| `sim_change_flag` | Telecom SIM-change indicator from payload | Known at transaction initiation | **Zero Leakage** |
| `high_risk_device_action` | Conjunction (`new_device & sim_change`) | Known at initiation | **Zero Leakage** |
| `time_since_last_txn` | `groupby(sender).shift(1)` | Strictly uses preceding transaction timestamp | **Zero Leakage** |
| `txn_count_1min` | `rolling("1min", closed="left")` | `closed="left"` strictly excludes current event | **Zero Leakage** |
| `txn_count_10min` | `rolling("10min", closed="left")` | `closed="left"` strictly excludes current event | **Zero Leakage** |
| `txn_count_1hour` | `rolling("1h", closed="left")` | `closed="left"` strictly excludes current event | **Zero Leakage** |
| `txn_count_24h` | `rolling("24h", closed="left")` | `closed="left"` strictly excludes current event | **Zero Leakage** |
| `amount_to_avg_ratio` | `cumsum_prior / cumcnt_prior` | Subtracts current row amount; prior-only | **Zero Leakage** |
| `is_new_beneficiary` | `groupby(sender, bene).cumcount() == 0` | Point-in-time expanding check | **Zero Leakage** |
| `merchant_spike_ratio` | `m_cnt_1h / (m_cnt_24h / 24 + 1)` | Both windows use `closed="left"` | **Zero Leakage** |
| `geo_mismatch`, `high_risk_bin`| Legacy card/geolocation checks | Known at initiation | **Zero Leakage** |
| Channel & Category One-Hots | Static one-hot encodings (18 columns) | Known at initiation | **Zero Leakage** |

### Critical Leakage Protections Confirmed:
1. **Target Columns**: `is_fraud`, `fraud_pattern`, `pattern` are strictly excluded from `FEATURE_COLUMNS`.
2. **Identification Columns**: `transaction_id` is never used as an input feature.
3. **Database Lookback**: During live scoring in `ml_service.fetch_historical_context()`, the SQL query explicitly filters `TransactionORM.timestamp < current_ts`, strictly retrieving historical transactions preceding the transaction being scored.

---

## 2. Chronological Splitting & Preprocessing Isolation

The dataset was partitioned using chronological index splitting based on timestamp ordering:

- **Training Split (70%)**: 38,500 transactions (2026-09-12 12:00:41 to 2026-10-03 14:35:08). Fraud prevalence: 2.07% (796 frauds).
- **Validation Split (15%)**: 8,250 transactions (2026-10-03 14:36:14 to 2026-10-08 00:45:56). Fraud prevalence: 2.82% (233 frauds).
- **Untouched Test Split (15%)**: 8,250 transactions (2026-10-08 00:46:26 to 2026-10-12 11:59:11). Fraud prevalence: 2.19% (181 frauds).

### Preprocessing & Threshold Verification:
- **Learned Scaler**: `StandardScaler` was fitted strictly on `X_train` (`scaler.fit_transform(X_train)`). The validation and test sets were transformed using the frozen parameters (`scaler.transform()`).
- **Isolation Forest Bounds**: Score normalization bounds (`min_val`, `max_val`) were computed solely on the training split.
- **Threshold Tuning**: The decision threshold ($T^* = 0.57$) was selected by sweeping candidates on the **Validation Split only** to maximize validation $F_1$. The test set was untouched during model training and hyperparameter selection.

---

## 3. Untouched Test Set Evaluation Metrics

Comprehensive evaluation across all benchmarked models on the 8,250 untouched test transactions:

| Model Architecture | PR-AUC | ROC-AUC | F1-Score | Recall | Precision | Selected Threshold | False Positive Rate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **XGBoost Classifier** (Selected) | **0.9986** | **1.0000** | **0.9861** | **0.9834** | **0.9889** | 0.57 | **0.02%** (2 / 8,069) |
| **Random Forest** (100 Trees, Depth 10) | 0.9969 | 0.9999 | 0.9777 | 0.9669 | 0.9887 | 0.57 | 0.02% (2 / 8,069) |
| **Logistic Regression** (Balanced Weights) | 0.9648 | 0.9979 | 0.9183 | 0.9006 | 0.9368 | 0.94 | 0.14% (11 / 8,069) |
| **Isolation Forest** (Unsupervised Baseline)| 0.5642 | 0.8959 | 0.5714 | 0.4751 | 0.7167 | 0.61 | 0.42% (34 / 8,069) |

### XGBoost Confusion Matrix Breakdown on Test Set:
- **True Negatives (TN)**: 8,067 legitimate transactions correctly allowed.
- **False Positives (FP)**: 2 legitimate transactions flagged (0.02% false-positive rate).
- **False Negatives (FN)**: 3 fraud transactions missed (1.66% false-negative rate).
- **True Positives (TP)**: 178 fraud transactions successfully detected.

---

## 4. Root-Cause Investigation: High Model Performance

The XGBoost model demonstrates unusually high precision (98.9%) and recall (98.3%). A thorough investigation confirmed the following root causes:

1. **Synthetic Generative Separability**: The dataset is synthetically generated via `ml/generate_data.py` modeling six parameterized fraud patterns (SIM Swap ATO, Rapid Micro-Transfers, Mule QR Spikes, Structuring Proximity, New Beneficiary Bursts, Collect Phishing). These scenarios have clean, high signal-to-noise signatures (e.g. `sim_change_flag=1` with `is_new_device=1` rarely occurs in benign synthetic records).
2. **Absence of Real-World Noise**: In actual commercial banking environments, legitimate users frequently change SIM cards, travel abroad, upgrade devices, and experience network retries that mimic fraud patterns. Conversely, real-world fraudsters continuously adapt their techniques to mimic normal user behavior.
3. **Absence of Label Noise**: Real-world fraud labels suffer from delayed chargeback reporting (often 30–90 days), friendly fraud, and misclassified complaints. The synthetic dataset has 100% deterministic, ground-truth label fidelity.
4. **Academic Reality**: **These high metrics demonstrate that the ML pipeline correctly learns the parameterized synthetic patterns without temporal leakage, but they do NOT constitute proof of real-world bank-grade performance.** In production banking environments, PR-AUC typically ranges between 0.35 and 0.75.

---

## 5. Edge-Case ML Robustness Testing

The scoring engine was subjected to edge-case stress tests via [`tests/test_audit_security.py`](file:///c:/Users/udays/OneDrive/Attachments/Desktop/fraud/tests/test_audit_security.py):

1. **Unseen Customers**: Evaluated a transaction with a customer ID that has zero prior database records. The engine fell back to standalone feature extraction and scored cleanly without raising missing-value errors.
2. **Zero-Amount Transactions**: Evaluated ₹0.0 transactions; ratios and flags handled the boundary without zero-division errors.
3. **Missing Historical Data**: Database lookback failures trigger graceful degradation to standalone extraction with baseline priors.
4. **Extreme Amounts**: Amounts exceeding ₹1 Crore are caught by API boundary validation, while amounts up to the ceiling are scaled without numeric overflow.

---

## 6. SHAP Explanations Audit

The SHAP explainability engine was audited in [`ml/predict.py`](file:///c:/Users/udays/OneDrive/Attachments/Desktop/fraud/ml/predict.py):
- **Model Correspondence**: `shap.TreeExplainer(xgb_model)` is fitted on the exact serialized XGBoost model artifact used for scoring.
- **Dynamic Explanations**: SHAP attribution values are computed in real time for each incoming feature vector.
- **Top Evidence Signals**: Explanations highlight the top 3 positive feature contributions pushing the prediction toward suspicion (e.g., SIM change, velocity burst, structuring proximity).
- **Causality Disclosure**: Explanations are statistical feature attributions reflecting model score contributions, not legally proven causes of fraud.
