"""
VaultGuard - SQLAlchemy ORM Models

Supports both Indian digital payment schema (Phase 2+) and legacy backward-compatible fields.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, Index
from backend.app.database import Base


class TransactionORM(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    transaction_id = Column(String, unique=True, index=True, nullable=False)
    timestamp = Column(String, index=True, nullable=False)

    # Indian digital payment fields (primary)
    amount_inr = Column(Float, nullable=True)
    channel = Column(String, nullable=False, default="UPI_P2P")
    transaction_type = Column(String, nullable=True)
    sender_id = Column(String, index=True, nullable=True)
    beneficiary_id = Column(String, index=True, nullable=True)
    sender_vpa = Column(String, nullable=True)
    beneficiary_vpa = Column(String, nullable=True)
    merchant_id = Column(String, index=True, nullable=True)
    merchant_category = Column(String, nullable=True)
    device_id = Column(String, nullable=True)
    is_new_device = Column(Integer, default=0)
    sim_change_flag = Column(Integer, default=0)
    ip_location_state = Column(String, nullable=True)
    transaction_status = Column(String, default="SUCCESS")

    # Legacy backward-compatible fields (kept for frontend compatibility)
    card_id = Column(String, index=True, nullable=True)
    customer_id = Column(String, index=True, nullable=True)
    amount = Column(Float, nullable=False, default=0.0)
    currency = Column(String, nullable=True, default="INR")
    country = Column(String, nullable=True, default="IN")
    billing_country = Column(String, nullable=True, default="IN")
    ip_address = Column(String, nullable=True)
    bin_range = Column(String, nullable=True)
    segment = Column(String, nullable=True)

    # Labels — only for offline labeled data, never used as inference input
    # NULL means no verified outcome exists; model predictions never populate this.
    is_fraud = Column(Integer, nullable=True, default=None)
    fraud_pattern = Column(String, nullable=True)
    label_source = Column(String, nullable=True)
    label_confirmed_at = Column(DateTime, nullable=True)

    # Scoring results
    risk_score = Column(Float, default=0.0)
    decision = Column(String, default="Allow")
    risk_category = Column(String, default="LOW_RISK")
    reasons = Column(Text, default="[]")  # JSON encoded list of reason strings
    status = Column(String, default="Approved")
    model_version = Column(String, nullable=True)
    scored_at = Column(String, nullable=True)

    # Source tracking
    source = Column(String, default="seed")  # "seed" for CSV import, "api" for live predictions

    __table_args__ = (
        Index("ix_txn_sender_timestamp", "sender_id", "timestamp"),
        Index("ix_txn_customer_timestamp", "customer_id", "timestamp"),
        Index("ix_txn_decision", "decision"),
    )


class FraudAlertORM(Base):
    __tablename__ = "fraud_alerts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    alert_id = Column(String, unique=True, index=True, nullable=False)
    transaction_id = Column(String, index=True, nullable=False)
    risk_score = Column(Float, nullable=False)
    risk_category = Column(String, nullable=False)
    reasons = Column(Text, default="[]")  # JSON encoded
    review_status = Column(String, default="OPEN", index=True)  # OPEN, UNDER_REVIEW, RESOLVED, DISMISSED
    analyst = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    model_version = Column(String, nullable=True)


class AlertORM(Base):
    """Legacy alerts table — preserved for backward compatibility with existing frontend/tests."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    alert_code = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    segment = Column(String, index=True, nullable=False)
    time_ago = Column(String, nullable=False)
    status = Column(String, index=True, default="Monitoring")
    assignee = Column(String, nullable=False)
    severity = Column(String, index=True, default="MEDIUM")
    acknowledged_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))


class AlertHistoryORM(Base):
    """Append-only lifecycle events for operational alerts."""
    __tablename__ = "alert_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    alert_id = Column(Integer, index=True, nullable=False)
    event_type = Column(String, nullable=False)
    previous_status = Column(String, nullable=True)
    new_status = Column(String, nullable=True)
    actor = Column(String, nullable=False, default="system")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ModelMetadataORM(Base):
    __tablename__ = "model_metadata"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    model_name = Column(String, nullable=False, index=True)
    model_version = Column(String, unique=True, nullable=False)
    training_timestamp = Column(String, nullable=True)
    selected_threshold = Column(Float, nullable=True)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    roc_auc = Column(Float, nullable=True)
    pr_auc = Column(Float, nullable=True)
    test_sample_count = Column(Integer, nullable=True)
    fraud_count_test = Column(Integer, nullable=True)
    feature_count = Column(Integer, nullable=True)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class CustomerORM(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    customer_id = Column(String, unique=True, index=True, nullable=False)
    segment = Column(String, nullable=False)
    risk_level = Column(String, default="Low")
    total_transactions = Column(Integer, default=0)
    fraud_incidents = Column(Integer, default=0)
    total_spend = Column(Float, default=0.0)


class MerchantORM(Base):
    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    merchant_id = Column(String, unique=True, index=True, nullable=False)
    category = Column(String, nullable=False)
    spike_ratio = Column(Float, default=1.0)
    risk_level = Column(String, default="Low")
    total_volume = Column(Float, default=0.0)
    transaction_count = Column(Integer, default=0)


class CaseORM(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    case_id = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    customer_id = Column(String, nullable=False)
    risk_score = Column(Float, default=0.0)
    status = Column(String, default="Open")
    assigned_analyst = Column(String, default="Unassigned")
    transaction_id = Column(String, nullable=True)
    severity = Column(String, default="MEDIUM", index=True)
    outcome = Column(String, nullable=True)
    closure_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("uq_cases_transaction_id", "transaction_id", unique=True),
    )


class CaseNoteORM(Base):
    __tablename__ = "case_notes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    case_id = Column(String, index=True, nullable=False)
    note = Column(Text, nullable=False)
    author = Column(String, nullable=False, default="system")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class CaseHistoryORM(Base):
    __tablename__ = "case_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    case_id = Column(String, index=True, nullable=False)
    event_type = Column(String, nullable=False)
    previous_status = Column(String, nullable=True)
    new_status = Column(String, nullable=True)
    actor = Column(String, nullable=False, default="system")
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class RuleConfigORM(Base):
    """Persisted override for a bounded set of supported risk-rule thresholds."""
    __tablename__ = "rule_configs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    rule_key = Column(String, unique=True, index=True, nullable=False)
    value = Column(Float, nullable=False)
    enabled = Column(Integer, nullable=False, default=1)
    version = Column(Integer, nullable=False, default=1)
    updated_by = Column(String, nullable=False, default="system")
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))


class RuleHistoryORM(Base):
    __tablename__ = "rule_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    rule_key = Column(String, index=True, nullable=False)
    previous_value = Column(Float, nullable=True)
    new_value = Column(Float, nullable=False)
    previous_enabled = Column(Integer, nullable=True)
    new_enabled = Column(Integer, nullable=False)
    version = Column(Integer, nullable=False)
    changed_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
