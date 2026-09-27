"""
VaultGuard - Alerts API Endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from backend.app.database import get_db
from backend.app.models.orm import AlertORM
from backend.app.schemas.pydantic_schemas import AlertResponse, AlertCreate, AlertUpdate

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


@router.get("", response_model=List[AlertResponse])
def get_alerts(
    status: Optional[str] = None,
    segment: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Retrieves paginated alerts with optional filters (status, segment, search).
    """
    query = db.query(AlertORM)

    if status:
        query = query.filter(AlertORM.status == status)
    if segment:
        query = query.filter(AlertORM.segment == segment)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                AlertORM.title.ilike(search_filter),
                AlertORM.alert_code.ilike(search_filter),
                AlertORM.assignee.ilike(search_filter),
            )
        )

    offset = (page - 1) * limit
    alerts = query.order_by(AlertORM.id.desc()).offset(offset).limit(limit).all()
    return alerts


@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
def create_alert(alert_in: AlertCreate, db: Session = Depends(get_db)):
    """
    Creates a new system or analyst security alert.
    """
    existing = (
        db.query(AlertORM)
        .filter(AlertORM.alert_code == alert_in.alert_code)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Alert with code '{alert_in.alert_code}' already exists.",
        )

    db_alert = AlertORM(**alert_in.model_dump())
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert


@router.patch("/{alert_id}", response_model=AlertResponse)
def update_alert(
    alert_id: int, alert_update: AlertUpdate, db: Session = Depends(get_db)
):
    """
    Updates an alert's status or assigned analyst.
    """
    db_alert = db.query(AlertORM).filter(AlertORM.id == alert_id).first()
    if not db_alert:
        raise HTTPException(status_code=404, detail="Alert not found.")

    update_data = alert_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_alert, key, value)

    db.commit()
    db.refresh(db_alert)
    return db_alert
