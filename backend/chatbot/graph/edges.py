"""
LangGraph Edge Functions for LISA AI
Conditional routing logic between nodes
"""

from .state import GraphState


def route_after_llm(state: GraphState) -> str:
    """After LLM response, decide if tool calling is needed."""
    if state.get("tool_name"):
        return "tool_execution"
    return "memory_update"
