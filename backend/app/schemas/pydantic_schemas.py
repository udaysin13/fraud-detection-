"""
VaultGuard - Pydantic Request & Response Schemas

Supports both Indian digital payment fields and legacy backward-compatible fields.
The frontend currently sends legacy fields (card_id, amount, currency, country, etc.)
and consumes PredictionResponse with {risk_score, decision, reasons, xgb_probability, anomaly_score}.
All schemas preserve backward compatibility while adding Indian payment support.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ─── Transaction Schemas ───────────────────────────────────────────────

class TransactionBase(BaseModel):
    transaction_id: str
    timestamp: str = ""
    # Legacy fields (kept for frontend compatibility)
    card_id: str = ""
    customer_id: str = ""
    merchant_id: str = ""
    merchant_category: str = ""
    amount: float = 0.0
    currency: str = "INR"
    country: str = "IN"
    billing_country: str = "IN"
    device_id: str = ""
    ip_address: str = ""
    is_new_device: int = 0
    bin_range: str = ""
    channel: str = "UPI_P2P"
    segment: str = ""
    is_fraud: Optional[int] = None
    # Indian payment fields (optional, not required by frontend)
    amount_inr: Optional[float] = None
    transaction_type: Optional[str] = None
    sender_id: Optional[str] = None
    beneficiary_id: Optional[str] = None
    sender_vpa: Optional[str] = None
    beneficiary_vpa: Optional[str] = None
    sim_change_flag: Optional[int] = 0
    ip_location_state: Optional[str] = None


class TransactionResponse(BaseModel):
    id: int
    transaction_id: str
    timestamp: str
    card_id: Optional[str] = ""
    customer_id: Optional[str] = ""
    merchant_id: Optional[str] = ""
    merchant_category: Optional[str] = ""
    amount: float
    currency: Optional[str] = "INR"
    country: Optional[str] = "IN"
    billing_country: Optional[str] = "IN"
    device_id: Optional[str] = ""
    ip_address: Optional[str] = ""
    is_new_device: int = 0
    bin_range: Optional[str] = ""
    channel: str = "UPI_P2P"
    segment: Optional[str] = ""
    is_fraud: Optional[int] = None
    risk_score: float = 0.0
    decision: str = "Allow"
    risk_category: Optional[str] = "LOW_RISK"
    reasons: List[str] = []
    status: str = "Approved"
    label_source: Optional[str] = None
    label_confirmed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TransactionDetailResponse(TransactionResponse):
    """Extended response for single transaction lookup."""
    amount_inr: Optional[float] = None
    transaction_type: Optional[str] = None
    sender_id: Optional[str] = None
    beneficiary_id: Optional[str] = None
    sender_vpa: Optional[str] = None
    beneficiary_vpa: Optional[str] = None
    sim_change_flag: Optional[int] = 0
    ip_location_state: Optional[str] = None
    model_version: Optional[str] = None
    scored_at: Optional[str] = None
    source: Optional[str] = None


class TransactionPredictRequest(BaseModel):
    """
    Accepts both legacy and Indian payment fields.
    Frontend currently sends: card_id, customer_id, merchant_id, merchant_category,
    amount, currency, country, billing_country, device_id, ip_address, is_new_device,
    bin_range, channel, segment.
    """
    # Limits to prevent oversized payloads / DoS
    transaction_id: Optional[str] = Field(None, max_length=128)
    timestamp: Optional[str] = Field(None, max_length=64)
    # Legacy fields (sent by current frontend)
    card_id: Optional[str] = Field(None, max_length=128)
    customer_id: Optional[str] = Field(None, max_length=128)
    merchant_id: Optional[str] = Field(None, max_length=128)
    merchant_category: Optional[str] = Field("p2p_transfer", max_length=64)
    amount: Optional[float] = None
    currency: str = Field("INR", max_length=10)
    country: str = Field("IN", max_length=10)
    billing_country: str = Field("IN", max_length=10)
    device_id: Optional[str] = Field("DEV_UNKNOWN", max_length=128)
    ip_address: Optional[str] = Field("0.0.0.0", max_length=64)
    is_new_device: int = 0
    bin_range: Optional[str] = Field("000000", max_length=32)
    channel: str = Field("UPI_P2P", max_length=32)
    segment: str = Field("UPI P2P", max_length=64)
    # Indian payment fields (optional)
    amount_inr: Optional[float] = None
    transaction_type: Optional[str] = Field(None, max_length=64)
    sender_id: Optional[str] = Field(None, max_length=128)
    beneficiary_id: Optional[str] = Field(None, max_length=128)
    sender_vpa: Optional[str] = Field(None, max_length=128)
    beneficiary_vpa: Optional[str] = Field(None, max_length=128)
    sim_change_flag: Optional[int] = 0
    ip_location_state: Optional[str] = Field(None, max_length=64)

    @model_validator(mode="after")
    def require_amount_and_sender(self):
        if self.amount is None and self.amount_inr is None:
            raise ValueError("Either amount or amount_inr is required for scoring.")
        if not (self.sender_id or self.customer_id or self.card_id):
            raise ValueError("One of sender_id, customer_id, or card_id is required for scoring.")
        return self

    @field_validator("amount", "amount_inr", mode="before")
    @classmethod
    def validate_amount_bounds(cls, v):
        if v is not None:
            try:
                v_float = float(v)
            except (ValueError, TypeError):
                raise ValueError("Amount must be a valid numeric value.")
            if v_float < 0:
                raise ValueError("Amount must be non-negative.")
            if v_float > 10_000_000.0:
                raise ValueError("Amount exceeds maximum allowed limit of ₹1,00,00,000 (1 Crore).")
            return v_float
        return v

    @field_validator("channel", mode="before")
    @classmethod
    def validate_channel(cls, v):
        if v is not None:
            valid_channels = {
                "UPI_P2P", "UPI_P2M_QR", "WALLET", "IMPS", "RUPAY_CARD",
                "web", "pos", "app", "mobile"
            }
            clean = str(v).strip()
            if clean not in valid_channels:
                return "UPI_P2P"
            return clean
        return "UPI_P2P"


class PredictionResponse(BaseModel):
    """
    Primary prediction response.
    Frontend consumes: risk_score, decision, reasons, xgb_probability, anomaly_score.
    Additional fields are additive and won't break existing frontend.
    """
    transaction_id: str
    risk_score: float
    decision: str
    reasons: List[str]
    xgb_probability: float
    anomaly_score: float
    # New fields (additive, backward-compatible)
    risk_category: Optional[str] = "LOW_RISK"
    model_version: Optional[str] = None
    scoring_timestamp: Optional[str] = None
    fraud_probability: Optional[float] = None
    rule_signals: List[Dict[str, str]] = []
    recommended_action: Optional[str] = None


# ─── Alert Schemas ────────────────────────────────────────────────────

class AlertBase(BaseModel):
    alert_code: str
    title: str
    segment: str
    time_ago: str
    status: str = "Monitoring"
    assignee: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    status: Optional[Literal["Monitoring", "Investigating", "Resolved", "Dismissed"]] = None
    assignee: Optional[str] = None
    severity: Optional[Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]] = None
    acknowledge: Optional[bool] = None


class AlertResponse(AlertBase):
    id: int
    acknowledged_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AlertHistoryResponse(BaseModel):
    id: int
    alert_id: int
    event_type: str
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    actor: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FraudAlertResponse(BaseModel):
    id: int
    alert_id: str
    transaction_id: str
    risk_score: float
    risk_category: str
    reasons: List[str] = []
    review_status: str = "OPEN"
    analyst: Optional[str] = None
    model_version: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ─── Entity Schemas ───────────────────────────────────────────────────

class CustomerResponse(BaseModel):
    id: int
    customer_id: str
    segment: str
    risk_level: str
    total_transactions: int
    fraud_incidents: int
    total_spend: float

    model_config = ConfigDict(from_attributes=True)


class MerchantResponse(BaseModel):
    id: int
    merchant_id: str
    category: str
    spike_ratio: float
    risk_level: str
    total_volume: float
    transaction_count: int

    model_config = ConfigDict(from_attributes=True)


class CaseResponse(BaseModel):
    id: int
    case_id: str
    title: str
    customer_id: str
    risk_score: float
    status: str
    assigned_analyst: str
    transaction_id: Optional[str] = None
    severity: Optional[str] = None
    outcome: Optional[str] = None
    closure_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


CaseStatus = Literal[
    "Open",
    "Under Review",
    "Escalated",
    "False Positive",
    "Confirmed Fraud",
    "Resolved",
]


class CaseStatusUpdate(BaseModel):
    status: CaseStatus
    closure_reason: Optional[str] = Field(None, max_length=1000)


class CaseCreate(BaseModel):
    transaction_id: str = Field(..., max_length=128)
    assigned_analyst: str = Field("Unassigned", max_length=128)
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"
    title: Optional[str] = Field(None, max_length=256)


class CaseNoteCreate(BaseModel):
    note: str = Field(..., min_length=1, max_length=4000)


class CaseNoteResponse(BaseModel):
    id: int
    case_id: str
    note: str
    author: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CaseHistoryResponse(BaseModel):
    id: int
    case_id: str
    event_type: str
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    actor: str
    detail: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RuleConfigUpdate(BaseModel):
    value: float = Field(..., ge=0, le=1_000_000)
    enabled: bool = True


class RuleConfigResponse(BaseModel):
    rule_key: str
    value: float
    enabled: bool
    version: int
    updated_by: str
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class RuleHistoryResponse(BaseModel):
    rule_key: str
    previous_value: Optional[float] = None
    new_value: float
    previous_enabled: Optional[int] = None
    new_enabled: int
    version: int
    changed_by: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CaseQueueItem(BaseModel):
    id: int
    case_id: str
    title: str
    customer_id: str
    risk_score: float
    status: str
    assigned_analyst: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FraudAlertQueueItem(BaseModel):
    id: int
    alert_id: str
    transaction_id: str
    risk_score: float
    risk_category: str
    reasons: List[str] = Field(default_factory=list)
    status: str
    analyst: Optional[str] = None
    created_at: Optional[datetime] = None
    amount_inr: Optional[float] = None
    channel: Optional[str] = None
    timestamp: Optional[str] = None
    decision: Optional[str] = None


class CaseQueueResponse(BaseModel):
    cases: List[CaseQueueItem]
    alerts: List[FraudAlertQueueItem]


# ─── Analytics Schemas ────────────────────────────────────────────────

class TopContributor(BaseModel):
    name: str
    percentage: float


class RiskScoreSummary(BaseModel):
    flagged_count: int
    pct_change: float
    top_contributors: List[TopContributor]


class TrendPoint(BaseModel):
    timestamp: str
    suspicious: int
    blocked: int
    manual_review: int


class AnalyticsOverview(BaseModel):
    total_transactions: int
    dataset_fraud_labels: int
    total_fraud_flagged: int
    total_blocked: int
    total_review: int
    total_allowed: int
    fraud_rate_pct: float
    avg_risk_score: float


# ─── Model Metrics Schemas ────────────────────────────────────────────

class ModelMetricsResponse(BaseModel):
    precision: float
    recall: float
    f1_score: float
    roc_auc: float
    confusion_matrix: List[List[int]] = []
    test_sample_count: int = 0
    fraud_count_test: int = 0
    decision_distribution: Dict[str, int] = {}
    # Extended fields
    pr_auc: Optional[float] = None
    selected_threshold: Optional[float] = None
    selected_model: Optional[str] = None
    model_version: Optional[str] = None


# ─── Health Schemas ───────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    database: str
    ml_artifacts: str
    model_version: Optional[str] = None
    transaction_count: Optional[int] = None
