"""
Reports API — generate and list incident reports.
"""
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database.session import get_db
from ..models.base import Incident, Report
from ..reports.generator import ReportGenerator

router = APIRouter()
_generator = ReportGenerator()


@router.post("/generate")
def generate_report(
    title: str = "Security Incident Report",
    severity_filter: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Generate an HTML report from current incidents."""
    q = db.query(Incident)
    if severity_filter:
        q = q.filter(Incident.severity == severity_filter)
    incidents = q.order_by(Incident.created_at.desc()).limit(100).all()

    if not incidents:
        raise HTTPException(status_code=404, detail="No incidents found to report")

    filepath = _generator.generate_incident_report(incidents, title=title)

    # Save report record to DB
    report = Report(
        title=title,
        report_type="incident",
        filepath=filepath,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "id": report.id,
        "title": report.title,
        "report_type": report.report_type,
        "filepath": filepath,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "incident_count": len(incidents),
    }


@router.get("/")
def list_reports(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """List all generated reports."""
    reports = (
        db.query(Report)
        .order_by(Report.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "title": r.title,
            "report_type": r.report_type,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "exists": os.path.exists(r.filepath or ""),
        }
        for r in reports
    ]


@router.get("/{report_id}/download")
def download_report(report_id: int, db: Session = Depends(get_db)):
    """Download a generated report file."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if not report.filepath or not os.path.exists(report.filepath):
        raise HTTPException(status_code=404, detail="Report file not found on disk")
    return FileResponse(
        path=report.filepath,
        media_type="text/html",
        filename=os.path.basename(report.filepath),
    )
