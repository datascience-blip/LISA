"""
Cross-Encoder Re-ranker for LISA AI
Re-ranks retrieved documents using a cross-encoder model for better relevance
"""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """Re-ranks documents using a cross-encoder model."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(model_name)
            self._available = True
            logger.info(f"Cross-encoder reranker loaded: {model_name}")
        except Exception as e:
            logger.warning(f"Cross-encoder not available: {e}. Re-ranking disabled.")
            self.model = None
            self._available = False

    def rerank(
        self,
        query: str,
        documents: List[Dict],
        top_k: int = 5,
    ) -> List[Dict]:
        """
        Re-rank documents by cross-encoder relevance score.

        Args:
            query: User's query
            documents: List of dicts with 'text' key (from retrieval node)
            top_k: Number of top documents to return

        Returns:
            Re-ranked list of document dicts with updated scores
        """
        if not self._available or not documents:
            return documents[:top_k]

        # Build query-document pairs for cross-encoder
        texts = [doc.get("text", doc.get("page_content", "")) for doc in documents]
        pairs = [(query, text) for text in texts]

        # Score all pairs
        scores = self.model.predict(pairs)

        # Attach scores and sort
        scored_docs = list(zip(documents, scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        # Return top-k with updated score
        reranked = []
        for doc, score in scored_docs[:top_k]:
            reranked_doc = dict(doc)
            reranked_doc["rerank_score"] = float(score)
            reranked.append(reranked_doc)

        return reranked
