"""
Incidents API — CRUD, AI analysis trigger, status update.
"""
from typing import List, Optional

from flask import Blueprint, request, jsonify, abort
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database.session import get_db_session
from ..models.base import AIAnalysis, Incident, MitreMapping, SecurityLog
from ..ai.ollama_client import IncidentAnalyzer

router = Blueprint("incidents", __name__)
_analyzer = IncidentAnalyzer()


def _to_int(value: Optional[str], default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@router.route("/", methods=["GET"])
def get_incidents():
    skip = _to_int(request.args.get("skip"), 0)
    limit = _to_int(request.args.get("limit"), 50)
    status = request.args.get("status")
    severity = request.args.get("severity")

    db = get_db_session()
    try:
        q = db.query(Incident)
        if status:
            q = q.filter(Incident.status == status)
        if severity:
            q = q.filter(Incident.severity == severity)
        incidents = q.order_by(Incident.created_at.desc()).offset(skip).limit(limit).all()

        total = db.query(func.count(Incident.id)).scalar() or 0
        return jsonify({
            "total": total,
            "items": [_serialize_incident(inc, db) for inc in incidents],
        })
    finally:
        db.close()


@router.route("/stats", methods=["GET"])
def get_incident_stats():
    db = get_db_session()
    try:
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
        return jsonify({
            "total": total,
            "open": open_count,
            "severity_distribution": {row[0]: row[1] for row in severity_dist},
        })
    finally:
        db.close()


@router.route("/<int:incident_id>", methods=["GET"])
def get_incident(incident_id: int):
    db = get_db_session()
    try:
        inc = db.query(Incident).filter(Incident.id == incident_id).first()
        if not inc:
            abort(404, "Incident not found")
        return jsonify(_serialize_incident(inc, db, include_analyses=True, include_logs=True))
    finally:
        db.close()


@router.route("/<int:incident_id>", methods=["PATCH"])
def update_incident(incident_id: int):
    payload = request.get_json(silent=True) or {}
    status = payload.get("status") or request.args.get("status")
    severity = payload.get("severity") or request.args.get("severity")

    db = get_db_session()
    try:
        inc = db.query(Incident).filter(Incident.id == incident_id).first()
        if not inc:
            abort(404, "Incident not found")
        if status:
            valid_statuses = {"open", "in_progress", "resolved", "closed"}
            if status not in valid_statuses:
                abort(400, f"Invalid status. Must be one of: {valid_statuses}")
            inc.status = status
        if severity:
            valid_severities = {"info", "low", "medium", "high", "critical"}
            if severity not in valid_severities:
                abort(400, "Invalid severity.")
            inc.severity = severity
        from datetime import datetime
        inc.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(inc)
        return jsonify(_serialize_incident(inc, db))
    finally:
        db.close()


@router.route("/<int:incident_id>/analyze", methods=["POST"])
def analyze_incident(incident_id: int):
    db = get_db_session()
    try:
        inc = db.query(Incident).filter(Incident.id == incident_id).first()
        if not inc:
            abort(404, "Incident not found")

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

        analysis_text = _analyzer.analyze_incident(incident_data)

        analysis = AIAnalysis(
            incident_id=incident_id,
            query=f"Analyze incident: {inc.title}",
            response=analysis_text,
            analysis_type="incident_analysis",
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        return jsonify({
            "id": analysis.id,
            "incident_id": analysis.incident_id,
            "query": analysis.query,
            "response": analysis.response,
            "analysis_type": analysis.analysis_type,
            "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
        })
    finally:
        db.close()


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
