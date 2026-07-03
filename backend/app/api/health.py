"""
Health API — system and Ollama connectivity check.
"""
from fastapi import APIRouter
from ..ai.ollama_client import OllamaClient

router = APIRouter()
_ollama = OllamaClient()


@router.get("/")
async def health_check():
    """Full system health check."""
    ollama_ok = await _ollama.is_available()
    return {
        "status": "healthy",
        "backend": "ok",
        "ollama": "connected" if ollama_ok else "unavailable",
        "ollama_model": _ollama.model,
    }
