"""
Knowledge Base Ingestion — load documents from knowledge_base folder into ChromaDB.
"""
import logging
import os
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


def _find_knowledge_base_path() -> Path:
    """Find the knowledge_base directory by checking multiple locations."""
    possible_paths = [
        Path("./knowledge_base"),
        Path("../knowledge_base"),
        Path("/app/knowledge_base"),
        Path("/workspace/knowledge_base"),
        Path.cwd() / "knowledge_base",
    ]
    
    for path in possible_paths:
        if path.exists() and path.is_dir():
            logger.info("Found knowledge_base at: %s", path.resolve())
            return path
    
    logger.warning("Knowledge base not found in any standard location")
    return None


def load_knowledge_base_documents(kb_path: str = None) -> List[Dict[str, str]]:
    """Load all markdown and text files from the knowledge_base directory structure."""
    documents = []
    
    # Resolve path
    if kb_path is None:
        kb_root = _find_knowledge_base_path()
    else:
        kb_root = Path(kb_path)
    
    if not kb_root or not kb_root.exists():
        logger.warning("Knowledge base path does not exist: %s", kb_path or "auto-detected")
        return documents
    
    logger.info("Loading knowledge base from: %s", kb_root.resolve())
    
    # Supported file extensions
    extensions = {'.md', '.txt', '.markdown'}
    
    # Walk through all subdirectories
    for root, dirs, files in os.walk(kb_root):
        for file in files:
            file_path = Path(root) / file
            file_ext = file_path.suffix.lower()
            
            # Skip non-document files and index files
            if file_ext not in extensions or file in ['README.md', 'COLLECTION_INDEX.md', 'DOCUMENT_INDEX.md', 'EMBEDDING_GUIDE.md', 'INGESTION_GUIDE.md', 'METADATA_SCHEMA.md', 'QUALITY_CHECKLIST.md', 'CHUNKING_GUIDE.md']:
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read().strip()
                
                if not content or len(content) < 10:  # Skip very short files
                    continue
                
                # Extract category from folder name (e.g., "01_windows_security" -> "windows_security")
                relative_path = file_path.relative_to(kb_root)
                folder_name = relative_path.parts[0] if len(relative_path.parts) > 1 else "misc"
                category = folder_name.split('_', 1)[-1] if '_' in folder_name else folder_name
                
                # Generate document title
                title = file_path.stem.replace('_', ' ').title()
                source = f"{folder_name}/{file_path.name}"
                
                doc = {
                    "id": f"kb_{file_path.stem}_{hash(str(file_path)) % 10000}",
                    "title": title,
                    "source": source,
                    "category": category,
                    "content": content,
                    "file_path": str(file_path),
                }
                documents.append(doc)
                logger.debug("Loaded document: %s from %s", title, source)
                
            except Exception as exc:
                logger.error("Failed to load document %s: %s", file_path, exc)
                continue
    
    logger.info("Loaded %d documents from knowledge base at %s", len(documents), kb_root.resolve())
    return documents


def ingest_knowledge_base(vector_store, kb_path: str = None) -> int:
    """Ingest all knowledge base documents into ChromaDB."""
    documents = load_knowledge_base_documents(kb_path)
    
    if not documents:
        logger.warning("No documents found in knowledge base")
        return 0
    
    docs = [d["content"] for d in documents]
    metas = [{"title": d["title"], "source": d["source"], "category": d["category"], "file_path": d["file_path"]} for d in documents]
    ids = [d["id"] for d in documents]
    
    success = vector_store.add_documents(docs, metas, ids)
    ingested = len(docs) if success else 0
    
    logger.info("Ingested %d documents into ChromaDB vector store", ingested)
    return ingested
