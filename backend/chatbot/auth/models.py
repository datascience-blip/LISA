"""
Authentication Models for LISA AI
Re-exports User model and provides login manager setup
"""

from flask_login import LoginManager
from ..memory.store import User, db

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)
