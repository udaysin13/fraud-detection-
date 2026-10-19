# VaultGuard — Indian Digital Payment Dataset Documentation (Phase 2)

> **⚠️ EXPLICIT DISCLOSURE:**
> This dataset is **strictly synthetic** for machine learning demonstration, research, and portfolio purposes.
> It is **NOT sourced from NPCI, the Reserve Bank of India (RBI), commercial banks, payment aggregators, or actual UPI networks**.
> All user names, VPAs, account IDs, merchant identifiers, IP addresses, and transaction references are synthetically generated.
> Fraud labels represent **simulated ground truth**, not verified financial crimes.

---

## 1. Overview & Provenance

The VaultGuard Indian Digital Payment Dataset simulates **55,000 retail digital payment transactions** spanning a 30-day chronological window (`2026-09-12 12:00:41` to `2026-10-12 11:59:11`).

The dataset specifically addresses the **micro-transaction and small-value fraud landscape in India**, where payments under ₹500 represent the overwhelming majority of daily UPI volume. It captures legitimate daily consumer activities (kirana store QR scans, tea stalls, ride shares, food delivery, P2P family remittances) alongside **6 distinct synthetic fraud vectors**.

- **Total Rows**: `55,000`
- **Legitimate Transactions**: `53,790 (97.80%)`
- **Fraud Transactions**: `1,210 (2.20%)`
- **Micro-Transactions (< ₹500)**: `73.71%`
- **Small Transactions (< ₹1,000)**: `78.48%`
- **Currency**: Indian Rupee (`INR`)
- **Random Seed**: `SEED = 42` (100% deterministic reproducibility)

---

## 2. Dataset Schema & Field Definitions

The dataset includes **18 primary domain fields** representing Indian digital payment infrastructure, alongside **9 backward-compatibility alias fields** to prevent breaking downstream modules prior to Phase 3/4 refactoring.

### Primary Indian Digital Payment Schema

| Field Name | Data Type | Example Value | Description |
|---|---|---|---|
| `transaction_id` | String | `TXN_IND_000001` | Unique sequential transaction identifier (`TXN_IND_000001` to `TXN_IND_055000`). |
| `timestamp` | String (`YYYY-MM-DD HH:MM:SS`) | `2026-09-12 12:00:41` | Transaction execution timestamp, sorted chronologically. |
| `amount_inr` | Float | `249.50` | Transaction value in Indian Rupees (₹). |
| `channel` | Categorical String | `UPI_P2M_QR` | Payment channel: `UPI_P2M_QR`, `UPI_P2P`, `WALLET`, `IMPS`, `RUPAY_CARD`. |
| `transaction_type` | Categorical String | `QR_PAYMENT` | Operational transaction type: `QR_PAYMENT`, `P2P_TRANSFER`, `MERCHANT_PAYMENT`, `COLLECT_REQUEST`. |
| `sender_id` | String | `CUST_IND_1042` | Unique identifier of the initiating sender account. |
| `beneficiary_id` | String | `BEN_IND_3810` / `MERCH_IND_101` | Unique identifier of the receiving beneficiary or merchant terminal. |
| `sender_vpa` | String | `rohit.sharma42@okhdfcbank` | Virtual Payment Address (VPA) of the sender. |
| `beneficiary_vpa` | String | `chai.point@icici` | Virtual Payment Address (VPA) of the beneficiary or merchant. |
| `merchant_id` | String | `MERCH_IND_101` | Registered merchant ID (set to `NOT_APPLICABLE` for pure P2P transfers). |
| `merchant_category` | Categorical String | `food_dining` | Merchant category: `food_dining`, `kirana_grocery`, `digital_services`, `transport_travel`, `retail_fashion`, `pharmacy_health`, `electronics`, `gaming_entertainment`, `p2p_transfer`. |
| `device_id` | String | `DEV_IND_1042` | Unique simulated mobile device fingerprint identifier. |
| `is_new_device` | Integer (`0` or `1`) | `0` | Binary indicator if the transaction originated from an unrecognised device. |
| `sim_change_flag` | Integer (`0` or `1`) | `0` | Binary indicator for recent SIM card swap or port within the last 48 hours. |
| `ip_location_state` | Categorical String | `Maharashtra` | Indian State or Union Territory associated with the client IP geolocation. |
| `transaction_status` | Categorical String | `SUCCESS` | Lifecycle settlement status: `SUCCESS` (97.5%), `FAILED` (2.0%), `PENDING` (0.5%). |
| `is_fraud` | Integer (`0` or `1`) | `0` | Simulated ground-truth target label: `0` (Legitimate) or `1` (Fraudulent). |
| `fraud_pattern` | Categorical String | `Legitimate` | Specific legitimate or synthetic fraud pattern classification. |

### Backward-Compatibility Mapping

To ensure the existing pipeline, database loader, and API remain functional during transitional phases:

| Legacy Field | Mapped To / Origin | Compatibility Reason |
|---|---|---|
| `amount` | `amount_inr` | Legacy feature engineering and SQLAlchemy ORM models expect `amount`. |
| `customer_id` | `sender_id` | Legacy analytics routes join on `customer_id`. |
| `card_id` | `sender_vpa` | Legacy velocity windowing groups on `card_id`. |
| `currency` | `"INR"` | Replaces legacy foreign currencies (`USD`, `EUR`). |
| `country` | `"IN"` | Fixed country code for domestic transfers. |
| `billing_country`| `"IN"` | Fixed billing country for domestic transfers. |
| `bin_range` | Synthetic IFSC prefix (`HDFC00`, `SBIN00`, etc.) | Legacy high-risk routing tests check `bin_range`. |
| `segment` | Human-readable channel name | E.g., `UPI P2P`, `UPI P2M QR`, `Digital Wallet`. |
| `pattern` | `fraud_pattern` | Legacy reporting filters reference `pattern`. |

---

## 3. Synthetic Fraud Scenarios

The dataset models **6 realistic Indian digital payment attack patterns**:

### 1. Rapid Micro-Transfers (UPI Testing Attack)
- **Prevalence**: 242 transactions (~20.0% of fraud)
- **Average Amount**: ₹24.67 (Range: ₹1.13 – ₹48.97)
- **Characteristics**: Rapid bursts of 6–10 low-value transfers within 1–3 minutes from a single sender to various test beneficiary handles. Simulates automated credential checking before larger theft attempts.

### 2. New Beneficiary Burst
- **Prevalence**: 217 transactions (~17.9% of fraud)
- **Average Amount**: ₹2,715.31 (Range: ₹506.66 – ₹4,775.71)
- **Characteristics**: An established account abruptly initiates 4–7 high-velocity transfers to an unverified, newly added beneficiary VPA in quick succession (< 10 minutes).

### 3. SIM Change Takeover (SIM Swap + Account Drain)
- **Prevalence**: 217 transactions (~17.9% of fraud)
- **Average Amount**: ₹5,513.21 (Range: ₹2,009.97 – ₹9,498.03)
- **Characteristics**: Both `sim_change_flag = 1` and `is_new_device = 1` are triggered simultaneously. High-value funds are siphoned across UPI, IMPS, or Wallets to mule accounts within minutes of account re-authentication.

### 4. QR Merchant Velocity Spike (Mule QR / Terminal Anomaly)
- **Prevalence**: 193 transactions (~16.0% of fraud)
- **Average Amount**: ₹1,034.80 (Range: ₹254.23 – ₹1,848.30)
- **Characteristics**: A single merchant QR code suddenly experiences a 10x–20x transaction count surge (12–20 transfers within 30 minutes) from distinct customer accounts. Simulates mule merchant laundering or fake discount QR stickers.

### 5. Phishing Collect Request Spoofing
- **Prevalence**: 169 transactions (~14.0% of fraud)
- **Average Amount**: ₹4,337.16 (Range: ₹999.00 – ₹9,990.00)
- **Characteristics**: `transaction_type = 'COLLECT_REQUEST'`. Simulates deceptive collect requests disguised as refunds, lottery payouts, or marketplace approvals with psychological price anchors (₹999, ₹1,999, ₹4,999, ₹9,990).

### 6. Structuring Split Transfers (Smurfing)
- **Prevalence**: 172 transactions (~14.2% of fraud)
- **Average Amount**: ₹3,952.18 (Range: ₹990.00 – ₹9,900.00)
- **Characteristics**: Repeated transfers spaced 1–5 minutes apart kept deliberately just below surveillance alert thresholds (₹990 vs ₹1,000, ₹1,990 vs ₹2,000, ₹4,950 vs ₹5,000, ₹9,900 vs ₹10,000).

---

## 4. Legitimate vs Fraud Behavioural Overlap

To prevent simplistic rule-based memorization and ensure machine learning models learn nuanced boundaries:
- **Legitimate users use new devices**: ~6% of legitimate transactions have `is_new_device = 1` (user upgrade, multi-device usage).
- **Legitimate users port SIMs**: ~1.5% of legitimate transactions have `sim_change_flag = 1`.
- **Night-time payments**: ~12% of legitimate transfers occur during late-night hours (11 PM – 5 AM).
- **Micro-amounts are normal**: Legitimate transactions under ₹50 (e.g., ₹10 tea, ₹20 snacks) occur frequently without being flagged as fraud.

---

## 5. Dataset Generation & Verification Commands

### Regenerate the Dataset:
```bash
python ml/generate_data.py
```

### Run Dataset Quality & Schema Tests:
```bash
pytest tests/test_dataset.py -v
```

### Run Complete Test Suite:
```bash
pytest -v
```
