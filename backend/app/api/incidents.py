"""
Incidents API — CRUD, AI analysis trigger, status update.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database.session import get_db
from ..models.base import AIAnalysis, Incident, MitreMapping, SecurityLog
from ..schemas import schemas
from ..ai.ollama_client import IncidentAnalyzer

router = APIRouter()
_analyzer = IncidentAnalyzer()


@router.get("/")
def get_incidents(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """List incidents with optional filtering."""
    q = db.query(Incident)
    if status:
        q = q.filter(Incident.status == status)
    if severity:
        q = q.filter(Incident.severity == severity)
    incidents = q.order_by(Incident.created_at.desc()).offset(skip).limit(limit).all()

    total = db.query(func.count(Incident.id)).scalar() or 0

    return {
        "total": total,
        "items": [_serialize_incident(inc, db) for inc in incidents],
    }


@router.get("/stats")
def get_incident_stats(db: Session = Depends(get_db)):
    """Return incident counts for the dashboard."""
    total = db.query(func.count(Incident.id)).scalar() or 0
    open_count = (
        db.query(func.count(Incident.id))
        .filter(Incident.status == "open")
        .scalar() or 0
    )
    severity_dist = (
        db.query(Incident.severity, func.count(Incident.id))
        .group_by(Incident.severity)
        .all()
    )
    return {
        "total": total,
        "open": open_count,
        "severity_distribution": {row[0]: row[1] for row in severity_dist},
    }


@router.get("/{incident_id}")
def get_incident(incident_id: int, db: Session = Depends(get_db)):
    """Get a single incident with MITRE mappings and analyses."""
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return _serialize_incident(inc, db, include_analyses=True, include_logs=True)


@router.patch("/{incident_id}")
def update_incident(
    incident_id: int,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Update incident status or severity."""
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    if status:
        valid_statuses = {"open", "in_progress", "resolved", "closed"}
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
        inc.status = status
    if severity:
        valid_severities = {"info", "low", "medium", "high", "critical"}
        if severity not in valid_severities:
            raise HTTPException(status_code=400, detail=f"Invalid severity.")
        inc.severity = severity
    from datetime import datetime
    inc.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(inc)
    return _serialize_incident(inc, db)


@router.post("/{incident_id}/analyze")
async def analyze_incident(incident_id: int, db: Session = Depends(get_db)):
    """Trigger AI analysis for an incident."""
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    mitre = db.query(MitreMapping).filter(MitreMapping.incident_id == incident_id).all()
    log_count = (
        db.query(func.count(SecurityLog.id))
        .join(SecurityLog.file)
        .scalar() or 0
    )

    incident_data = {
        "title": inc.title,
        "severity": inc.severity,
        "description": inc.description,
        "source_ip": getattr(inc, "source_ip", "unknown"),
        "threat_score": getattr(inc, "threat_score", 0),
        "log_count": log_count,
        "mitre_mappings": [
            {
                "technique_id": m.technique_id,
                "technique_name": m.technique_name,
                "tactic": m.tactic,
            }
            for m in mitre
        ],
    }

    analysis_text = await _analyzer.analyze_incident(incident_data)

    analysis = AIAnalysis(
        incident_id=incident_id,
        query=f"Analyze incident: {inc.title}",
        response=analysis_text,
        analysis_type="incident_analysis",
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return {
        "id": analysis.id,
        "incident_id": analysis.incident_id,
        "query": analysis.query,
        "response": analysis.response,
        "analysis_type": analysis.analysis_type,
        "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
    }


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _serialize_incident(inc: Incident, db: Session, include_analyses=False, include_logs=False) -> dict:
    mitre = db.query(MitreMapping).filter(MitreMapping.incident_id == inc.id).all()
    result = {
        "id": inc.id,
        "title": inc.title,
        "description": inc.description,
        "status": inc.status,
        "severity": inc.severity,
        "created_at": inc.created_at.isoformat() if inc.created_at else None,
        "updated_at": inc.updated_at.isoformat() if inc.updated_at else None,
        "mitre_mappings": [
            {
                "technique_id": m.technique_id,
                "technique_name": m.technique_name,
                "tactic": m.tactic,
            }
            for m in mitre
        ],
    }
    if include_analyses:
        analyses = db.query(AIAnalysis).filter(AIAnalysis.incident_id == inc.id).all()
        result["analyses"] = [
            {
                "id": a.id,
                "query": a.query,
                "response": a.response,
                "analysis_type": a.analysis_type,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in analyses
        ]
    return result
