"""
LangGraph State Schema for LISA AI
Defines the TypedDict that flows through every graph node
"""

from typing import TypedDict, List, Dict, Optional, Literal


class GraphState(TypedDict):
    # --- Input ---
    query: str
    user_id: str
    session_id: str
    conversation_history: List[Dict]  # [{role: "user"|"assistant", content: str}]

    # --- Intent Classification (LLM-only, no ML model) ---
    intent: Literal["query_support", "content_generation", "behaviour_discovery", ""]
    intent_confidence: float

    # --- RAG Retrieval ---
    retrieved_documents: List[Dict]  # [{text, metadata, score}]
    reranked_documents: List[Dict]

    # --- Tool Calling ---
    tool_name: Optional[str]
    tool_input: Optional[Dict]
    tool_output: Optional[str]

    # --- LLM Response ---
    response: str
    needs_clarification: bool

    # --- Memory ---
    memory_updated: bool

    # --- Tracing ---
    trace_metadata: Dict

    # --- Regeneration ---
    regenerate: bool

    # --- Message ID (set after memory update) ---
    message_id: Optional[str]

    # --- Error ---
    error: Optional[str]
