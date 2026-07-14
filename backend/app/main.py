import logging
from flask import Flask, jsonify
from flask_cors import CORS

from .core.settings import settings
from .api import logs_router, incidents_router, health_router, ai_router, reports_router
from .database.session import engine
from .models import base
from .rag.service import RAGQueryService
from .rag.ingestion import ingest_knowledge_base

logger = logging.getLogger(__name__)

# Initialize database tables
base.Base.metadata.create_all(bind=engine)

app = Flask(__name__)
CORS(app, origins=[str(o) for o in settings.BACKEND_CORS_ORIGINS], supports_credentials=True)

# Global RAG service - initialize on first use
_rag_service = None
_rag_initialized = False

def get_rag_service():
    """Lazy-load RAG service with knowledge base ingestion."""
    global _rag_service, _rag_initialized
    
    if _rag_service is None:
        _rag_service = RAGQueryService()
    
    if not _rag_initialized:
        try:
            current_count = _rag_service._store.count()
            if current_count == 0:
                logger.info("RAG: Ingesting knowledge base from ./knowledge_base folder...")
                ingested = ingest_knowledge_base(_rag_service._store, kb_path=None)
                logger.info("RAG: Knowledge base ingestion complete: %d documents indexed", ingested)
            else:
                logger.info("RAG: Knowledge base already initialized with %d documents", current_count)
        except Exception as exc:
            logger.error("RAG initialization failed: %s. System will continue with empty KB.", exc)
        
        _rag_initialized = True
    
    return _rag_service

# ─── Routers ─────────────────────────────────────────────────────────────────
app.register_blueprint(health_router, url_prefix=f"{settings.API_V1_STR}/health")
app.register_blueprint(logs_router, url_prefix=f"{settings.API_V1_STR}/logs")
app.register_blueprint(incidents_router, url_prefix=f"{settings.API_V1_STR}/incidents")
app.register_blueprint(ai_router, url_prefix=f"{settings.API_V1_STR}/ai")
app.register_blueprint(reports_router, url_prefix=f"{settings.API_V1_STR}/reports")

@app.route("/")
def root():
    return jsonify({"message": "Security Log Analysis Assistant API"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
