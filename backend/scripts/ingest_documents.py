#!/usr/bin/env python3
"""
Document Ingestion Script for LISA AI
Run this once to build the FAISS vector index from data/ directory.

Usage:
    python rag/scripts/ingest_documents.py
"""

import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))
sys.path.insert(0, str(project_root))

from config.config import Config
from chatbot.rag.ingest import run_ingestion

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    if not Config.OPENAI_API_KEY and not Config.GEMINI_API_KEY:
        logger.error("No API key set. Set OPENAI_API_KEY or GEMINI_API_KEY in .env")
        sys.exit(1)

    provider = "OpenAI" if Config.OPENAI_API_KEY else "Gemini"
    embed_model = Config.EMBEDDING_MODEL if Config.OPENAI_API_KEY else "models/embedding-001"

    logger.info("=" * 60)
    logger.info("LISA AI - Document Ingestion Pipeline")
    logger.info("=" * 60)
    logger.info(f"Data directory:    {Config.DATA_DIR}")
    logger.info(f"Output directory:  {Config.VECTOR_DB_PATH}")
    logger.info(f"Embedding provider:{provider}")
    logger.info(f"Embedding model:   {embed_model}")
    logger.info(f"Chunk size:        {Config.CHUNK_SIZE}")
    logger.info(f"Chunk overlap:     {Config.CHUNK_OVERLAP}")
    logger.info("=" * 60)

    vectorstore = run_ingestion(
        data_dir=Config.DATA_DIR,
        output_path=Config.VECTOR_DB_PATH,
        embedding_model=Config.EMBEDDING_MODEL,
        openai_api_key=Config.OPENAI_API_KEY,
        gemini_api_key=Config.GEMINI_API_KEY,
        chunk_size=Config.CHUNK_SIZE,
        chunk_overlap=Config.CHUNK_OVERLAP,
    )

    logger.info("=" * 60)
    logger.info("Ingestion complete! FAISS index saved.")
    logger.info(f"Index location: {Config.VECTOR_DB_PATH}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
