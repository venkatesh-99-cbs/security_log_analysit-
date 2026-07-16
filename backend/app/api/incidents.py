"""
Incidents API — CRUD, AI analysis trigger, status update, SOC timeline.
"""
from typing import List, Optional
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, abort
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database.session import get_db_session
from ..models.base import AIAnalysis, Incident, MitreMapping, SecurityLog, UploadedFile
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


@router.route("/<int:incident_id>/timeline", methods=["GET"])
def get_incident_timeline(incident_id: int):
    """
    Returns a chronological list of SOC investigation events for an incident.
    All timestamps are UTC ISO strings; the frontend localizes them via Intl.DateTimeFormat.
    """
    db = get_db_session()
    try:
        inc = db.query(Incident).filter(Incident.id == incident_id).first()
        if not inc:
            abort(404, "Incident not found")

        events = []

        # 1. Log upload event — derive from the earliest SecurityLog for this incident
        #    We correlate via file records that contributed logs flagged near this incident.
        #    Simplification: use the incident's own created_at as the baseline; find any
        #    related UploadedFile by matching SecurityLogs whose timestamps are <= incident created_at.
        related_file = (
            db.query(UploadedFile)
            .join(SecurityLog, SecurityLog.file_id == UploadedFile.id)
            .filter(UploadedFile.status == "processed")
            .order_by(UploadedFile.created_at.asc())
            .first()
        )

        upload_ts = related_file.created_at if related_file else inc.created_at
        events.append({
            "id": "upload",
            "event_type": "log_uploaded",
            "title": "Log File Uploaded",
            "description": f"File '{related_file.filename}' ingested into the pipeline" if related_file else "Log source ingested",
            "severity": "info",
            "timestamp": upload_ts.isoformat() if upload_ts else None,
        })

        # 2. Parsing completed — a few seconds after upload (use log count as indicator)
        log_count = db.query(func.count(SecurityLog.id)).filter(
            SecurityLog.file_id == (related_file.id if related_file else -1)
        ).scalar() or 0

        # Use first SecurityLog timestamp as parsing complete indicator
        first_log = (
            db.query(SecurityLog)
            .filter(SecurityLog.file_id == (related_file.id if related_file else -1))
            .order_by(SecurityLog.timestamp.asc())
            .first()
        )
        parse_ts = first_log.timestamp if first_log else upload_ts
        events.append({
            "id": "parsed",
            "event_type": "parsing_completed",
            "title": "Log Parsing Completed",
            "description": f"{log_count} log entries parsed and structured",
            "severity": "info",
            "timestamp": parse_ts.isoformat() if parse_ts else None,
        })

        # 3. Incident correlation / detection
        events.append({
            "id": "incident_created",
            "event_type": "incident_detected",
            "title": "Incident Detected",
            "description": f"Correlation engine flagged: {inc.title}",
            "severity": inc.severity or "medium",
            "timestamp": inc.created_at.isoformat() if inc.created_at else None,
        })

        # 4. MITRE mapping
        mitre = db.query(MitreMapping).filter(MitreMapping.incident_id == incident_id).all()
        if mitre:
            events.append({
                "id": "mitre",
                "event_type": "mitre_mapped",
                "title": "MITRE ATT&CK Techniques Mapped",
                "description": ", ".join(f"{m.technique_id} ({m.tactic})" for m in mitre[:3]),
                "severity": "high" if any(m.tactic in ("execution", "persistence", "privilege-escalation") for m in mitre) else "medium",
                "timestamp": inc.created_at.isoformat() if inc.created_at else None,
            })

        # 5. AI Analysis (most recent)
        latest_analysis = (
            db.query(AIAnalysis)
            .filter(AIAnalysis.incident_id == incident_id)
            .order_by(AIAnalysis.created_at.desc())
            .first()
        )
        if latest_analysis:
            events.append({
                "id": f"analysis_{latest_analysis.id}",
                "event_type": "analysis_completed",
                "title": "AI Playbook Analysis Completed",
                "description": "Ollama LLM generated incident response recommendations",
                "severity": "info",
                "timestamp": latest_analysis.created_at.isoformat() if latest_analysis.created_at else None,
            })

        # Sort chronologically by timestamp, None timestamps go last
        events.sort(key=lambda e: e["timestamp"] or "9999")

        return jsonify({
            "incident_id": incident_id,
            "events": events,
        })
    finally:
        db.close()



@router.route("/<int:incident_id>", methods=["DELETE"])
def delete_incident(incident_id: int):
    """Delete an individual incident and cascade delete its analyses/mappings."""
    db = get_db_session()
    try:
        inc = db.query(Incident).filter(Incident.id == incident_id).first()
        if not inc:
            abort(404, "Incident not found")
        db.delete(inc)
        db.commit()
        return jsonify({"deleted": True, "id": incident_id})
    finally:
        db.close()


@router.route("/", methods=["DELETE"])
def bulk_delete_incidents():
    """Bulk-delete selected incidents by ID or delete all incidents if 'all' is true."""
    payload = request.get_json(silent=True) or {}
    ids = payload.get("ids", [])
    delete_all = payload.get("all", False)

    db = get_db_session()
    try:
        if delete_all:
            deleted_count = db.query(Incident).delete(synchronize_session=False)
            db.commit()
            return jsonify({"deleted": deleted_count})
        elif ids:
            deleted_count = db.query(Incident).filter(Incident.id.in_(ids)).delete(synchronize_session=False)
            db.commit()
            return jsonify({"deleted": deleted_count, "ids": ids})
        else:
            abort(400, "Provide a list of 'ids' or set 'all' to true")
    finally:
        db.close()


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _serialize_incident(inc: Incident, db: Session, include_analyses=False, include_logs=False) -> dict:
    mitre = db.query(MitreMapping).filter(MitreMapping.incident_id == inc.id).all()
    # Incidents currently predate a direct upload FK. Resolve the upload that
    # created the incident from the processing timeline so the queue can group
    # investigations by upload batch.
    upload = (
        db.query(UploadedFile)
        .filter(UploadedFile.created_at <= inc.created_at)
        .order_by(UploadedFile.created_at.desc())
        .first()
    )
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
        "upload_id": upload.id if upload else None,
        "upload_filename": upload.filename if upload else "Unassigned upload",
        "upload_created_at": upload.created_at.isoformat() if upload and upload.created_at else None,
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
