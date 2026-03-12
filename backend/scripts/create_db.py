#!/usr/bin/env python3
"""
Database Initialization Script for LISA AI
Creates all tables in the database.

Usage:
    python rag/scripts/create_db.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))
sys.path.insert(0, str(project_root))

from app import create_app
from chatbot.memory.store import db


def main():
    app = create_app()
    with app.app_context():
        db.create_all()
        print("Database tables created successfully!")
        print(f"Database URL: {app.config['SQLALCHEMY_DATABASE_URI']}")


if __name__ == "__main__":
    main()
