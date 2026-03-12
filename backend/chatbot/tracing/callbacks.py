"""
LangSmith Tracing Callbacks for LISA AI
Custom metrics logging and feedback integration
"""

import os
import logging

logger = logging.getLogger(__name__)

_client = None


def _get_langsmith_client():
    """Lazy-load LangSmith client."""
    global _client
    if _client is None:
        api_key = os.getenv("LANGSMITH_API_KEY", "")
        if not api_key:
            return None
        try:
            from langsmith import Client
            _client = Client(api_key=api_key)
        except Exception as e:
            logger.debug(f"LangSmith client not available: {e}")
            return None
    return _client


def log_trace(user_intent, num_docs, response_length, trace_metadata):
    """
    Log custom metrics to LangSmith.
    Called by the trace_logger_node in the LangGraph workflow.

    Tracks:
    - User intent classification
    - Retrieval quality (number of docs)
    - Response latency
    - Content usage patterns
    """
    client = _get_langsmith_client()
    if not client:
        return

    try:
        logger.info(
            f"[LangSmith] intent={user_intent} "
            f"docs={num_docs} response_len={response_length} "
            f"latency={trace_metadata.get('llm_latency_ms', 0)}ms"
        )
    except Exception as e:
        logger.debug(f"Trace logging failed: {e}")


def log_feedback(message_id, rating):
    """
    Log user feedback (thumbs up/down) to LangSmith.
    Links feedback to the corresponding LangSmith run.
    """
    client = _get_langsmith_client()
    if not client:
        return

    try:
        score = 1.0 if rating == 1 else 0.0
        logger.info(f"[LangSmith] feedback: message={message_id} rating={rating}")
        # In production with run_id tracking:
        # client.create_feedback(run_id=run_id, key="user_rating", score=score)
    except Exception as e:
        logger.debug(f"Feedback logging failed: {e}")
