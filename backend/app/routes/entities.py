"""
VaultGuard - Entities API Router (Customers, Merchants, Cases)
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from backend.app.database import get_db
from backend.app.models.orm import CustomerORM, MerchantORM, CaseORM
from backend.app.schemas.pydantic_schemas import (
    CustomerResponse,
    MerchantResponse,
    CaseResponse,
)

router = APIRouter(prefix="/api", tags=["Entities"])


@router.get("/customers", response_model=List[CustomerResponse])
def get_customers(
    risk_level: Optional[str] = None,
    segment: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Retrieves paginated customer profiles with risk levels.
    """
    query = db.query(CustomerORM)
    if risk_level:
        query = query.filter(CustomerORM.risk_level == risk_level)
    if segment:
        query = query.filter(CustomerORM.segment == segment)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(CustomerORM.customer_id.ilike(search_filter))

    offset = (page - 1) * limit
    return query.order_by(CustomerORM.id.asc()).offset(offset).limit(limit).all()


@router.get("/merchants", response_model=List[MerchantResponse])
def get_merchants(
    category: Optional[str] = None,
    risk_level: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Retrieves paginated merchant risk profiles and volume spike ratios.
    """
    query = db.query(MerchantORM)
    if category:
        query = query.filter(MerchantORM.category == category)
    if risk_level:
        query = query.filter(MerchantORM.risk_level == risk_level)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(MerchantORM.merchant_id.ilike(search_filter))

    offset = (page - 1) * limit
    return query.order_by(MerchantORM.spike_ratio.desc()).offset(offset).limit(limit).all()


@router.get("/cases", response_model=List[CaseResponse])
def get_cases(
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Retrieves investigation cases created for high-risk micro-fraud incidents.
    """
    query = db.query(CaseORM)
    if status:
        query = query.filter(CaseORM.status == status)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                CaseORM.case_id.ilike(search_filter),
                CaseORM.customer_id.ilike(search_filter),
                CaseORM.title.ilike(search_filter),
            )
        )

    offset = (page - 1) * limit
    return query.order_by(CaseORM.id.desc()).offset(offset).limit(limit).all()
