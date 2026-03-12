"""
Authentication Middleware for LISA AI
Decorators for protecting API routes
"""

from functools import wraps
from flask import jsonify
from flask_login import current_user


def api_login_required(f):
    """Decorator for API routes: returns 401 JSON instead of redirect."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated
