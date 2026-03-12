"""
Authentication Routes for LISA AI
Login, logout, and session management
"""

from flask import Blueprint, request, redirect, url_for, render_template, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from ..memory.store import db, User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Partner login page."""
    if current_user.is_authenticated:
        return redirect(url_for("main.chat"))

    if request.method == "GET":
        return render_template("login.html")

    # POST: validate credentials
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if not username or not password:
        flash("Please enter both username and password.", "error")
        return render_template("login.html")

    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password) and user.is_active:
        login_user(user, remember=True)
        next_page = request.args.get("next")
        return redirect(next_page or url_for("main.chat"))

    flash("Invalid username or password.", "error")
    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    """Logout and redirect to login page."""
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/api/auth/status")
def auth_status():
    """Check authentication status (for frontend)."""
    if current_user.is_authenticated:
        return jsonify({
            "authenticated": True,
            "user": {
                "id": current_user.id,
                "username": current_user.username,
                "partner_type": current_user.partner_type,
                "partner_name": current_user.partner_name,
            }
        })
    return jsonify({"authenticated": False}), 401
