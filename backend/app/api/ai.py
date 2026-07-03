"""
AI API — chat endpoint and RAG query.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database.session import get_db
from ..models.base import ChatHistory
from ..ai.ollama_client import ChatService, OllamaClient
from ..rag.service import RAGQueryService

router = APIRouter()
_chat_service = ChatService()
_rag_service = RAGQueryService()
_ollama = OllamaClient()


class ChatRequest(BaseModel):
    session_id: str
    message: str
    use_rag: bool = True


class ChatResponse(BaseModel):
    session_id: str
    response: str
    rag_used: bool


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """Send a message to the AI copilot with optional RAG context."""
    # Load history
    history_records = (
        db.query(ChatHistory)
        .filter(ChatHistory.session_id == request.session_id)
        .order_by(ChatHistory.timestamp.asc())
        .limit(20)
        .all()
    )
    history = [{"role": h.role, "content": h.content} for h in history_records]

    # RAG retrieval
    rag_context: Optional[str] = None
    rag_used = False
    if request.use_rag:
        rag_context = _rag_service.retrieve_context(request.message, n_results=4)
        rag_used = bool(rag_context)

    # Generate response
    response_text = await _chat_service.respond(
        user_message=request.message,
        history=history,
        rag_context=rag_context,
    )

    # Persist history
    from datetime import datetime
    db.add(ChatHistory(
        session_id=request.session_id,
        role="user",
        content=request.message,
        timestamp=datetime.utcnow(),
    ))
    db.add(ChatHistory(
        session_id=request.session_id,
        role="assistant",
        content=response_text,
        timestamp=datetime.utcnow(),
    ))
    db.commit()

    return ChatResponse(
        session_id=request.session_id,
        response=response_text,
        rag_used=rag_used,
    )


@router.get("/chat/{session_id}/history")
def get_chat_history(session_id: str, limit: int = 50, db: Session = Depends(get_db)):
    """Retrieve chat history for a session."""
    records = (
        db.query(ChatHistory)
        .filter(ChatHistory.session_id == session_id)
        .order_by(ChatHistory.timestamp.asc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "role": r.role,
            "content": r.content,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
        }
        for r in records
    ]


@router.delete("/chat/{session_id}/history")
def clear_chat_history(session_id: str, db: Session = Depends(get_db)):
    """Clear all messages in a chat session."""
    deleted = (
        db.query(ChatHistory)
        .filter(ChatHistory.session_id == session_id)
        .delete()
    )
    db.commit()
    return {"deleted": deleted}


@router.get("/status")
async def ai_status():
    """Check if Ollama is available."""
    available = await _ollama.is_available()
    return {
        "ollama_available": available,
        "model": _ollama.model,
        "base_url": _ollama.base_url,
        "rag_documents": _rag_service._store.count(),
    }


@router.post("/rag/ingest")
def ingest_knowledge():
    """Ingest built-in security knowledge into the vector store."""
    count = _rag_service.ingest_security_knowledge()
    return {"ingested": count, "total": _rag_service._store.count()}
