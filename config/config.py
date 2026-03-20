"""
LISA AI - Centralized Configuration
Loads all settings from .env file with sensible defaults
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent  # project root


class Config:
    # --- LLM Provider: "bedrock", "openai", or "gemini" ---
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "bedrock")

    # --- AWS Bedrock ---
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    BEDROCK_LLM_MODEL = os.getenv("BEDROCK_LLM_MODEL", "anthropic.claude-sonnet-4-6-20250514")
    BEDROCK_EMBEDDING_MODEL = os.getenv("BEDROCK_EMBEDDING_MODEL", "amazon.titan-embed-text-v2:0")

    # --- OpenAI (fallback) ---
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

    # --- LangChain / LangSmith ---
    LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "")
    LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "")
    LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "LISA-AI")
    LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "true")

    # --- Database ---
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'lisa.db'}")
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Authentication ---
    SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "dev-secret-change-in-production")
    SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "86400"))

    # --- RAG ---
    VECTOR_DB_PATH = str(BASE_DIR / os.getenv("VECTOR_DB_PATH", "vectorstore"))
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))
    TOP_K = int(os.getenv("TOP_K", "5"))
    RERANK_ENABLED = os.getenv("RERANK_ENABLED", "true").lower() == "true"

    # --- Flask ---
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "5001"))

    # --- Paths ---
    DATA_DIR = str(BASE_DIR / os.getenv("DATA_DIR", "data"))

    # --- Legacy Gemini (fallback if no OpenAI key) ---
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
