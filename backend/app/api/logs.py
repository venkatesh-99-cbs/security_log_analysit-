"""
Logs API — file upload, log retrieval, file status, stats.
"""
import os
import shutil
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..core.settings import settings
from ..database.session import get_db
from ..models.base import SecurityLog, UploadedFile
from ..schemas import schemas
from ..background.pipeline import process_log_file

router = APIRouter()


# ─── File Upload ─────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_log(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a log file and trigger background parsing."""
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # Sanitize filename
    safe_name = os.path.basename(file.filename or "upload.log")
    filepath = os.path.join(settings.UPLOAD_DIR, f"{os.urandom(8).hex()}_{safe_name}")

    # Save to disk
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Create DB record
    file_record = UploadedFile(
        filename=safe_name,
        filepath=filepath,
        status="uploaded",
    )
    db.add(file_record)
    db.commit()
    db.refresh(file_record)

    # Kick off background pipeline
    background_tasks.add_task(process_log_file, file_record.id, db)

    return {
        "id": file_record.id,
        "filename": file_record.filename,
        "status": file_record.status,
        "created_at": file_record.created_at.isoformat(),
    }


# ─── Files ────────────────────────────────────────────────────────────────────

@router.get("/files")
def list_files(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List all uploaded files with their processing status."""
    files = db.query(UploadedFile).order_by(
        UploadedFile.created_at.desc()
    ).offset(skip).limit(limit).all()

    return [
        {
            "id": f.id,
            "filename": f.filename,
            "status": f.status,
            "created_at": f.created_at.isoformat() if f.created_at else None,
            "log_count": db.query(func.count(SecurityLog.id)).filter(
                SecurityLog.file_id == f.id
            ).scalar() or 0,
        }
        for f in files
    ]


@router.get("/files/{file_id}")
def get_file(file_id: int, db: Session = Depends(get_db)):
    """Get a single uploaded file record."""
    f = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    return {
        "id": f.id,
        "filename": f.filename,
        "status": f.status,
        "created_at": f.created_at.isoformat() if f.created_at else None,
    }


# ─── Log Entries ─────────────────────────────────────────────────────────────

@router.get("/", response_model=List[schemas.SecurityLog])
def get_logs(
    skip: int = 0,
    limit: int = 100,
    severity: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    file_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """List security log entries with optional filters."""
    q = db.query(SecurityLog)
    if severity:
        q = q.filter(SecurityLog.severity == severity)
    if category:
        q = q.filter(SecurityLog.category == category)
    if source:
        q = q.filter(SecurityLog.source.ilike(f"%{source}%"))
    if file_id:
        q = q.filter(SecurityLog.file_id == file_id)
    return q.order_by(SecurityLog.timestamp.desc()).offset(skip).limit(limit).all()


# ─── Stats ───────────────────────────────────────────────────────────────────

@router.get("/stats")
def get_log_stats(db: Session = Depends(get_db)):
    """Return aggregate statistics for the dashboard."""
    total_logs = db.query(func.count(SecurityLog.id)).scalar() or 0

    severity_counts = (
        db.query(SecurityLog.severity, func.count(SecurityLog.id))
        .group_by(SecurityLog.severity)
        .all()
    )

    category_counts = (
        db.query(SecurityLog.category, func.count(SecurityLog.id))
        .group_by(SecurityLog.category)
        .order_by(func.count(SecurityLog.id).desc())
        .limit(10)
        .all()
    )

    files_total = db.query(func.count(UploadedFile.id)).scalar() or 0
    files_processing = (
        db.query(func.count(UploadedFile.id))
        .filter(UploadedFile.status.in_(["uploaded", "processing"]))
        .scalar() or 0
    )

    return {
        "total_logs": total_logs,
        "total_files": files_total,
        "files_processing": files_processing,
        "severity_breakdown": {row[0]: row[1] for row in severity_counts},
        "category_breakdown": {row[0]: row[1] for row in category_counts},
    }
