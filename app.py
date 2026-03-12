#!/usr/bin/env python3
"""
LISA AI - Lark Intelligent Support Assistant
Root entry point - wrapper for backend app

Usage:
    python app.py
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir.parent))
sys.path.insert(0, str(backend_dir))

from app import create_app, Config

if __name__ == "__main__":
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
