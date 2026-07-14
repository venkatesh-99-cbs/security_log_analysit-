"""
AI API — chat endpoint and RAG query.
"""
import logging
from typing import List, Optional
from datetime import datetime

from flask import Blueprint, request, jsonify, abort
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from ..database.session import get_db_session
from ..models.base import ChatHistory
from ..ai.ollama_client import ChatService, OllamaClient
from ..rag.service import RAGQueryService

logger = logging.getLogger(__name__)

router = Blueprint("ai", __name__)
_chat_service = ChatService()
_rag_service = None
_ollama = OllamaClient()


def _get_rag_service():
    """Get or initialize RAG service from main app."""
    global _rag_service
    if _rag_service is None:
        from ..main import get_rag_service
        _rag_service = get_rag_service()
    return _rag_service


def _validate_chat_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        abort(400, "Invalid request payload")
    if "session_id" not in payload or "message" not in payload:
        abort(400, "session_id and message are required")
    return {
        "session_id": payload["session_id"],
        "message": payload["message"],
        "use_rag": payload.get("use_rag", True),
    }


@router.route("/chat", methods=["POST"])
def chat():
    payload = _validate_chat_payload(request.get_json(silent=True) or {})
    db = get_db_session()
    try:
        history_records = (
            db.query(ChatHistory)
            .filter(ChatHistory.session_id == payload["session_id"])
            .order_by(ChatHistory.timestamp.asc())
            .limit(20)
            .all()
        )
        history = [{"role": h.role, "content": h.content} for h in history_records]

        rag_context: Optional[str] = None
        rag_used = False
        if payload["use_rag"]:
            rag_svc = _get_rag_service()
            rag_context = rag_svc.retrieve_context(payload["message"], n_results=4)
            rag_used = bool(rag_context)

        response_text = _chat_service.respond(
            user_message=payload["message"],
            history=history,
            rag_context=rag_context,
        )

        db.add(ChatHistory(
            session_id=payload["session_id"],
            role="user",
            content=payload["message"],
            timestamp=datetime.utcnow(),
        ))
        db.add(ChatHistory(
            session_id=payload["session_id"],
            role="assistant",
            content=response_text,
            timestamp=datetime.utcnow(),
        ))
        db.commit()

        return jsonify({
            "session_id": payload["session_id"],
            "response": response_text,
            "rag_used": rag_used,
        })
    finally:
        db.close()


@router.route("/chat/sessions", methods=["GET"])
def list_sessions():
    """List all unique chat sessions with latest message preview."""
    db = get_db_session()
    try:
        sessions = (
            db.query(
                ChatHistory.session_id,
                func.max(ChatHistory.timestamp).label("last_message"),
            )
            .group_by(ChatHistory.session_id)
            .order_by(desc("last_message"))
            .all()
        )
        
        result = []
        for session_id, last_message in sessions:
            latest_msg = (
                db.query(ChatHistory)
                .filter(ChatHistory.session_id == session_id)
                .order_by(desc(ChatHistory.timestamp))
                .first()
            )
            msg_count = (
                db.query(ChatHistory)
                .filter(ChatHistory.session_id == session_id)
                .count()
            )
            preview = ""
            if latest_msg:
                preview = (latest_msg.content[:60] + "...") if len(latest_msg.content) > 60 else latest_msg.content
            
            result.append({
                "session_id": session_id,
                "last_message": last_message.isoformat() if last_message else None,
                "preview": preview,
                "message_count": msg_count,
            })
        
        return jsonify(result)
    finally:
        db.close()


@router.route("/chat/<session_id>/history", methods=["GET"])
def get_chat_history(session_id: str):
    limit = request.args.get("limit", 50)
    try:
        limit = int(limit)
    except ValueError:
        abort(400, "limit must be an integer")

    db = get_db_session()
    try:
        records = (
            db.query(ChatHistory)
            .filter(ChatHistory.session_id == session_id)
            .order_by(ChatHistory.timestamp.asc())
            .limit(limit)
            .all()
        )
        return jsonify([
            {
                "id": r.id,
                "role": r.role,
                "content": r.content,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            }
            for r in records
        ])
    finally:
        db.close()


@router.route("/chat/<session_id>/history", methods=["DELETE"])
def clear_chat_history(session_id: str):
    db = get_db_session()
    try:
        deleted = (
            db.query(ChatHistory)
            .filter(ChatHistory.session_id == session_id)
            .delete()
        )
        db.commit()
        return jsonify({"deleted": deleted})
    finally:
        db.close()


@router.route("/chat/<session_id>", methods=["DELETE"])
def delete_session(session_id: str):
    """Delete an entire chat session and all its messages."""
    db = get_db_session()
    try:
        deleted = (
            db.query(ChatHistory)
            .filter(ChatHistory.session_id == session_id)
            .delete()
        )
        db.commit()
        return jsonify({"deleted": deleted, "session_id": session_id, "success": True})
    finally:
        db.close()


@router.route("/settings", methods=["POST"])
def update_ai_settings():
    payload = request.get_json(silent=True) or {}
    model = payload.get("model")
    if not model:
        abort(400, "model is required")
    
    # Update settings in-memory
    from ..core.settings import settings, USER_SETTINGS_PATH
    settings.OLLAMA_MODEL = model
    
    # Save to user_settings.json for persistence
    import json
    import os
    try:
        data = {}
        if os.path.exists(USER_SETTINGS_PATH):
            with open(USER_SETTINGS_PATH, "r") as f:
                data = json.load(f)
        data["ollama_model"] = model
        with open(USER_SETTINGS_PATH, "w") as f:
            json.dump(data, f)
        
        # Also update global _ollama client's model
        _ollama.model = model
    except Exception as e:
        logger.error("Failed to save AI settings: %s", e)
        abort(500, "Failed to save AI settings")
        
    return jsonify({"success": True, "model": model})


@router.route("/status", methods=["GET"])
def ai_status():
    available = _ollama.is_available()
    available_models = _ollama.list_models() if available else []
    selected_model = _ollama.resolve_model() if available else _ollama.model
    rag_svc = _get_rag_service()
    return jsonify({
        "ollama_available": available,
        "model": selected_model,
        "base_url": _ollama.base_url,
        "recommended_model": _ollama.recommended_model,
        "available_models": available_models,
        "rag_documents": rag_svc._store.count(),
    })


@router.route("/rag/ingest", methods=["POST"])
def ingest_knowledge():
    rag_svc = _get_rag_service()
    count = rag_svc.ingest_security_knowledge()
    return jsonify({"ingested": count, "total": rag_svc._store.count()})


@router.route("/rag/add", methods=["POST"])
def add_knowledge():
    payload = request.get_json(silent=True) or {}
    title = payload.get("title", "").strip()
    content = payload.get("content", "").strip()
    source = payload.get("source", "User Upload").strip() or "User Upload"
    category = payload.get("category", "custom").strip() or "custom"

    if not title or not content:
        abort(400, "title and content are required")

    rag_svc = _get_rag_service()
    ingested = rag_svc.add_document(title=title, content=content, source=source, category=category)
    return jsonify({"ingested": ingested, "total": rag_svc._store.count()})


@router.route("/rag/upload", methods=["POST"])
def upload_knowledge_file():
    file = request.files.get("file")
    title = (request.form.get("title") or "").strip()
    source = (request.form.get("source") or "User Upload").strip() or "User Upload"
    category = (request.form.get("category") or "custom").strip() or "custom"

    if not file or not file.filename:
        abort(400, "A file is required")
    if not title:
        title = file.filename

    content = file.read().decode("utf-8", errors="ignore")
    if not content.strip():
        abort(400, "The uploaded file is empty")

    rag_svc = _get_rag_service()
    ingested = rag_svc.add_document(title=title, content=content, source=source, category=category)
    return jsonify({"ingested": ingested, "total": rag_svc._store.count()})
