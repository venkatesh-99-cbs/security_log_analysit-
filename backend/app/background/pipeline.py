"""
Background Processing Pipeline — orchestrates file parsing, detection, and correlation.
"""
import logging
import os
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..core.settings import settings
from ..database.session import get_db_session
from ..models.base import SecurityLog, Incident, MitreMapping, UploadedFile
from ..parsers import parse_log_file
from ..detection import DetectionOrchestrator
from ..correlation.engine import CorrelationEngine

logger = logging.getLogger(__name__)


def process_log_file(file_id: int) -> Dict[str, Any]:
    """
    Main background pipeline:
    1. Load file from disk
    2. Detect format → parse → save SecurityLog records
    3. Run all detectors → collect alerts
    4. Run correlation engine → create Incident records
    5. Update UploadedFile.status

    Returns summary dict.
    """
    db = get_db_session()
    try:
        file_record: Optional[UploadedFile] = db.query(UploadedFile).filter(
            UploadedFile.id == file_id
        ).first()

        if not file_record:
            logger.error("File record %d not found.", file_id)
            return {"error": "File record not found"}

        file_record.status = "processing"
        db.commit()

        summary = {
            "file_id": file_id,
            "filename": file_record.filename,
            "logs_parsed": 0,
            "alerts_detected": 0,
            "incidents_created": 0,
            "status": "failed",
        }

        filepath = file_record.filepath
        if not filepath or not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            raw_data = f.read()

        logger.info("Processing file %s (%d chars)", file_record.filename, len(raw_data))

        parsed_entries = parse_log_file(raw_data, filename=file_record.filename)
        logger.info("Parsed %d log entries from %s", len(parsed_entries), file_record.filename)

        for entry in parsed_entries:
            ts = entry.get("timestamp")
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts)
                except ValueError:
                    ts = datetime.utcnow()
            elif not isinstance(ts, datetime):
                ts = datetime.utcnow()

            log_record = SecurityLog(
                file_id=file_id,
                timestamp=ts,
                source=str(entry.get("source", "unknown"))[:255],
                category=str(entry.get("category", "general"))[:100],
                severity=str(entry.get("severity", "info"))[:50],
                message=str(entry.get("message", ""))[:2000],
                raw_data=entry.get("raw_data"),
            )
            db.add(log_record)

            if len(db.new) % 500 == 0:
                db.commit()
                db.flush()

        db.commit()
        db.refresh(file_record)

        saved_logs = db.query(SecurityLog).filter(SecurityLog.file_id == file_id).all()
        log_dicts = [
            {
                "id": l.id,
                "timestamp": l.timestamp,
                "source": l.source,
                "category": l.category,
                "severity": l.severity,
                "message": l.message,
                "raw_data": l.raw_data or {},
            }
            for l in saved_logs
        ]
        summary["logs_parsed"] = len(saved_logs)

        orchestrator = DetectionOrchestrator()
        alerts = orchestrator.run_all(log_dicts)
        logger.info("Detected %d alerts", len(alerts))
        summary["alerts_detected"] = len(alerts)

        correlation_engine = CorrelationEngine()
        incidents_data = correlation_engine.correlate(log_dicts, alerts)
        logger.info("Correlated %d incidents", len(incidents_data))

        for inc_data in incidents_data:
            incident = Incident(
                title=inc_data.get("title", "Untitled Incident")[:255],
                description=inc_data.get("description", "")[:5000],
                status=inc_data.get("status", "open"),
                severity=inc_data.get("severity", "medium"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(incident)
            db.flush()

            for mapping in inc_data.get("mitre_mappings", []):
                mitre = MitreMapping(
                    incident_id=incident.id,
                    technique_id=mapping.get("technique_id", ""),
                    technique_name=mapping.get("technique_name", ""),
                    tactic=mapping.get("tactic", ""),
                )
                db.add(mitre)

        db.commit()
        summary["incidents_created"] = len(incidents_data)

        file_record.status = "processed"
        db.commit()
        summary["status"] = "success"
        logger.info("Pipeline complete for file %d: %s", file_id, summary)
    except Exception as exc:
        logger.error("Pipeline failed for file %d: %s", file_id, exc, exc_info=True)
        try:
            if file_record is not None:
                file_record.status = "failed"
                db.commit()
        except Exception:
            pass
        summary = {"error": str(exc)}
    finally:
        db.close()

    return summary
