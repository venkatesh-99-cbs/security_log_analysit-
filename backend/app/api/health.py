"""
Health API — system and Ollama connectivity check.
"""
from flask import Blueprint, jsonify

from ..ai.ollama_client import OllamaClient

router = Blueprint("health", __name__)
_ollama = OllamaClient()


@router.route("/", methods=["GET"])
@router.route("/status", methods=["GET"])
def health_check():
    """Full system health check."""
    ollama_ok = _ollama.is_available()
    return jsonify({
        "status": "healthy",
        "backend": "ok",
        "ollama": "connected" if ollama_ok else "unavailable",
        "ollama_model": _ollama.model,
    })
