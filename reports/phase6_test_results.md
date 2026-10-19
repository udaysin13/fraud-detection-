# Phase 6 Automated Test Suite & Build Verification Results

## 1. Automated Python Test Suite (`pytest`)

Execution command:
```bash
python -m pytest tests/ -v
```

### Complete Test Execution Log:
```
============================= test session starts =============================
platform win32 -- Python 3.14.4, pytest-9.1.1, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\udays\OneDrive\Attachments\Desktop\fraud
plugins: Faker-40.1.2, anyio-4.14.2
collected 47 items

tests/test_api.py::test_root_endpoint PASSED                             [  2%]
tests/test_api.py::test_health_endpoint PASSED                           [  4%]
tests/test_api.py::test_analytics_overview PASSED                        [  6%]
tests/test_api.py::test_risk_score_endpoint PASSED                       [  8%]
tests/test_api.py::test_trend_endpoint PASSED                            [ 10%]
tests/test_api.py::test_alerts_endpoints PASSED                          [ 12%]
tests/test_api.py::test_transactions_endpoints PASSED                    [ 14%]
tests/test_api.py::test_predict_endpoint_indian_upi PASSED               [ 17%]
tests/test_api.py::test_predict_endpoint_legacy_compat PASSED            [ 19%]
tests/test_api.py::test_entities_endpoints PASSED                        [ 21%]
tests/test_api.py::test_model_metrics_endpoint PASSED                    [ 23%]
tests/test_audit_security.py::test_sanitize_csv_cell_formula_injection PASSED [ 25%]
tests/test_audit_security.py::test_export_endpoint_returns_sanitized_csv PASSED [ 27%]
tests/test_audit_security.py::test_predict_rejects_negative_amount PASSED [ 29%]
tests/test_audit_security.py::test_predict_rejects_excessive_amount PASSED [ 31%]
tests/test_audit_security.py::test_predict_handles_unknown_channel_gracefully PASSED [ 34%]
tests/test_audit_security.py::test_predict_rejects_oversized_string_fields PASSED [ 36%]
tests/test_audit_security.py::test_decision_and_risk_category_boundaries PASSED [ 38%]
tests/test_audit_security.py::test_scoring_unseen_customer_without_history PASSED [ 40%]
tests/test_audit_security.py::test_scoring_zero_amount_edge_case PASSED  [ 42%]
tests/test_audit_security.py::test_is_fraud_is_never_a_model_feature PASSED [ 44%]
tests/test_audit_security.py::test_retrain_endpoint_admin_token_enforcement PASSED [ 46%]
tests/test_dataset.py::test_dataset_file_exists_and_row_count PASSED     [ 48%]
tests/test_dataset.py::test_dataset_required_columns_and_no_missing_values PASSED [ 51%]
tests/test_dataset.py::test_dataset_backward_compatibility_columns PASSED [ 53%]
tests/test_dataset.py::test_dataset_unique_transaction_ids PASSED        [ 55%]
tests/test_dataset.py::test_dataset_chronological_ordering PASSED        [ 57%]
tests/test_dataset.py::test_dataset_valid_timestamp_format PASSED        [ 59%]
tests/test_dataset.py::test_dataset_valid_channels PASSED                [ 61%]
tests/test_dataset.py::test_dataset_non_negative_inr_amounts PASSED      [ 63%]
tests/test_dataset.py::test_dataset_binary_fraud_labels PASSED           [ 65%]
tests/test_dataset.py::test_dataset_plausible_distributions PASSED       [ 68%]
tests/test_dataset.py::test_dataset_deterministic_reproducibility PASSED [ 70%]
tests/test_ml_pipeline.py::test_rolling_features_alignment_across_entities PASSED [ 72%]
tests/test_ml_pipeline.py::test_future_transactions_do_not_affect_past_features PASSED [ 74%]
tests/test_ml_pipeline.py::test_target_columns_excluded_from_model_inputs PASSED [ 76%]
tests/test_ml_pipeline.py::test_chronological_splits_preserve_ordering PASSED [ 78%]
tests/test_ml_pipeline.py::test_preprocessing_fitted_on_training_data_only PASSED [ 80%]
tests/test_ml_pipeline.py::test_threshold_selection_uses_validation_data_only PASSED [ 82%]
tests/test_ml_pipeline.py::test_evaluation_metrics_safe_for_single_class_splits PASSED [ 85%]
tests/test_ml_pipeline.py::test_training_and_prediction_feature_schemas_match PASSED [ 87%]
tests/test_ml_pipeline.py::test_saved_model_artifacts_load_and_score PASSED [ 89%]
tests/test_ml_pipeline.py::test_risk_category_mapping PASSED             [ 91%]
tests/test_scoring.py::test_just_below_threshold_check PASSED            [ 93%]
tests/test_scoring.py::test_decision_thresholds PASSED                   [ 95%]
tests/test_scoring.py::test_feature_engineering PASSED                   [ 97%]
tests/test_scoring.py::test_score_transaction PASSED                     [100%]

======================= 47 passed, 5 warnings in 9.82s ========================
```
- **Total Tests Collected**: 47
- **Passed**: 47 (100% success rate)
- **Failed**: 0
- **Duration**: 9.82 seconds

---

## 2. Frontend Production Build (`npm run build`)

Execution directory: `frontend/`  
Command: `npm run build`

### Build Output Log:
```
> vaultguard-frontend@1.0.0 build
> vite build

vite v5.4.21 building for production...
transforming...
✓ 2382 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   1.20 kB │ gzip:   0.60 kB
dist/assets/index-C8Mm_f9X.css   25.07 kB │ gzip:   5.37 kB
dist/assets/icons-JZTzsZ-j.js    19.23 kB │ gzip:   3.79 kB
dist/assets/index-CRDvlbaY.js   132.46 kB │ gzip:  26.70 kB
dist/assets/vendor-CzVCL58Z.js  163.56 kB │ gzip:  53.38 kB
dist/assets/charts-UvjncyJx.js  411.46 kB │ gzip: 110.92 kB
✓ built in 3.82s
```
- **Result**: Zero compilation errors, zero warnings.
- **Code Splitting**: Optimized vendor, chart, and icon chunks ensure all bundle files remain well within Vite's 500 kB limit.

---

## 3. Live Server Endpoint Verification

Each endpoint was exercised against the active FastAPI server running on `http://127.0.0.1:8000`:

1. `GET /api/health` ➔ **HTTP 200 OK**
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
2. `GET /api/analytics/overview` ➔ **HTTP 200 OK**
   ```json
   {
     "total_transactions": 55009,
     "total_fraud_flagged": 1301,
     "total_blocked": 1289,
     "total_review": 12,
     "total_allowed": 53708,
     "fraud_rate_pct": 2.37,
     "avg_risk_score": 2.65
   }
   ```
3. `POST /api/predict` (High-Risk SIM Swap ATO) ➔ **HTTP 200 OK**
   ```json
   {
     "transaction_id": "TXN_LIVE_1776100234",
     "risk_score": 87.0,
     "decision": "Block",
     "risk_category": "HIGH_RISK",
     "xgb_probability": 0.9856,
     "anomaly_score": 0.524,
     "reasons": [
       "High-risk device takeover: simultaneous new device & recent SIM swap",
       "Recent SIM card change detected on account",
       "First-time transfer to unfamiliar beneficiary VPA"
     ]
   }
   ```
4. `GET /api/export?type=csv` ➔ **HTTP 200 OK** (Streaming CSV with sanitized formula cells).
5. `GET /` (Frontend Dev Server at `http://localhost:3000/`) ➔ **HTTP 200 OK**.

---

## 4. Browser Automation & Environmental Checks

- **Browser Subagent Test**: The automated browser test attempted to initialize a headless Playwright browser context against `http://localhost:3000/`.
- **Environmental Result**: The underlying Playwright driver binary download returned HTTP 404 from upstream mirrors (`https://playwright.azureedge.net/builds/driver/playwright-1.57.0-win32_x64.zip`).
- **Alternative Verification**: Verified through live HTTP endpoint probing, full Vite bundle compilation, and React component code inspection of navigation, modals, drawers, and form validation. All interactive elements have descriptive IDs and accessible focus styles.
