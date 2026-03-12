#!/usr/bin/env python3
"""
Seed Users Script for LISA AI
Creates initial partner accounts for testing.

Usage:
    python rag/scripts/seed_users.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))
sys.path.insert(0, str(project_root))

from app import create_app
from chatbot.memory.store import db, User


SEED_USERS = [
    {
        "username": "admin",
        "email": "admin@larkfinserv.com",
        "password": "admin123",
        "partner_type": "admin",
        "partner_name": "Lark Finserv",
    },
    {
        "username": "demo_mfd",
        "email": "demo@mfd.com",
        "password": "demo123",
        "partner_type": "MFD",
        "partner_name": "Demo MFD Partner",
    },
    {
        "username": "demo_wealth",
        "email": "demo@wealth.com",
        "password": "demo123",
        "partner_type": "wealth_platform",
        "partner_name": "Demo Wealth Platform",
    },
]


def main():
    app = create_app()
    with app.app_context():
        db.create_all()

        for user_data in SEED_USERS:
            existing = User.query.filter_by(username=user_data["username"]).first()
            if existing:
                print(f"User '{user_data['username']}' already exists, skipping.")
                continue

            user = User(
                username=user_data["username"],
                email=user_data["email"],
                partner_type=user_data["partner_type"],
                partner_name=user_data["partner_name"],
            )
            user.set_password(user_data["password"])
            db.session.add(user)
            print(f"Created user: {user_data['username']} ({user_data['partner_type']})")

        db.session.commit()
        print("\nSeed users created successfully!")
        print("\nLogin credentials:")
        for u in SEED_USERS:
            print(f"  Username: {u['username']}  Password: {u['password']}")


if __name__ == "__main__":
    main()
