"""CSV bulk fraud-analysis API; uploads are processed in memory and never persisted."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.services.bulk_analysis import (
    MAX_UPLOAD_BYTES,
    accepted_schema,
    analyse_csv,
    get_result,
    result_csv,
    sample_csv_bytes,
)

router = APIRouter(prefix="/api/bulk-analysis", tags=["Bulk Fraud Detection"])


@router.get("/schema")
def get_schema():
    return accepted_schema()


@router.get("/sample.csv")
def download_sample_csv():
    return Response(
        sample_csv_bytes(), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="vaultguard_bulk_sample.csv"'},
    )


@router.post("/upload")
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if file.content_type not in {"text/csv", "application/csv", "application/vnd.ms-excel", "application/octet-stream"}:
        raise HTTPException(status_code=415, detail="Upload a CSV file with a supported content type.")
    try:
        result = analyse_csv(await file.read(MAX_UPLOAD_BYTES + 1), db=db)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return result


@router.get("/{analysis_id}")
def get_analysis(analysis_id: str):
    result = get_result(analysis_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Analysis results are unavailable or have expired.")
    return result


@router.get("/{analysis_id}/export")
def export_analysis(analysis_id: str):
    csv_text = result_csv(analysis_id)
    if csv_text is None:
        raise HTTPException(status_code=404, detail="Analysis results are unavailable or have expired.")
    return Response(
        csv_text, media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="vaultguard_bulk_analysis.csv"'},
    )
