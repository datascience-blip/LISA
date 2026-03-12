"""
LangGraph Builder for LISA AI
Assembles and compiles the full workflow graph

Simplified flow (no ML model):
  START → Intent Classifier (LLM) → RAG Retrieval → LLM Response → Memory Update → Trace Logger → END
"""

from langgraph.graph import StateGraph, END
from .state import GraphState
from .nodes import (
    intent_classifier_node,
    rag_retrieval_node,
    llm_response_node,
    tool_execution_node,
    memory_update_node,
    trace_logger_node,
)
from .edges import route_after_llm


def build_graph():
    """
    Build and compile the LISA AI LangGraph workflow.

    Flow:
        START → Intent Classifier (LLM)
              → RAG Retrieval (FAISS search)
              → LLM Response (GPT-4o-mini generates answer from retrieved docs)
                  → (tool needed) → Tool Execution → LLM Response (loop)
                  → (no tool) → Memory Update → Trace Logger → END
    """
    workflow = StateGraph(GraphState)

    # Add all nodes
    workflow.add_node("intent_classifier", intent_classifier_node)
    workflow.add_node("rag_retrieval", rag_retrieval_node)
    workflow.add_node("llm_response", llm_response_node)
    workflow.add_node("tool_execution", tool_execution_node)
    workflow.add_node("memory_update", memory_update_node)
    workflow.add_node("trace_logger", trace_logger_node)

    # Entry point → Intent Classifier
    workflow.set_entry_point("intent_classifier")

    # Intent Classifier → RAG Retrieval (always, no scope gating)
    workflow.add_edge("intent_classifier", "rag_retrieval")

    # RAG Retrieval → LLM Response
    workflow.add_edge("rag_retrieval", "llm_response")

    # LLM Response → Tool Execution or Memory Update
    workflow.add_conditional_edges(
        "llm_response",
        route_after_llm,
        {
            "tool_execution": "tool_execution",
            "memory_update": "memory_update",
        },
    )

    # Tool Execution → back to LLM for final synthesis
    workflow.add_edge("tool_execution", "llm_response")

    # Memory Update → Trace Logger
    workflow.add_edge("memory_update", "trace_logger")

    # Trace Logger → END
    workflow.add_edge("trace_logger", END)

    return workflow.compile()


# Singleton compiled graph
_graph = None


def get_graph():
    """Get or create the compiled graph singleton."""
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
