"""
RAG Service — ChromaDB vector store + Ollama embeddings + retrieval-augmented generation.
"""
import logging
import uuid
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from ..core.settings import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "security_kb"


def _get_chroma_client() -> chromadb.ClientAPI:
    """Return a persistent ChromaDB client."""
    try:
        client = chromadb.PersistentClient(
            path=settings.CHROMA_DB_PATH,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        return client
    except Exception as exc:
        logger.error("ChromaDB init failed: %s", exc)
        raise


class EmbeddingService:
    """Generates text embeddings via Ollama's /api/embeddings endpoint using nomic-embed-text."""

    def __init__(self):
        import httpx
        self._httpx = httpx
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.model = settings.OLLAMA_EMBEDDING_MODEL
        logger.info("EmbeddingService initialized with model: %s", self.model)

    def get_embeddings(self, text: str) -> List[float]:
        """Synchronous embedding call using nomic-embed-text."""
        if not text or not text.strip():
            logger.warning("Empty text for embedding, using fallback vector")
            return [0.0] * 768  # nomic-embed-text outputs 768-dim vectors
        
        try:
            with self._httpx.Client(timeout=60) as client:
                resp = client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": text.strip()},
                    timeout=60,
                )
                resp.raise_for_status()
                embedding = resp.json().get("embedding", [])
                if isinstance(embedding, list) and embedding:
                    return embedding
        except Exception as exc:
            logger.warning("Embedding failed for model %s: %s. Using fallback vector.", self.model, exc)
        
        return [0.0] * 768

    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.get_embeddings(t) for t in texts]


class OllamaEmbeddingFunction(chromadb.EmbeddingFunction):
    """ChromaDB-compatible embedding function backed by Ollama nomic-embed-text."""

    def __init__(self):
        self._service = EmbeddingService()

    def __call__(self, input: List[str]) -> List[List[float]]:  # type: ignore[override]
        return self._service.get_embeddings_batch(input)


class VectorStoreService:
    """Manages the ChromaDB knowledge base for RAG."""

    def __init__(self):
        try:
            self._client = _get_chroma_client()
            self._embedding_fn = OllamaEmbeddingFunction()
            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                embedding_function=self._embedding_fn,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("ChromaDB collection '%s' ready with nomic-embed-text embeddings.", COLLECTION_NAME)
        except Exception as exc:
            logger.error("VectorStoreService init failed: %s", exc)
            self._collection = None

    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> bool:
        """Add documents to the vector store."""
        if self._collection is None:
            logger.warning("Collection is None, cannot add documents")
            return False
        if not documents:
            return True
        try:
            doc_ids = ids or [str(uuid.uuid4()) for _ in documents]
            meta = metadatas or [{}] * len(documents)
            self._collection.upsert(
                documents=documents,
                metadatas=meta,
                ids=doc_ids,
            )
            logger.info("Added %d documents to ChromaDB.", len(documents))
            return True
        except Exception as exc:
            logger.error("add_documents failed: %s", exc)
            return False

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """Query the vector store and return top-k results with better ranking."""
        if self._collection is None:
            return []
        try:
            # Request more results internally, then filter by quality
            internal_k = min(n_results * 2, max(self._collection.count() or 5, 1))
            
            kwargs: Dict[str, Any] = {
                "query_texts": [query_text],
                "n_results": internal_k,
                "include": ["documents", "metadatas", "distances"],
            }
            if where:
                kwargs["where"] = where
            
            results = self._collection.query(**kwargs)
            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            dists = results.get("distances", [[]])[0]
            
            # Filter and sort by distance (lower is better for cosine)
            ranked = sorted(
                [
                    {"document": doc, "metadata": meta, "distance": dist}
                    for doc, meta, dist in zip(docs, metas, dists)
                    if dist < 1.0  # Only include reasonably similar results
                ],
                key=lambda x: x["distance"]
            )
            
            return ranked[:n_results]
        except Exception as exc:
            logger.error("VectorStore query failed: %s", exc)
            return []

    def delete_collection(self):
        """Drop and recreate the knowledge base."""
        try:
            self._client.delete_collection(COLLECTION_NAME)
            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                embedding_function=self._embedding_fn,
            )
        except Exception as exc:
            logger.error("delete_collection failed: %s", exc)

    def count(self) -> int:
        if self._collection is None:
            return 0
        try:
            return self._collection.count()
        except Exception:
            return 0


class RAGQueryService:
    """Combines vector retrieval with Ollama LLM for grounded answers."""

    def __init__(
        self,
        vector_store: Optional[VectorStoreService] = None,
    ):
        self._store = vector_store or VectorStoreService()

    def retrieve_context(self, query: str, n_results: int = 5) -> str:
        """Retrieve relevant knowledge-base excerpts as a single context string."""
        results = self._store.query(query, n_results=n_results)
        if not results:
            return ""
        
        parts = []
        for i, r in enumerate(results, 1):
            doc = r.get("document", "")
            meta = r.get("metadata", {})
            distance = r.get("distance", 0)
            source = meta.get("source", meta.get("title", f"Document {i}"))
            category = meta.get("category", "reference")
            
            # Truncate very long documents for performance
            if len(doc) > 500:
                doc = doc[:500] + "..."
            
            # Include relevance indicator
            relevance = "high" if distance < 0.3 else "medium" if distance < 0.6 else "low"
            parts.append(f"[{i}] **{source}** ({category}, {relevance} relevance)\n{doc}")
        
        return "\n\n".join(parts)

    def add_document(self, title: str, content: str, source: str = "User Upload", category: str = "custom") -> int:
        """Add a single user-provided knowledge document to the vector store."""
        if not title or not content:
            return 0
        doc_id = str(uuid.uuid4())
        success = self._store.add_documents(
            [content],
            [{"title": title, "source": source, "category": category}],
            [doc_id],
        )
        return 1 if success else 0

    def ingest_security_knowledge(self) -> int:
        """Ingest built-in security knowledge into the vector store."""
        knowledge = _builtin_security_knowledge()
        docs = [k["content"] for k in knowledge]
        metas = [{"title": k["title"], "source": k["source"], "category": k["category"]} for k in knowledge]
        ids = [k["id"] for k in knowledge]
        self._store.add_documents(docs, metas, ids)
        return len(docs)


def _builtin_security_knowledge() -> List[Dict[str, str]]:
    """Curated security knowledge for RAG seeding."""
    return [
        {
            "id": "brute_force_001",
            "title": "Brute Force Attack Response",
            "source": "SOC Playbook",
            "category": "incident_response",
            "content": (
                "A brute force attack involves systematically trying many passwords to gain access. "
                "Response steps: 1) Block the source IP at the firewall immediately. "
                "2) Lock the targeted accounts temporarily. "
                "3) Enable MFA on all affected accounts. "
                "4) Review authentication logs for successful logins from the IP. "
                "5) Check for data exfiltration after any successful login. "
                "MITRE T1110. Detection: >5 failed logins in 5 minutes from one IP."
            ),
        },
        {
            "id": "port_scan_001",
            "title": "Port Scan Detection and Response",
            "source": "SOC Playbook",
            "category": "incident_response",
            "content": (
                "Port scanning is reconnaissance to discover open services. "
                "Response: 1) Identify the scanner IP and geolocate it. "
                "2) Block IP at perimeter firewall if external. "
                "3) Check if scanner is an internal asset (may indicate compromise). "
                "4) Review firewall rules for unnecessarily exposed ports. "
                "MITRE T1046. Detection: >15 distinct destination ports from one IP in 2 minutes."
            ),
        },
        {
            "id": "lateral_movement_001",
            "title": "Lateral Movement Investigation",
            "source": "SOC Playbook",
            "category": "incident_response",
            "content": (
                "Lateral movement is when an attacker pivots between systems after initial compromise. "
                "Indicators: Multiple successful remote logins to different hosts from one account. "
                "Response: 1) Isolate all affected hosts from the network. "
                "2) Reset credentials of the compromised account. "
                "3) Review what data was accessed on each host. "
                "4) Look for new accounts or scheduled tasks created. "
                "MITRE T1021."
            ),
        },
        {
            "id": "mitre_ta0006",
            "title": "MITRE Credential Access Techniques",
            "source": "MITRE ATT&CK",
            "category": "mitre",
            "content": (
                "Credential Access (TA0006): Techniques to steal credentials. "
                "T1110 Brute Force — trying many passwords. "
                "T1003 OS Credential Dumping — extracting credentials from memory (mimikatz). "
                "T1552 Unsecured Credentials — finding plaintext passwords in files. "
                "Prevention: Use MFA, PAM solutions, credential vaulting, monitor LSASS."
            ),
        },
        {
            "id": "windows_event_auth",
            "title": "Windows Security Event IDs for Authentication",
            "source": "Windows Security Log Encyclopedia",
            "category": "reference",
            "content": (
                "Key Windows authentication event IDs: "
                "4624 — Successful logon (type 2=interactive, 3=network, 10=remote). "
                "4625 — Failed logon (failure reasons: 0xC000006A wrong password, 0xC0000064 bad username). "
                "4648 — Logon using explicit credentials. "
                "4672 — Special privileges assigned (admin logon). "
                "4768/4771 — Kerberos ticket events. "
                "4776 — NTLM credential validation."
            ),
        },
        {
            "id": "soc_triage",
            "title": "SOC Alert Triage Process",
            "source": "SOC Operations Manual",
            "category": "process",
            "content": (
                "Alert Triage Steps: 1) Classify severity (critical/high/medium/low). "
                "2) Determine if it is a true positive or false positive. "
                "3) Identify affected assets and accounts. "
                "4) Escalate critical/high to Tier 2 within 15 minutes. "
                "5) Document all findings in the incident ticket. "
                "6) Collect evidence before any remediation. "
                "7) Notify stakeholders per the escalation matrix."
            ),
        },
    ]
