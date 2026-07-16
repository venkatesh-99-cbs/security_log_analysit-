"""
Logs API — file upload, log retrieval, file status, stats, deletion.
"""
import os
import threading
from typing import Optional

from flask import Blueprint, request, jsonify, abort
from sqlalchemy import func

from ..core.settings import settings
from ..database.session import get_db_session
from ..models.base import SecurityLog, UploadedFile
from ..background.pipeline import process_log_file

router = Blueprint("logs", __name__)


def _to_int(value: Optional[str], default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ─── File Upload ─────────────────────────────────────────────────────────────

@router.route("/upload", methods=["POST"])
def upload_log():
    file = request.files.get("file")
    if not file:
        abort(400, "No file uploaded")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    safe_name = os.path.basename(file.filename or "upload.log")
    filepath = os.path.join(settings.UPLOAD_DIR, f"{os.urandom(8).hex()}_{safe_name}")
    file.save(filepath)

    # Capture file size immediately on upload
    try:
        file_size = os.path.getsize(filepath)
    except Exception:
        file_size = None

    db = get_db_session()
    try:
        file_record = UploadedFile(
            filename=safe_name,
            filepath=filepath,
            status="uploaded",
            file_size=file_size,
        )
        db.add(file_record)
        db.commit()
        db.refresh(file_record)

        thread = threading.Thread(target=process_log_file, args=(file_record.id,), daemon=True)
        thread.start()

        return jsonify({
            "id": file_record.id,
            "filename": file_record.filename,
            "status": file_record.status,
            "file_size": file_record.file_size,
            "created_at": file_record.created_at.isoformat(),
        })
    finally:
        db.close()


# ─── Files ───────────────────────────────────────────────────────────────────

@router.route("/files", methods=["GET"])
def list_files():
    skip = _to_int(request.args.get("skip"), 0)
    limit = _to_int(request.args.get("limit"), 50)

    db = get_db_session()
    try:
        files = db.query(UploadedFile).order_by(UploadedFile.created_at.desc()).offset(skip).limit(limit).all()
        return jsonify([
            {
                "id": f.id,
                "filename": f.filename,
                "status": f.status,
                "created_at": f.created_at.isoformat() if f.created_at else None,
                "file_size": f.file_size,
                "findings_count": f.findings_count,
                "log_count": db.query(func.count(SecurityLog.id)).filter(SecurityLog.file_id == f.id).scalar() or 0,
            }
            for f in files
        ])
    finally:
        db.close()


@router.route("/files/<int:file_id>", methods=["GET"])
def get_file(file_id: int):
    db = get_db_session()
    try:
        f = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
        if not f:
            abort(404, "File not found")
        return jsonify({
            "id": f.id,
            "filename": f.filename,
            "status": f.status,
            "file_size": f.file_size,
            "findings_count": f.findings_count,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        })
    finally:
        db.close()


@router.route("/files/<int:file_id>", methods=["DELETE"])
def delete_file(file_id: int):
    """Delete an uploaded file record, all associated SecurityLog entries, and the disk file."""
    db = get_db_session()
    try:
        f = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
        if not f:
            abort(404, "File not found")

        filepath = f.filepath

        # Delete the database record (cascade="all, delete-orphan" handles SecurityLog children)
        db.delete(f)
        db.commit()

        # Remove the physical file from disk
        disk_deleted = False
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
                disk_deleted = True
            except Exception as exc:
                # Log but don't fail — the DB record is already gone
                import logging
                logging.getLogger(__name__).error("Could not delete file %s: %s", filepath, exc)

        return jsonify({
            "deleted": True,
            "id": file_id,
            "disk_deleted": disk_deleted,
        })
    finally:
        db.close()


@router.route("/files", methods=["DELETE"])
def bulk_delete_files():
    """Bulk-delete multiple uploaded files by ID list in JSON body."""
    payload = request.get_json(silent=True) or {}
    ids = payload.get("ids", [])
    if not isinstance(ids, list) or not ids:
        abort(400, "ids (list of integers) is required")

    db = get_db_session()
    deleted_ids = []
    try:
        files = db.query(UploadedFile).filter(UploadedFile.id.in_(ids)).all()
        for f in files:
            filepath = f.filepath
            db.delete(f)
            if filepath and os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    pass
            deleted_ids.append(f.id)
        db.commit()
        return jsonify({"deleted": len(deleted_ids), "ids": deleted_ids})
    finally:
        db.close()


@router.route("/", methods=["GET"])
def get_logs():
    skip = _to_int(request.args.get("skip"), 0)
    limit = _to_int(request.args.get("limit"), 100)
    severity = request.args.get("severity")
    category = request.args.get("category")
    source = request.args.get("source")
    file_id = request.args.get("file_id")

    db = get_db_session()
    try:
        q = db.query(SecurityLog)
        if severity:
            q = q.filter(SecurityLog.severity == severity)
        if category:
            q = q.filter(SecurityLog.category == category)
        if source:
            q = q.filter(SecurityLog.source.ilike(f"%{source}%"))
        if file_id is not None:
            try:
                q = q.filter(SecurityLog.file_id == int(file_id))
            except ValueError:
                abort(400, "file_id must be an integer")

        logs = q.order_by(SecurityLog.timestamp.desc()).offset(skip).limit(limit).all()
        return jsonify([
            {
                "id": log.id,
                "file_id": log.file_id,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "source": log.source,
                "category": log.category,
                "severity": log.severity,
                "message": log.message,
                "raw_data": log.raw_data,
            }
            for log in logs
        ])
    finally:
        db.close()


@router.route("/stats", methods=["GET"])
def get_log_stats():
    db = get_db_session()
    try:
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

        return jsonify({
            "total_logs": total_logs,
            "total_files": files_total,
            "files_processing": files_processing,
            "severity_breakdown": {row[0]: row[1] for row in severity_counts},
            "category_breakdown": {row[0]: row[1] for row in category_counts},
        })
    finally:
        db.close()
