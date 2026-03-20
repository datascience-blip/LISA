"""
Document Ingestion Pipeline for LISA AI
Loads documents from data/, chunks them, embeds with OpenAI, and builds FAISS index
"""

import os
import logging
from pathlib import Path
from typing import List

from langchain_community.document_loaders import TextLoader, CSVLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# Metadata mapping: filename → topic/partner_type tags
FILE_METADATA = {
    "Lark_Finserv_Company_Information.txt": {
        "topic": "company_info",
        "partner_type": "all",
    },
    "Master_Training_Document_Query_Classification.txt": {
        "topic": "product_overview",
        "partner_type": "all",
    },
    "AI_B2C_RAG_Optimized.txt": {
        "topic": "product_faq",
        "partner_type": "all",
    },
    "Lender_Partner_Documentation.txt": {
        "topic": "lender_partners",
        "partner_type": "all",
    },
    "Cleaned_Promotion_Material.txt": {
        "topic": "marketing",
        "partner_type": "MFD",
    },
    "Promotion Material.txt": {
        "topic": "marketing",
        "partner_type": "MFD",
    },
    "ABFL Tata Offline LAS.txt": {
        "topic": "phygital_process",
        "partner_type": "phygital",
    },
}


def load_documents(data_dir: str) -> List[Document]:
    """Load all documents from the data directory with enriched metadata."""
    data_path = Path(data_dir)
    all_docs = []

    for file_path in sorted(data_path.iterdir()):
        if file_path.name.startswith(".") or file_path.name == "README.md":
            continue

        try:
            if file_path.suffix == ".txt":
                loader = TextLoader(str(file_path), encoding="utf-8")
                docs = loader.load()
            elif file_path.suffix == ".csv":
                loader = CSVLoader(
                    str(file_path),
                    csv_args={"delimiter": ","},
                    encoding="utf-8",
                )
                docs = loader.load()
            else:
                continue

            # Enrich metadata
            file_meta = FILE_METADATA.get(file_path.name, {})
            for doc in docs:
                doc.metadata.update({
                    "source": file_path.name,
                    "file_type": file_path.suffix.lstrip("."),
                    "topic": file_meta.get("topic", "general"),
                    "partner_type": file_meta.get("partner_type", "all"),
                })

            all_docs.extend(docs)
            logger.info(f"Loaded {len(docs)} document(s) from {file_path.name}")

        except Exception as e:
            logger.error(f"Error loading {file_path.name}: {e}")

    logger.info(f"Total documents loaded: {len(all_docs)}")
    return all_docs


def chunk_documents(
    documents: List[Document],
    chunk_size: int = 500,
    chunk_overlap: int = 100,
) -> List[Document]:
    """Split documents into chunks with metadata preserved."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=[
            "\n====",  # Major section breaks in LISA docs
            "\n----",  # Minor section breaks
            "\n\n",    # Paragraph breaks
            "\n",      # Line breaks
            ". ",      # Sentence breaks
            " ",       # Word breaks
        ],
        length_function=len,
    )

    chunks = splitter.split_documents(documents)
    logger.info(f"Created {len(chunks)} chunks from {len(documents)} documents")
    return chunks


def _get_embeddings(embedding_model: str, openai_api_key: str = "", gemini_api_key: str = ""):
    """Get embeddings model based on LLM_PROVIDER config. Falls back to explicit keys."""
    from config.config import Config
    provider = Config.LLM_PROVIDER.lower()

    if provider == "bedrock":
        from langchain_aws import BedrockEmbeddings
        logger.info(f"Using Bedrock embeddings: {Config.BEDROCK_EMBEDDING_MODEL}")
        return BedrockEmbeddings(
            model_id=Config.BEDROCK_EMBEDDING_MODEL,
            region_name=Config.AWS_REGION,
        )
    elif openai_api_key or (provider == "openai" and Config.OPENAI_API_KEY):
        from langchain_openai import OpenAIEmbeddings
        key = openai_api_key or Config.OPENAI_API_KEY
        logger.info(f"Using OpenAI embeddings: {embedding_model}")
        return OpenAIEmbeddings(model=embedding_model, api_key=key)
    elif gemini_api_key or (provider == "gemini" and Config.GEMINI_API_KEY):
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        key = gemini_api_key or Config.GEMINI_API_KEY
        gemini_model = "models/gemini-embedding-001"
        logger.info(f"Using Gemini embeddings: {gemini_model}")
        return GoogleGenerativeAIEmbeddings(
            model=gemini_model,
            google_api_key=key,
        )
    else:
        raise RuntimeError("No embeddings provider configured. Set LLM_PROVIDER in .env")


def build_faiss_index(
    chunks: List[Document],
    embedding_model: str,
    output_path: str,
    openai_api_key: str = "",
    gemini_api_key: str = "",
):
    """Build FAISS vector index from document chunks, with rate-limit handling for Gemini."""
    import time
    from langchain_community.vectorstores import FAISS

    embeddings = _get_embeddings(embedding_model, openai_api_key, gemini_api_key)

    logger.info(f"Building FAISS index with {len(chunks)} chunks...")

    # For Gemini: process in small batches with retry to handle rate limits
    if gemini_api_key and not openai_api_key:
        batch_size = 20  # ~1 API call per batch, stays under 100 req/min naturally
        vectorstore = None
        total_batches = (len(chunks) + batch_size - 1) // batch_size

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            batch_num = i // batch_size + 1

            for attempt in range(10):
                try:
                    logger.info(f"  Batch {batch_num}/{total_batches} ({len(batch)} chunks)...")
                    if vectorstore is None:
                        vectorstore = FAISS.from_documents(batch, embeddings)
                    else:
                        batch_vs = FAISS.from_documents(batch, embeddings)
                        vectorstore.merge_from(batch_vs)
                    break
                except Exception as e:
                    err_str = str(e)
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "ConnectError" in err_str or "nodename" in err_str:
                        wait_time = 60 if "429" in err_str else 10
                        logger.warning(f"  Retry {attempt + 1}/10 - waiting {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        raise
            else:
                logger.error(f"  Failed batch {batch_num} after 10 attempts, skipping...")

            # Save checkpoint every 25 batches
            if batch_num % 25 == 0 and vectorstore:
                output = Path(output_path)
                output.mkdir(parents=True, exist_ok=True)
                vectorstore.save_local(str(output))
                logger.info(f"  Checkpoint saved at batch {batch_num}")
    else:
        vectorstore = FAISS.from_documents(chunks, embeddings)

    # Save to disk
    output = Path(output_path)
    output.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(output))
    logger.info(f"FAISS index saved to {output_path}")

    return vectorstore


def run_ingestion(data_dir: str, output_path: str, embedding_model: str,
                  openai_api_key: str = "", gemini_api_key: str = "",
                  chunk_size: int = 500, chunk_overlap: int = 100):
    """Full ingestion pipeline: load → chunk → embed → index."""
    docs = load_documents(data_dir)
    chunks = chunk_documents(docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    vectorstore = build_faiss_index(chunks, embedding_model, output_path, openai_api_key, gemini_api_key)
    return vectorstore
