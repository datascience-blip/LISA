"""
Database Models and Memory Store for LISA AI
SQLAlchemy models for users, sessions, messages, and feedback
Supports both PostgreSQL and SQLite
"""

import uuid
import json
from datetime import datetime, timedelta

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


def _uuid():
    return str(uuid.uuid4())


# ═══════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    partner_type = db.Column(db.String(50), default="MFD")  # MFD, wealth_platform, admin
    partner_name = db.Column(db.String(255), default="")
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sessions = db.relationship("ChatSession", backref="user", lazy="dynamic",
                               cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class ChatSession(db.Model):
    __tablename__ = "sessions"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(255), default="New Chat")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    messages = db.relationship("Message", backref="session", lazy="dynamic",
                               cascade="all, delete-orphan",
                               order_by="Message.created_at")


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    session_id = db.Column(db.String(36), db.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    intent = db.Column(db.String(50), default="")
    is_in_scope = db.Column(db.Boolean, default=True)
    confidence = db.Column(db.Float, default=0.0)
    retrieved_docs_json = db.Column(db.Text, default="[]")  # JSON string
    token_count = db.Column(db.Integer, default=0)
    latency_ms = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    feedback = db.relationship("Feedback", backref="message", lazy="dynamic",
                               cascade="all, delete-orphan")

    @property
    def retrieved_docs(self):
        try:
            return json.loads(self.retrieved_docs_json) if self.retrieved_docs_json else []
        except json.JSONDecodeError:
            return []


class Feedback(db.Model):
    __tablename__ = "feedback"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    message_id = db.Column(db.String(36), db.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rating = db.Column(db.SmallInteger, nullable=False)  # 1 = thumbs up, -1 = thumbs down
    comment = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def save_message(session_id, user_query, assistant_response, intent="",
                 retrieved_docs=None, trace_metadata=None):
    """Save a conversation turn (user + assistant messages) to the database."""
    if not session_id:
        return

    try:
        # Save user message
        user_msg = Message(
            session_id=session_id,
            role="user",
            content=user_query,
        )
        db.session.add(user_msg)

        # Save assistant message
        docs_json = json.dumps(
            [{"text": d.get("text", "")[:200], "score": float(d.get("score", 0))}
             for d in (retrieved_docs or [])[:5]]
        )
        latency = (trace_metadata or {}).get("llm_latency_ms", 0)

        assistant_msg = Message(
            session_id=session_id,
            role="assistant",
            content=assistant_response,
            intent=intent,
            retrieved_docs_json=docs_json,
            latency_ms=latency,
        )
        db.session.add(assistant_msg)

        # Auto-title session from first user message
        session = ChatSession.query.get(session_id)
        if session and session.title == "New Chat":
            session.title = user_query[:80] + ("..." if len(user_query) > 80 else "")
            session.updated_at = datetime.utcnow()

        db.session.commit()
        return assistant_msg.id

    except Exception:
        db.session.rollback()
        raise


def get_conversation_history(session_id, limit=20):
    """Get recent messages for a session as a list of dicts."""
    messages = (
        Message.query
        .filter_by(session_id=session_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
        .all()
    )
    # Reverse to chronological order
    messages.reverse()
    return [{"role": msg.role, "content": msg.content} for msg in messages]
