"""
API Routes for LISA AI
Chat, sessions, feedback, and health endpoints
"""

import json
import time
from datetime import datetime

from flask import Blueprint, request, jsonify, Response, stream_with_context
from flask_login import current_user

from ..auth.middleware import api_login_required
from ..memory.store import db, ChatSession, Message, Feedback, get_conversation_history

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _run_graph(query, user_id, session_id, conversation_history, regenerate=False):
    """Execute the LangGraph workflow and return final state."""
    from ..graph.builder import get_graph

    graph = get_graph()
    initial_state = {
        "query": query,
        "user_id": user_id,
        "session_id": session_id,
        "conversation_history": conversation_history,
        "intent": "",
        "intent_confidence": 0.0,
        "retrieved_documents": [],
        "reranked_documents": [],
        "tool_name": None,
        "tool_input": None,
        "tool_output": None,
        "response": "",
        "needs_clarification": False,
        "regenerate": regenerate,
        "memory_updated": False,
        "message_id": None,
        "trace_metadata": {},
        "error": None,
    }

    return graph.invoke(initial_state)


# ═══════════════════════════════════════════════════════════════
# CHAT ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@api_bp.route("/chat", methods=["POST"])
@api_login_required
def chat():
    """Send a message and get a response."""
    data = request.get_json()
    query = (data.get("query") or "").strip()
    session_id = data.get("session_id")

    if not query:
        return jsonify({"error": "Query cannot be empty"}), 400

    # Create session if not provided
    if not session_id:
        session = ChatSession(user_id=current_user.id)
        db.session.add(session)
        db.session.commit()
        session_id = session.id

    # Get conversation history
    history = get_conversation_history(session_id, limit=10)

    # Run the graph
    start_time = time.time()
    final_state = _run_graph(query, current_user.id, session_id, history)
    total_ms = int((time.time() - start_time) * 1000)

    if final_state.get("error"):
        return jsonify({"error": final_state["error"]}), 500

    # Format documents for frontend
    documents = []
    for doc in final_state.get("reranked_documents", []):
        documents.append({
            "text": doc.get("text", "")[:300],
            "category": doc.get("metadata", {}).get("category",
                        doc.get("metadata", {}).get("topic", "General")),
            "source": doc.get("metadata", {}).get("source", ""),
            "score": round(float(doc.get("score", doc.get("rerank_score", 0))), 4),
        })

    return jsonify({
        "success": True,
        "session_id": session_id,
        "message_id": final_state.get("message_id"),
        "response": final_state.get("response", ""),
        "classification": {
            "intent": final_state.get("intent", ""),
            "intent_confidence": round(float(final_state.get("intent_confidence", 0)) * 100, 2),
        },
        "documents": documents,
        "latency_ms": total_ms,
    })


@api_bp.route("/chat/regenerate", methods=["POST"])
@api_login_required
def regenerate():
    """Regenerate the last assistant response for a session."""
    data = request.get_json()
    session_id = data.get("session_id")

    if not session_id:
        return jsonify({"error": "session_id required"}), 400

    # Find the last user message
    last_user_msg = (
        Message.query
        .filter_by(session_id=session_id, role="user")
        .order_by(Message.created_at.desc())
        .first()
    )
    if not last_user_msg:
        return jsonify({"error": "No messages to regenerate"}), 400

    # Delete the last assistant message
    last_assistant_msg = (
        Message.query
        .filter_by(session_id=session_id, role="assistant")
        .order_by(Message.created_at.desc())
        .first()
    )
    if last_assistant_msg:
        db.session.delete(last_assistant_msg)
        db.session.commit()

    # Re-run the graph with the last user query (regenerate=True for variation)
    history = get_conversation_history(session_id, limit=10)
    start_time = time.time()
    final_state = _run_graph(last_user_msg.content, current_user.id, session_id, history, regenerate=True)
    total_ms = int((time.time() - start_time) * 1000)

    return jsonify({
        "success": True,
        "session_id": session_id,
        "response": final_state.get("response", ""),
        "latency_ms": total_ms,
    })


# ═══════════════════════════════════════════════════════════════
# SESSION ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@api_bp.route("/sessions", methods=["GET"])
@api_login_required
def list_sessions():
    """List all chat sessions for the current user."""
    sessions = (
        ChatSession.query
        .filter_by(user_id=current_user.id, is_active=True)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    return jsonify({
        "sessions": [
            {
                "id": s.id,
                "title": s.title,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
            }
            for s in sessions
        ]
    })


@api_bp.route("/sessions", methods=["POST"])
@api_login_required
def create_session():
    """Create a new chat session."""
    session = ChatSession(user_id=current_user.id)
    db.session.add(session)
    db.session.commit()
    return jsonify({
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at.isoformat(),
    }), 201


@api_bp.route("/sessions/<session_id>/messages", methods=["GET"])
@api_login_required
def get_messages(session_id):
    """Get all messages for a session."""
    session = ChatSession.query.get(session_id)
    if not session or session.user_id != current_user.id:
        return jsonify({"error": "Session not found"}), 404

    messages = (
        Message.query
        .filter_by(session_id=session_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return jsonify({
        "session_id": session_id,
        "title": session.title,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "intent": m.intent,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    })


@api_bp.route("/sessions/<session_id>", methods=["DELETE"])
@api_login_required
def delete_session(session_id):
    """Delete (soft) a chat session."""
    session = ChatSession.query.get(session_id)
    if not session or session.user_id != current_user.id:
        return jsonify({"error": "Session not found"}), 404

    session.is_active = False
    db.session.commit()
    return jsonify({"success": True})


@api_bp.route("/sessions/search", methods=["GET"])
@api_login_required
def search_sessions():
    """Search across chat history."""
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"results": []})

    # Search in message content
    matching_messages = (
        Message.query
        .join(ChatSession)
        .filter(
            ChatSession.user_id == current_user.id,
            ChatSession.is_active == True,
            Message.content.ilike(f"%{q}%"),
        )
        .order_by(Message.created_at.desc())
        .limit(20)
        .all()
    )

    # Group by session
    sessions_seen = set()
    results = []
    for msg in matching_messages:
        if msg.session_id not in sessions_seen:
            sessions_seen.add(msg.session_id)
            results.append({
                "session_id": msg.session_id,
                "title": msg.session.title,
                "snippet": msg.content[:150],
                "role": msg.role,
                "created_at": msg.created_at.isoformat(),
            })

    return jsonify({"results": results})


@api_bp.route("/sessions/<session_id>/export", methods=["GET"])
@api_login_required
def export_session(session_id):
    """Export a chat session as JSON or text."""
    session = ChatSession.query.get(session_id)
    if not session or session.user_id != current_user.id:
        return jsonify({"error": "Session not found"}), 404

    fmt = request.args.get("format", "json")
    messages = (
        Message.query
        .filter_by(session_id=session_id)
        .order_by(Message.created_at.asc())
        .all()
    )

    if fmt == "text":
        lines = [f"LISA AI Chat - {session.title}\n{'=' * 40}\n"]
        for m in messages:
            role = "You" if m.role == "user" else "LISA"
            lines.append(f"\n{role}:\n{m.content}\n")
        return Response("\n".join(lines), mimetype="text/plain",
                        headers={"Content-Disposition": f"attachment; filename=lisa_chat_{session_id[:8]}.txt"})

    return jsonify({
        "session": {
            "id": session.id,
            "title": session.title,
            "created_at": session.created_at.isoformat(),
        },
        "messages": [
            {"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
            for m in messages
        ],
    })


# ═══════════════════════════════════════════════════════════════
# FEEDBACK ENDPOINT
# ═══════════════════════════════════════════════════════════════

@api_bp.route("/feedback", methods=["POST"])
@api_login_required
def submit_feedback():
    """Submit thumbs up/down feedback for a message."""
    data = request.get_json()
    message_id = data.get("message_id")
    rating = data.get("rating")  # 1 or -1

    if not message_id or rating not in (1, -1):
        return jsonify({"error": "message_id and rating (1 or -1) required"}), 400

    message = Message.query.get(message_id)
    if not message:
        return jsonify({"error": "Message not found"}), 404

    # Check if feedback already exists, update if so
    existing = Feedback.query.filter_by(
        message_id=message_id, user_id=current_user.id
    ).first()

    if existing:
        existing.rating = rating
        existing.comment = data.get("comment", "")
    else:
        feedback = Feedback(
            message_id=message_id,
            user_id=current_user.id,
            rating=rating,
            comment=data.get("comment", ""),
        )
        db.session.add(feedback)

    db.session.commit()

    # Log to LangSmith if available
    try:
        from ..tracing.callbacks import log_feedback
        log_feedback(message_id, rating)
    except Exception:
        pass

    return jsonify({"success": True})


# ═══════════════════════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════════════════════

@api_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint (no auth required)."""
    from config.config import Config

    return jsonify({
        "status": "healthy",
        "llm_provider": "openai" if Config.OPENAI_API_KEY else ("gemini" if Config.GEMINI_API_KEY else "none"),
        "llm_model": Config.LLM_MODEL if Config.OPENAI_API_KEY else Config.GEMINI_MODEL,
        "vector_db": "FAISS",
        "langsmith_enabled": Config.LANGCHAIN_TRACING_V2 == "true" and bool(Config.LANGSMITH_API_KEY),
    })
