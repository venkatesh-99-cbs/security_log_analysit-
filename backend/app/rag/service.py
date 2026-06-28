import chromadb
from ..core.settings import settings

class VectorStoreService:
    """
    Manages local ChromaDB vector store for RAG.
    """
    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
        self.collection = self.client.get_or_create_collection(name="security_kb")

    def add_documents(self, documents: list[str], metadatas: list[dict], ids: list[str]):
        # TODO: Implement document ingestion
        pass

    def query(self, query_text: str, n_results: int = 5):
        # TODO: Implement vector search
        return []

class EmbeddingService:
    """
    Generates embeddings using local Ollama models.
    """
    def get_embeddings(self, text: str):
        # TODO: Call Ollama embeddings API
        pass
