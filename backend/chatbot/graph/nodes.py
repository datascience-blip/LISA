"""
LangGraph Node Functions for LISA AI
Each node receives and returns GraphState

Simplified flow (no ML model):
  User Query → Intent Classifier (LLM) → RAG Retrieval (FAISS) → LLM Response → Memory → Trace
"""

import json
import time
import logging
import threading

from .state import GraphState
from ..prompts.system import (
    LISA_SYSTEM_PROMPT,
    INTENT_CLASSIFIER_PROMPT,
    QUERY_SUPPORT_PROMPT,
    CONTENT_GENERATION_PROMPT,
    BEHAVIOUR_DISCOVERY_PROMPT,
    REGENERATION_INSTRUCTION,
)

logger = logging.getLogger(__name__)

# Lazy-loaded globals with thread-safe initialization
_llm = None
_creative_llm = None
_retriever = None
_reranker = None
_init_lock = threading.Lock()


def _create_llm(temperature: float):
    """Create an LLM instance based on configured provider."""
    from config.config import Config
    provider = Config.LLM_PROVIDER.lower()

    if provider == "bedrock":
        from langchain_aws import ChatBedrock
        return ChatBedrock(
            model_id=Config.BEDROCK_LLM_MODEL,
            region_name=Config.AWS_REGION,
            model_kwargs={"temperature": temperature},
        )
    elif provider == "openai" and Config.OPENAI_API_KEY:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=Config.LLM_MODEL,
            temperature=temperature,
            api_key=Config.OPENAI_API_KEY,
        )
    elif provider == "gemini" and Config.GEMINI_API_KEY:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=Config.GEMINI_MODEL,
            temperature=temperature,
            google_api_key=Config.GEMINI_API_KEY,
            convert_system_message_to_human=True,
        )
    else:
        raise RuntimeError(
            f"LLM provider '{provider}' not configured. "
            "Set LLM_PROVIDER and the corresponding credentials in .env"
        )


def _get_llm():
    """Lazy-load the LLM (thread-safe)."""
    global _llm
    if _llm is None:
        with _init_lock:
            if _llm is None:
                _llm = _create_llm(temperature=0.3)
    return _llm


def _get_creative_llm():
    """Lazy-load a higher-temperature LLM for regeneration (thread-safe)."""
    global _creative_llm
    if _creative_llm is None:
        with _init_lock:
            if _creative_llm is None:
                _creative_llm = _create_llm(temperature=0.85)
    return _creative_llm


def _get_retriever():
    """Lazy-load the FAISS retriever (thread-safe)."""
    global _retriever
    if _retriever is None:
        with _init_lock:
            if _retriever is None:
                from ..rag.retriever import HybridRetriever
                from config.config import Config
                _retriever = HybridRetriever(Config.VECTOR_DB_PATH, Config.EMBEDDING_MODEL)
    return _retriever


def _get_reranker():
    """Lazy-load the cross-encoder reranker (thread-safe)."""
    global _reranker
    if _reranker is None:
        with _init_lock:
            if _reranker is None:
                from ..rag.reranker import CrossEncoderReranker
                _reranker = CrossEncoderReranker()
    return _reranker


def _format_history(conversation_history):
    """Format conversation history for prompt."""
    if not conversation_history:
        return "No previous conversation."
    lines = []
    for msg in conversation_history[-6:]:  # Last 6 messages
        role = msg.get("role", "user").capitalize()
        lines.append(f"{role}: {msg.get('content', '')}")
    return "\n".join(lines)


def _format_documents(documents):
    """Format retrieved documents for prompt."""
    if not documents:
        return "No relevant documents found."
    parts = []
    for i, doc in enumerate(documents, 1):
        metadata = doc.get("metadata", {})
        source = metadata.get("source", "Unknown")
        topic = metadata.get("topic", "General")
        text = doc.get("text", doc.get("page_content", ""))
        parts.append(f"[Document {i}] (Source: {source}, Topic: {topic})\n{text}")
    return "\n\n".join(parts)


# ═══════════════════════════════════════════════════════════════
# NODE 1: Intent Classifier (LLM-only, no ML model)
# ═══════════════════════════════════════════════════════════════
def intent_classifier_node(state: GraphState) -> GraphState:
    """
    Classify user intent using LLM only.
    Categories: query_support, content_generation, behaviour_discovery
    """
    start_time = time.time()

    try:
        query = state["query"]
        llm = _get_llm()
        history_str = _format_history(state.get("conversation_history", []))
        prompt = INTENT_CLASSIFIER_PROMPT.format(query=query, history=history_str)

        response = llm.invoke(prompt)
        content = response.content.strip()

        # Handle markdown code blocks from LLM
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        parsed = json.loads(content)
        state["intent"] = parsed.get("intent", "query_support")
        state["intent_confidence"] = parsed.get("confidence", 0.8)

    except json.JSONDecodeError:
        # Fallback to query_support if LLM didn't return valid JSON
        state["intent"] = "query_support"
        state["intent_confidence"] = 0.7
    except Exception as e:
        logger.error(f"Intent classification error: {e}")
        state["intent"] = "query_support"
        state["intent_confidence"] = 0.5

    state["trace_metadata"] = {
        **state.get("trace_metadata", {}),
        "classification_latency_ms": int((time.time() - start_time) * 1000),
        "intent": state["intent"],
    }
    return state


# ═══════════════════════════════════════════════════════════════
# NODE 2: RAG Retrieval (FAISS)
# ═══════════════════════════════════════════════════════════════
def rag_retrieval_node(state: GraphState) -> GraphState:
    """
    Search FAISS vector store for relevant documents.
    Optionally re-rank results with cross-encoder.
    """
    start_time = time.time()

    try:
        query = state["query"]
        from config.config import Config

        retriever = _get_retriever()
        raw_docs = retriever.retrieve(query, top_k=Config.TOP_K)

        state["retrieved_documents"] = [
            {
                "text": doc.page_content,
                "metadata": doc.metadata,
                "score": score,
            }
            for doc, score in raw_docs
        ]

        # Re-ranking
        if Config.RERANK_ENABLED and len(state["retrieved_documents"]) > 1:
            try:
                reranker = _get_reranker()
                state["reranked_documents"] = reranker.rerank(
                    query, state["retrieved_documents"], top_k=Config.TOP_K
                )
            except Exception:
                logger.warning("Reranker not available, using original order")
                state["reranked_documents"] = state["retrieved_documents"]
        else:
            state["reranked_documents"] = state["retrieved_documents"]

    except Exception as e:
        logger.error(f"RAG retrieval error: {e}")
        state["error"] = f"Retrieval error: {str(e)}"
        state["retrieved_documents"] = []
        state["reranked_documents"] = []

    state["trace_metadata"] = {
        **state.get("trace_metadata", {}),
        "retrieval_latency_ms": int((time.time() - start_time) * 1000),
        "num_retrieved": len(state.get("retrieved_documents", [])),
        "num_reranked": len(state.get("reranked_documents", [])),
    }
    return state


# ═══════════════════════════════════════════════════════════════
# NODE 3: LLM Response
# ═══════════════════════════════════════════════════════════════
def llm_response_node(state: GraphState) -> GraphState:
    """
    Generate response using LLM with RAG context.
    The RAG documents are injected into the prompt so the LLM answers based on them.
    """
    start_time = time.time()

    try:
        is_regenerate = state.get("regenerate", False)
        # Use higher-temperature LLM for regeneration to ensure different output
        llm = _get_creative_llm() if is_regenerate else _get_llm()

        query = state["query"]
        intent = state.get("intent", "query_support")
        history_str = _format_history(state.get("conversation_history", []))
        context_str = _format_documents(state.get("reranked_documents", []))

        # Select prompt template based on intent
        if intent == "content_generation":
            user_prompt = CONTENT_GENERATION_PROMPT.format(
                context=context_str, history=history_str, query=query
            )
        elif intent == "behaviour_discovery":
            user_prompt = BEHAVIOUR_DISCOVERY_PROMPT.format(
                context=context_str, history=history_str, query=query
            )
        else:
            user_prompt = QUERY_SUPPORT_PROMPT.format(
                context=context_str, history=history_str, query=query
            )

        # Append regeneration instruction so the LLM produces a different output
        if is_regenerate:
            user_prompt += REGENERATION_INSTRUCTION

        from langchain_core.messages import SystemMessage, HumanMessage

        messages = [
            SystemMessage(content=LISA_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        # Only bind tools for behaviour_discovery intent.
        # For content_generation and query_support, the RAG context already
        # provides the promotion material / product data — no extra tool call needed.
        use_tools = intent == "behaviour_discovery"

        if use_tools:
            from ..tools import get_tools
            tools = get_tools()
            if tools:
                llm_with_tools = llm.bind_tools(tools)
                response = llm_with_tools.invoke(messages)

                if hasattr(response, "tool_calls") and response.tool_calls:
                    tool_call = response.tool_calls[0]
                    state["tool_name"] = tool_call["name"]
                    state["tool_input"] = tool_call["args"]
                    state["response"] = ""
                    return state
            else:
                response = llm.invoke(messages)
        else:
            response = llm.invoke(messages)

        state["response"] = response.content
        state["needs_clarification"] = False
        state["tool_name"] = None

    except Exception as e:
        logger.error(f"LLM response error: {e}")
        state["error"] = f"Response generation error: {str(e)}"
        state["response"] = "I apologize, but I encountered an error generating a response. Please try again."

    state["trace_metadata"] = {
        **state.get("trace_metadata", {}),
        "llm_latency_ms": int((time.time() - start_time) * 1000),
        "intent_used": state.get("intent", ""),
    }
    return state


# ═══════════════════════════════════════════════════════════════
# NODE 3b: Tool Execution
# ═══════════════════════════════════════════════════════════════
def tool_execution_node(state: GraphState) -> GraphState:
    """Execute a tool selected by the LLM and store the result."""
    try:
        from ..tools import get_tool_by_name

        tool_name = state.get("tool_name")
        tool_input = state.get("tool_input", {})

        if not tool_name:
            return state

        tool = get_tool_by_name(tool_name)
        if tool:
            result = tool.invoke(tool_input)
            state["tool_output"] = str(result)
        else:
            state["tool_output"] = f"Tool '{tool_name}' not found."

        # Reset tool_name so LLM node generates final response
        state["tool_name"] = None

    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        state["tool_output"] = f"Tool execution error: {str(e)}"
        state["tool_name"] = None

    return state


# ═══════════════════════════════════════════════════════════════
# NODE 4: Memory Update
# ═══════════════════════════════════════════════════════════════
def memory_update_node(state: GraphState) -> GraphState:
    """Save the conversation turn to the database."""
    try:
        from ..memory.store import save_message

        msg_id = save_message(
            session_id=state.get("session_id", ""),
            user_query=state["query"],
            assistant_response=state.get("response", ""),
            intent=state.get("intent", ""),
            retrieved_docs=state.get("reranked_documents", []),
            trace_metadata=state.get("trace_metadata", {}),
        )
        state["memory_updated"] = True
        state["message_id"] = msg_id
    except Exception as e:
        logger.warning(f"Memory update failed (non-critical): {e}")
        state["memory_updated"] = False

    return state


# ═══════════════════════════════════════════════════════════════
# NODE 5: Trace Logger
# ═══════════════════════════════════════════════════════════════
def trace_logger_node(state: GraphState) -> GraphState:
    """Log metrics to LangSmith for observability."""
    try:
        from ..tracing.callbacks import log_trace

        log_trace(
            user_intent=state.get("intent", ""),
            num_docs=len(state.get("reranked_documents", [])),
            response_length=len(state.get("response", "")),
            trace_metadata=state.get("trace_metadata", {}),
        )
    except Exception as e:
        logger.debug(f"Trace logging skipped: {e}")

    return state
