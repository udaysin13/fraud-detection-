"""
VaultGuard - Pydantic Request & Response Schemas
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, ConfigDict


class TransactionBase(BaseModel):
    transaction_id: str
    timestamp: str
    card_id: str
    customer_id: str
    merchant_id: str
    merchant_category: str
    amount: float
    currency: str
    country: str
    billing_country: str
    device_id: str
    ip_address: str
    is_new_device: int = 0
    bin_range: str
    channel: str
    segment: str
    is_fraud: Optional[int] = 0


class TransactionResponse(TransactionBase):
    id: int
    risk_score: float
    decision: str
    reasons: List[str]
    status: str

    model_config = ConfigDict(from_attributes=True)


class TransactionPredictRequest(BaseModel):
    transaction_id: Optional[str] = "TXN_LIVE_REQ"
    timestamp: Optional[str] = None
    card_id: str
    customer_id: str
    merchant_id: str
    merchant_category: str
    amount: float
    currency: str = "USD"
    country: str
    billing_country: str
    device_id: str
    ip_address: str
    is_new_device: int = 0
    bin_range: str
    channel: str = "web"
    segment: str = "AS Cards"


class PredictionResponse(BaseModel):
    transaction_id: str
    risk_score: float
    decision: str
    reasons: List[str]
    xgb_probability: float
    anomaly_score: float


class AlertBase(BaseModel):
    alert_code: str
    title: str
    segment: str
    time_ago: str
    status: str = "Monitoring"
    assignee: str


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    status: Optional[str] = None
    assignee: Optional[str] = None


class AlertResponse(AlertBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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


class ModelMetricsResponse(BaseModel):
    precision: float
    recall: float
    f1_score: float
    roc_auc: float
    confusion_matrix: List[List[int]]
    test_sample_count: int
    fraud_count_test: int
    decision_distribution: Dict[str, int]
