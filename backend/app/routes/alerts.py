"""
VaultGuard - Alerts API Endpoints
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from backend.app.database import get_db
from backend.app.models.orm import AlertHistoryORM, AlertORM
from backend.app.schemas.pydantic_schemas import AlertHistoryResponse, AlertResponse, AlertCreate, AlertUpdate

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


@router.get("", response_model=List[AlertResponse])
def get_alerts(
    status: Optional[str] = None,
    segment: Optional[str] = None,
    severity: Optional[str] = None,
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
    if severity:
        query = query.filter(AlertORM.severity == severity)
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

    # Suppress a second open alert with the same operational meaning in a short
    # time window; it avoids noise while retaining the original alert for review.
    recent_cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
    duplicate = (
        db.query(AlertORM)
        .filter(
            AlertORM.title == alert_in.title,
            AlertORM.segment == alert_in.segment,
            AlertORM.status.in_(["Monitoring", "Investigating"]),
            AlertORM.created_at >= recent_cutoff,
        )
        .first()
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A matching open alert already exists ({duplicate.alert_code}).",
        )

    db_alert = AlertORM(**alert_in.model_dump())
    try:
        db.add(db_alert)
        db.flush()
        db.add(AlertHistoryORM(alert_id=db_alert.id, event_type="created", new_status=db_alert.status))
        db.commit()
        db.refresh(db_alert)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to create alert.") from exc
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
    acknowledge = update_data.pop("acknowledge", None)
    previous_status = db_alert.status
    for key, value in update_data.items():
        setattr(db_alert, key, value)

    if acknowledge is True and db_alert.acknowledged_at is None:
        db_alert.acknowledged_at = datetime.now(timezone.utc)
    elif acknowledge is False:
        db_alert.acknowledged_at = None

    try:
        if previous_status != db_alert.status:
            db.add(AlertHistoryORM(
                alert_id=db_alert.id,
                event_type="status_changed",
                previous_status=previous_status,
                new_status=db_alert.status,
            ))
        if acknowledge is not None:
            db.add(AlertHistoryORM(
                alert_id=db_alert.id,
                event_type="acknowledged" if acknowledge else "acknowledgement_cleared",
                previous_status=previous_status,
                new_status=db_alert.status,
            ))
        db.commit()
        db.refresh(db_alert)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to update alert.") from exc
    return db_alert


@router.get("/{alert_id}/history", response_model=List[AlertHistoryResponse])
def get_alert_history(alert_id: int, db: Session = Depends(get_db)):
    """Return persisted lifecycle events for an operational alert."""
    if not db.query(AlertORM.id).filter(AlertORM.id == alert_id).first():
        raise HTTPException(status_code=404, detail="Alert not found.")
    return (
        db.query(AlertHistoryORM)
        .filter(AlertHistoryORM.alert_id == alert_id)
        .order_by(AlertHistoryORM.created_at.desc(), AlertHistoryORM.id.desc())
        .all()
    )
