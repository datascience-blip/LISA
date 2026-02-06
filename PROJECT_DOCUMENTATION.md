# LISA AI - Project Documentation

## Project Overview

**LISA** (Lark Intelligent Support Assistant) is an AI-powered chatbot built for **Lark Finserv**.
It helps Mutual Fund Distributors (MFDs) and partners with information about **Loan Against Mutual Funds (LAMF)** and **Loan Against Securities (LAS)** products.

**Tech Stack:** Flask + LangChain + LangGraph + OpenAI (GPT-4o-mini) + FAISS + SQLAlchemy

---

## How It Works (Data Flow)

```
User Query
    |
    v
[1. Intent Classifier] -- LLM classifies query into: query_support / content_generation / behaviour_discovery
    |
    v
[2. RAG Retrieval] -- FAISS vector search finds relevant documents from data/ files
    |
    v
[3. LLM Response] -- GPT-4o-mini generates answer using retrieved documents as context
    |                    |
    |                    v (if tool needed)
    |               [3b. Tool Execution] -- Runs tool, loops back to LLM
    |
    v
[4. Memory Update] -- Saves query + response to SQLite database
    |
    v
[5. Trace Logger] -- Logs metrics to LangSmith (if enabled)
    |
    v
Response sent to User
```

---

## Startup Sequence

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create database tables
python scripts/create_db.py

# 3. Create test users (admin/admin123, demo_mfd/demo123, demo_wealth/demo123)
python scripts/seed_users.py

# 4. Build FAISS vector index from data/ files (requires OPENAI_API_KEY)
python scripts/ingest_documents.py

# 5. Start the server
KMP_DUPLICATE_LIB_OK=TRUE python app.py
# Server runs at http://localhost:5001
```

---

## File Structure & Purpose

### Root Files

| File | Purpose |
|------|---------|
| `app.py` | **Flask application factory.** Creates the Flask app, initializes database and auth extensions, registers blueprints (auth, api, main), defines the `/` and `/chat` routes. Entry point when running the server. |
| `config.py` | **Centralized configuration.** Loads all settings from `.env` file (API keys, database URL, RAG settings, Flask config). All other files import from here. |
| `.env` | **Environment variables.** Contains API keys (OpenAI, Gemini, LangSmith), database URL, RAG settings (chunk size, top_k), and Flask settings (port, debug mode). |
| `requirements.txt` | **Python dependencies.** Lists all pip packages needed: Flask, LangChain, LangGraph, FAISS, sentence-transformers, etc. |
| `.gitignore` | **Git ignore rules.** Excludes venv/, __pycache__/, .env, instance/, vectorstore/, etc. |

---

### chatbot/graph/ -- LangGraph Workflow Engine

This is the **brain** of the chatbot. It defines the AI workflow as a graph of nodes.

| File | Purpose |
|------|---------|
| `state.py` | **Graph state schema.** Defines `GraphState` TypedDict -- the data structure that flows through every node. Contains: `query`, `user_id`, `session_id`, `conversation_history`, `intent`, `intent_confidence`, `retrieved_documents`, `reranked_documents`, `tool_name`, `tool_input`, `tool_output`, `response`, `memory_updated`, `trace_metadata`, `error`. |
| `nodes.py` | **All graph node functions.** The core processing logic. Contains 6 functions: |
| | - `intent_classifier_node()` -- Uses LLM to classify user query into query_support/content_generation/behaviour_discovery |
| | - `rag_retrieval_node()` -- Searches FAISS index for relevant documents, optionally re-ranks with cross-encoder |
| | - `llm_response_node()` -- Generates the final answer using LLM + retrieved documents as context. Supports tool calling |
| | - `tool_execution_node()` -- Executes a LangChain tool if the LLM requests one |
| | - `memory_update_node()` -- Saves the conversation turn to SQLite database |
| | - `trace_logger_node()` -- Logs metrics to LangSmith for monitoring |
| | Also contains helper functions: `_get_llm()` (lazy-loads OpenAI or Gemini), `_get_retriever()`, `_get_reranker()`, `_format_history()`, `_format_documents()` |
| `builder.py` | **Graph assembly.** Connects all nodes into a LangGraph `StateGraph` workflow. Defines the flow: Intent Classifier -> RAG Retrieval -> LLM Response -> (conditional: Tool Execution loop or Memory Update) -> Trace Logger -> END. Provides `get_graph()` singleton. |
| `edges.py` | **Conditional routing.** Contains `route_after_llm()` which decides: if LLM requested a tool -> go to tool_execution, otherwise -> go to memory_update. |
| `__init__.py` | Empty init file for Python package. |

---

### chatbot/rag/ -- RAG (Retrieval Augmented Generation) Pipeline

This handles **document ingestion, vector search, and re-ranking**.

| File | Purpose |
|------|---------|
| `ingest.py` | **Document ingestion pipeline.** Loads all files from `data/` directory (TextLoader for .txt, CSVLoader for .csv), splits them into chunks (500 chars with 100 overlap), adds metadata (topic, partner_type, source), and builds a FAISS vector index. Supports both OpenAI and Gemini embeddings with rate-limit retry logic. Key functions: `load_documents()`, `chunk_documents()`, `build_faiss_index()`, `run_ingestion()`. |
| `retriever.py` | **FAISS hybrid retriever.** `HybridRetriever` class loads the FAISS index from disk, performs similarity search with scores, and supports post-hoc metadata filtering (since FAISS doesn't natively support metadata filters). Falls back to Gemini embeddings if no OpenAI key. Key method: `retrieve(query, top_k, metadata_filter)`. |
| `reranker.py` | **Cross-encoder re-ranker.** `CrossEncoderReranker` class uses the `cross-encoder/ms-marco-MiniLM-L-6-v2` model to re-score and re-order retrieved documents for better relevance. Gracefully disabled if model not available. Key method: `rerank(query, documents, top_k)`. |
| `__init__.py` | Empty init file for Python package. |

---

### chatbot/memory/ -- Database & Conversation Storage

| File | Purpose |
|------|---------|
| `store.py` | **SQLAlchemy database models and helpers.** Defines 4 models: |
| | - `User` -- Partner accounts with hashed passwords, partner_type (MFD/wealth_platform/NBFC/admin), Flask-Login integration |
| | - `ChatSession` -- Chat sessions linked to users, with title and soft-delete (is_active) |
| | - `Message` -- Individual messages (user/assistant) linked to sessions, stores intent classification |
| | - `Feedback` -- Thumbs up/down feedback linked to messages |
| | Helper functions: `save_message()` (saves a conversation turn), `get_conversation_history()` (loads last N messages for context) |
| `__init__.py` | Empty init file for Python package. |

---

### chatbot/auth/ -- Authentication System

| File | Purpose |
|------|---------|
| `models.py` | **Flask-Login setup.** Creates the `LoginManager`, sets login view to `auth.login`, defines `load_user()` callback that loads User by ID. |
| `routes.py` | **Auth routes.** Defines 3 endpoints: |
| | - `POST /login` -- Validates username/password, creates session with Flask-Login |
| | - `GET /logout` -- Logs out user and redirects to login |
| | - `GET /api/auth/status` -- Returns JSON with auth status and user info (for frontend) |
| `middleware.py` | **API auth decorator.** `api_login_required` decorator -- same as Flask-Login's `@login_required` but returns 401 JSON instead of redirecting to login page. Used on all /api/ routes. |
| `__init__.py` | Empty init file for Python package. |

---

### chatbot/api/ -- REST API Endpoints

| File | Purpose |
|------|---------|
| `routes.py` | **All API endpoints.** Defines the `api_bp` blueprint with `/api` prefix. Contains: |
| | **Chat Endpoints:** |
| | - `POST /api/chat` -- Main chat endpoint. Takes `{query, session_id?}`, runs the LangGraph workflow, returns `{response, intent, documents, latency_ms}` |
| | - `POST /api/chat/regenerate` -- Re-generates the last assistant response for a session |
| | **Session Endpoints:** |
| | - `GET /api/sessions` -- List all sessions for current user |
| | - `POST /api/sessions` -- Create a new chat session |
| | - `GET /api/sessions/<id>/messages` -- Get all messages in a session |
| | - `DELETE /api/sessions/<id>` -- Soft-delete a session |
| | - `GET /api/sessions/search?q=` -- Search across chat history |
| | - `GET /api/sessions/<id>/export?format=json|text` -- Export chat as JSON or text file |
| | **Other:** |
| | - `POST /api/feedback` -- Submit thumbs up/down on a message |
| | - `GET /api/health` -- Health check (no auth required) -- returns LLM provider, model, status |
| | Also contains `_run_graph()` helper that initializes GraphState and invokes the LangGraph workflow. |
| `__init__.py` | Empty init file for Python package. |

---

### chatbot/tools/ -- LangChain Tool Calling

These are tools the LLM can choose to call during response generation.

| File | Purpose |
|------|---------|
| `__init__.py` | **Tool registry.** Imports all 3 tools and provides `get_tools()` (returns list of all tools) and `get_tool_by_name(name)` (returns specific tool). |
| `content_generator.py` | **Marketing content tool.** `generate_marketing_content(content_type, product, target_audience, tone)` -- LLM calls this when user asks to create WhatsApp messages, emails, social media posts, or pitch scripts. Uses a separate LLM call with marketing-specific system prompt. |
| `faq_retriever.py` | **FAQ lookup tool.** `lookup_faq(question_topic)` -- Pre-built FAQ database with instant answers for: interest_rates, eligibility, documents_required, process, prepayment, loan_to_value, tenure, fees. Returns structured markdown answers with specific numbers. |
| `partner_analytics.py` | **Analytics tool.** `analyze_partner_behavior(partner_type, analysis_type)` -- Queries the database for partner interaction patterns. Supports: common_queries, objection_patterns, product_interest, engagement_metrics. Falls back to industry insights if no data. |

---

### chatbot/prompts/ -- System Prompts & Templates

| File | Purpose |
|------|---------|
| `system.py` | **All prompt templates.** Contains 5 prompts: |
| | - `LISA_SYSTEM_PROMPT` -- Main persona. Defines LISA's 4 roles: Financial Knowledge Assistant, MFD Marketing Co-Pilot, Customer Intent Analyzer, LAMF Growth Enabler. Includes critical rules (only answer from context, never fabricate). |
| | - `INTENT_CLASSIFIER_PROMPT` -- Template for classifying user intent. Takes `{query}` and `{history}`, returns JSON with intent + confidence. |
| | - `QUERY_SUPPORT_PROMPT` -- Template for answering questions. Takes `{context}` (RAG docs), `{history}`, `{query}`. |
| | - `CONTENT_GENERATION_PROMPT` -- Template for creating marketing content. |
| | - `BEHAVIOUR_DISCOVERY_PROMPT` -- Template for analytics/insights responses. |
| `__init__.py` | Empty init file for Python package. |

---

### chatbot/tracing/ -- LangSmith Observability

| File | Purpose |
|------|---------|
| `callbacks.py` | **LangSmith integration.** `log_trace()` logs metrics (intent, doc count, latency) to LangSmith. `log_feedback()` logs user feedback. Gracefully disabled if no LangSmith API key. Uses lazy-loaded LangSmith client. |
| `__init__.py` | Empty init file for Python package. |

---

### scripts/ -- Setup & Maintenance Scripts

| File | Purpose |
|------|---------|
| `create_db.py` | **Database initialization.** Creates all SQLAlchemy tables in SQLite. Run once before first use. |
| `seed_users.py` | **Test user creation.** Creates 3 demo accounts: `admin/admin123` (admin), `demo_mfd/demo123` (MFD partner), `demo_wealth/demo123` (wealth platform). |
| `ingest_documents.py` | **Document ingestion runner.** Reads all files from `data/`, chunks them, generates embeddings (OpenAI or Gemini), and builds the FAISS vector index in `vectorstore/`. Must be run before the chatbot can answer questions. |

---

### templates/ -- HTML Templates

| File | Purpose |
|------|---------|
| `login.html` | **Login page.** Dark gradient theme with username/password form. Inline CSS styling. Shows flash messages for errors. |
| `chat.html` | **Main chat interface.** ChatGPT-like layout with: sidebar (session list, search, new chat button, user info), main chat area (message bubbles with markdown rendering), input bar (text input + send button). Uses CDN for marked.js (markdown) and DOMPurify (XSS protection). Links to `chat.css` and `chat.js`. |

---

### static/ -- Frontend Assets

| File | Purpose |
|------|---------|
| `css/chat.css` | **Chat UI styles.** Dark theme with CSS variables. Responsive layout with sidebar + main area. Styled message bubbles (user = blue, assistant = dark gray), code blocks, input area, sidebar sessions, scrollbars. ~530 lines. |
| `js/chat.js` | **Chat UI logic.** Full client-side JavaScript for: `sendMessage()` (POST to /api/chat), `loadSessions()` / `renderSidebar()`, `addMessage()` with markdown rendering via marked.js, `copyMessage()`, `regenerateResponse()`, `submitFeedback()` (thumbs up/down), `exportChat()` (JSON/text download), `searchChats()`. ~480 lines. |

---

### data/ -- Training Data (8 files)

| File | Topic | Description |
|------|-------|-------------|
| `AI_B2C_RAG_Optimized.txt` | Product FAQ | Comprehensive Q&A about LAMF/LAS products, processes, eligibility |
| `Lark_Finserv_Company_Information.txt` | Company Info | About Lark Finserv, mission, vision, team |
| `Master_Training_Document_Query_Classification.txt` | Product Overview | Detailed product documentation with classifications |
| `Lender_Partner_Documentation.txt` | Lender Partners | Documentation about BFL, DSP, ABFL, Tata Capital partnerships |
| `Cleaned_Promotion_Material.txt` | Marketing | Cleaned promotional content for MFD partners |
| `Promotion Material.txt` | Marketing | Raw promotional content, WhatsApp templates, pitch ideas |
| `ABFL Tata Offline LAS.txt` | Phygital Process | Offline/phygital loan process for ABFL and Tata Capital |
| `Complete_Training_Dataset_Labeled.csv` | Labeled Dataset | 503 labeled examples with TEXT, CATEGORY, SUB_CATEGORY, LABEL columns |

---

### Generated Directories

| Directory | Purpose |
|-----------|---------|
| `vectorstore/` | Contains the FAISS index files (`index.faiss`, `index.pkl`) built by the ingestion script. This is the vector database used for RAG retrieval. |
| `instance/` | Flask instance folder. Contains `lisa.db` (SQLite database with users, sessions, messages, feedback tables). |
| `venv/` | Python virtual environment with all installed packages. |

---

## API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | No | Redirects to `/chat` (if logged in) or `/login` |
| GET | `/chat` | Yes | Main chat UI page |
| GET/POST | `/login` | No | Login page and form handler |
| GET | `/logout` | Yes | Logout and redirect |
| GET | `/api/auth/status` | No | Check auth status (JSON) |
| POST | `/api/chat` | Yes | Send message, get AI response |
| POST | `/api/chat/regenerate` | Yes | Re-generate last response |
| GET | `/api/sessions` | Yes | List all sessions |
| POST | `/api/sessions` | Yes | Create new session |
| GET | `/api/sessions/<id>/messages` | Yes | Get session messages |
| DELETE | `/api/sessions/<id>` | Yes | Delete session |
| GET | `/api/sessions/search?q=` | Yes | Search chat history |
| GET | `/api/sessions/<id>/export` | Yes | Export chat (JSON/text) |
| POST | `/api/feedback` | Yes | Submit feedback on message |
| GET | `/api/health` | No | Health check |

---

## Test Accounts

| Username | Password | Role | Partner Type |
|----------|----------|------|--------------|
| admin | admin123 | Admin | admin |
| demo_mfd | demo123 | Demo | MFD |
| demo_wealth | demo123 | Demo | wealth_platform |

---

## Environment Variables (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | (empty) | OpenAI API key for LLM and embeddings |
| `EMBEDDING_MODEL` | text-embedding-3-large | OpenAI embedding model name |
| `LLM_MODEL` | gpt-4o-mini | OpenAI LLM model name |
| `GEMINI_API_KEY` | (empty) | Google Gemini API key (fallback) |
| `GEMINI_MODEL` | gemini-4.5-flash | Gemini model name |
| `LANGSMITH_API_KEY` | (empty) | LangSmith API key for tracing |
| `LANGCHAIN_TRACING_V2` | false | Enable/disable LangSmith tracing |
| `DATABASE_URL` | sqlite:///lisa.db | Database connection string |
| `AUTH_SECRET_KEY` | (change me) | Flask session secret key |
| `VECTOR_DB_PATH` | vectorstore | Path to FAISS index directory |
| `CHUNK_SIZE` | 500 | Document chunk size for ingestion |
| `CHUNK_OVERLAP` | 100 | Overlap between chunks |
| `TOP_K` | 5 | Number of documents to retrieve |
| `RERANK_ENABLED` | true | Enable cross-encoder re-ranking |
| `PORT` | 5001 | Flask server port |
