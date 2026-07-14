"""
Reports API — generate and list incident reports.
"""
import os
import logging
from typing import Optional

from flask import Blueprint, request, jsonify, abort, send_file
from sqlalchemy.orm import Session

from ..database.session import get_db_session
from ..models.base import Incident, Report
from ..reports.generator import ReportGenerator

logger = logging.getLogger(__name__)

router = Blueprint("reports", __name__)
_generator = ReportGenerator()


def _to_int(value: Optional[str], default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@router.route("/generate", methods=["POST"])
def generate_report():
    payload = request.get_json(silent=True) or {}
    title = payload.get("title", request.args.get("title", "Security Incident Report"))
    severity_filter = payload.get("severity_filter", request.args.get("severity_filter"))

    db = get_db_session()
    try:
        q = db.query(Incident)
        if severity_filter:
            q = q.filter(Incident.severity == severity_filter)
        incidents = q.order_by(Incident.created_at.desc()).limit(100).all()

        if not incidents:
            abort(404, "No incidents found to report")

        filepath = _generator.generate_incident_report(incidents, title=title)

        report = Report(
            title=title,
            report_type="incident",
            filepath=filepath,
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        return jsonify({
            "id": report.id,
            "title": report.title,
            "report_type": report.report_type,
            "filepath": filepath,
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "incident_count": len(incidents),
        })
    except Exception as exc:
        logger.error("Report generation failed: %s", exc)
        abort(500, f"Report generation failed: {str(exc)}")
    finally:
        db.close()


@router.route("/", methods=["GET"])
def list_reports():
    skip = _to_int(request.args.get("skip"), 0)
    limit = _to_int(request.args.get("limit"), 20)

    db = get_db_session()
    try:
        reports = (
            db.query(Report)
            .order_by(Report.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return jsonify([
            {
                "id": r.id,
                "title": r.title,
                "report_type": r.report_type,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "exists": os.path.exists(r.filepath or ""),
            }
            for r in reports
        ])
    except Exception as exc:
        logger.error("Failed to list reports: %s", exc)
        abort(500, "Failed to list reports")
    finally:
        db.close()


@router.route("/<int:report_id>/download", methods=["GET"])
def download_report(report_id: int):
    """Download a report file with proper naming and error handling."""
    db = get_db_session()
    try:
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            logger.warning("Report not found: %d", report_id)
            abort(404, "Report not found")
        
        if not report.filepath or not os.path.exists(report.filepath):
            logger.warning("Report file not found: %s", report.filepath)
            abort(404, "Report file not found")
        
        # Create a simple, identifiable filename
        # Format: "SOC_Report_<title>_<id>.html"
        clean_title = report.title.replace(" ", "_").replace("/", "_").lower()[:30]
        download_filename = f"SOC_Report_{clean_title}_{report_id}.html"
        
        logger.info("Downloading report: %s -> %s", report.filepath, download_filename)
        
        # Resolve to absolute path to prevent Flask send_file relative-to-app-root resolution bugs
        abs_filepath = os.path.abspath(report.filepath)
        
        # Send file with proper headers for resume support
        return send_file(
            abs_filepath,
            mimetype="text/html",
            as_attachment=True,
            download_name=download_filename
        )
    except FileNotFoundError as exc:
        logger.error("File not found during download: %s", exc)
        abort(404, "Report file not found on server")
    except Exception as exc:
        logger.error("Download error for report %d: %s", report_id, exc)
        abort(500, f"Download failed: {str(exc)}")
    finally:
        db.close()


@router.route("/<int:report_id>", methods=["DELETE"])
def delete_report(report_id: int):
    """Delete a report and its file."""
    db = get_db_session()
    try:
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            abort(404, "Report not found")
        
        # Delete file from disk if it exists
        if report.filepath and os.path.exists(report.filepath):
            try:
                os.remove(report.filepath)
                logger.info("Deleted report file: %s", report.filepath)
            except Exception as e:
                logger.error("Failed to delete file %s: %s", report.filepath, e)
                abort(500, f"Failed to delete file: {str(e)}")
        
        # Delete database record
        db.delete(report)
        db.commit()
        
        logger.info("Deleted report record: %d", report_id)
        return jsonify({"deleted": True, "id": report_id})
    except Exception as exc:
        logger.error("Delete report error: %s", exc)
        abort(500, f"Delete failed: {str(exc)}")
    finally:
        db.close()
