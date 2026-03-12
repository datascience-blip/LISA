"""
LISA AI - Lark Intelligent Support Assistant
Flask Application Factory
"""

import os
import sys
from pathlib import Path
from datetime import timedelta

# Fix OpenMP duplicate library crash (FAISS + sentence-transformers both load libomp)
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from flask import Flask, redirect, url_for, render_template
from flask_login import login_required, current_user

# Add project root and config to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from config.config import Config  # noqa: E402 — make Config importable from this module


def create_app(config_class=None):
    """Flask application factory."""
    _root = Path(__file__).parent.parent
    _frontend = _root / "frontend"
    app = Flask(
        __name__,
        template_folder=str(_frontend / "templates"),
        static_folder=str(_frontend / "static"),
        instance_path=str(_root / "instance"),
    )

    # Load config
    if config_class is None:
        from config.config import Config
        config_class = Config
    app.config.from_object(config_class)

    # Session config
    app.config["REMEMBER_COOKIE_DURATION"] = timedelta(seconds=config_class.SESSION_TIMEOUT)

    # ─── Initialize extensions ───
    from chatbot.memory.store import db
    db.init_app(app)

    from chatbot.auth.models import login_manager
    login_manager.init_app(app)

    # ─── Register blueprints ───
    from chatbot.auth.routes import auth_bp
    from chatbot.api.routes import api_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)

    # ─── Page routes ───
    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("main.chat"))
        return redirect(url_for("auth.login"))

    # Main blueprint for authenticated pages
    from flask import Blueprint
    main_bp = Blueprint("main", __name__)

    @main_bp.route("/chat")
    @login_required
    def chat():
        return render_template("chat.html")

    app.register_blueprint(main_bp)

    # ─── Create tables on first request ───
    with app.app_context():
        db.create_all()

    return app


# ═══════════════════════════════════════════════════════════════
# Run the application
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from config.config import Config

    app = create_app()

    print("=" * 60)
    print("  LISA AI - Lark Intelligent Support Assistant")
    print("=" * 60)
    print(f"  LLM Provider : {'OpenAI' if Config.OPENAI_API_KEY else ('Gemini' if Config.GEMINI_API_KEY else 'NONE')}")
    print(f"  LLM Model    : {Config.LLM_MODEL if Config.OPENAI_API_KEY else Config.GEMINI_MODEL}")
    print(f"  Vector DB    : FAISS ({Config.VECTOR_DB_PATH})")
    print(f"  Database     : {Config.DATABASE_URL.split('://')[0]}")
    print(f"  LangSmith    : {'Enabled' if Config.LANGSMITH_API_KEY else 'Disabled'}")
    print(f"  Server       : http://localhost:{Config.PORT}")
    print("=" * 60)

    app.run(
        debug=Config.DEBUG,
        host=Config.HOST,
        port=Config.PORT,
        threaded=True,
    )