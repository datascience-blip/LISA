"""
Hybrid Retriever for LISA AI
FAISS semantic search with optional metadata filtering
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class HybridRetriever:
    """FAISS-based retriever with metadata filtering support."""

    def __init__(self, vectorstore_path: str, embedding_model: str):
        from langchain_community.vectorstores import FAISS
        from config.config import Config

        # Use OpenAI embeddings if available, otherwise Gemini
        if Config.OPENAI_API_KEY:
            from langchain_openai import OpenAIEmbeddings
            self.embeddings = OpenAIEmbeddings(model=embedding_model)
        elif Config.GEMINI_API_KEY:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/gemini-embedding-001",
                google_api_key=Config.GEMINI_API_KEY,
            )
        else:
            raise RuntimeError("No API key for embeddings. Set OPENAI_API_KEY or GEMINI_API_KEY.")

        vs_path = Path(vectorstore_path)
        if not (vs_path / "index.faiss").exists():
            raise FileNotFoundError(
                f"FAISS index not found at {vectorstore_path}. "
                "Run 'python scripts/ingest_documents.py' first."
            )

        self.vectorstore = FAISS.load_local(
            str(vs_path),
            self.embeddings,
            allow_dangerous_deserialization=True,
        )
        logger.info(f"FAISS index loaded from {vectorstore_path}")

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        metadata_filter: Optional[Dict] = None,
    ) -> List[Tuple[Document, float]]:
        """
        Retrieve top-k documents with optional metadata filtering.

        FAISS doesn't natively support metadata filtering, so we
        over-retrieve and filter post-hoc when filters are applied.
        """
        if metadata_filter:
            # Over-retrieve to compensate for post-hoc filtering
            raw_results = self.vectorstore.similarity_search_with_score(
                query, k=top_k * 3
            )
            filtered = [
                (doc, score)
                for doc, score in raw_results
                if self._matches_filter(doc.metadata, metadata_filter)
            ]
            return filtered[:top_k]
        else:
            return self.vectorstore.similarity_search_with_score(query, k=top_k)

    def _matches_filter(self, metadata: Dict, filters: Dict) -> bool:
        """Check if document metadata matches all filter criteria."""
        for key, value in filters.items():
            doc_value = metadata.get(key)
            if doc_value is None:
                return False
            if isinstance(value, list):
                if doc_value not in value:
                    return False
            elif doc_value != value:
                return False
        return True
