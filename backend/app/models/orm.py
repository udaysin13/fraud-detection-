"""
VaultGuard - SQLAlchemy ORM Models
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from backend.app.database import Base


class TransactionORM(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    transaction_id = Column(String, unique=True, index=True, nullable=False)
    timestamp = Column(String, index=True, nullable=False)
    card_id = Column(String, index=True, nullable=False)
    customer_id = Column(String, index=True, nullable=False)
    merchant_id = Column(String, index=True, nullable=False)
    merchant_category = Column(String, index=True, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, nullable=False)
    country = Column(String, nullable=False)
    billing_country = Column(String, nullable=False)
    device_id = Column(String, nullable=False)
    ip_address = Column(String, nullable=False)
    is_new_device = Column(Integer, default=0)
    bin_range = Column(String, nullable=False)
    channel = Column(String, nullable=False)
    segment = Column(String, index=True, nullable=False)
    is_fraud = Column(Integer, default=0)

    # Scored fields
    risk_score = Column(Float, default=0.0)
    decision = Column(String, default="Allow")
    reasons = Column(Text, default="[]")  # JSON encoded list of reason strings
    status = Column(String, default="Approved")


class AlertORM(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    alert_code = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    segment = Column(String, index=True, nullable=False)
    time_ago = Column(String, nullable=False)
    status = Column(String, index=True, default="Monitoring")
    assignee = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


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
    created_at = Column(DateTime, default=datetime.utcnow)
