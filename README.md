# LISA AI - Lark Intelligent Support Assistant

A production-ready AI chatbot for Lark Finserv that helps MFD (Mutual Fund Distributor) partners with information about LAMF and LAS products.

## 🏗️ Project Structure

The codebase is organized into **4 clear modules** for easy review and collaboration:

```
LISA-RAG/
├── frontend/        ← UI (templates, CSS, JavaScript)
├── backend/         ← Flask API, authentication, core logic
├── rag/            ← Document processing, vector search, RAG pipeline
├── config/         ← Configuration management
└── data/           ← Training data
```

→ See **`FOLDER_STRUCTURE.md`** for detailed module breakdown and review guide.

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up Environment
```bash
# Create .env file and add your API keys
export OPENAI_API_KEY="sk-..."      # or GEMINI_API_KEY
export LANGSMITH_API_KEY="..."      # optional
```

### 3. Initialize Database
```bash
python rag/scripts/create_db.py
```

### 4. Create Test Users
```bash
python rag/scripts/seed_users.py
# Creates: admin/admin123, demo_mfd/demo123, demo_wealth/demo123
```

### 5. Build Vector Index (one-time)
```bash
python rag/scripts/ingest_documents.py
```

### 6. Run the Server
```bash
python app.py
# Open http://localhost:5001
```

---

## 🔄 Architecture

**Data Flow:**
1. **Frontend** → Sends query via `/api/chat`
2. **API Routes** → Receives request, validates auth
3. **LangGraph Workflow** → Orchestrates multi-step processing:
   - Intent classifier (understands user intent)
   - RAG retrieval (searches FAISS for relevant docs)
   - LLM response (generates answer with context)
   - Tool execution (optionally calls marketing, FAQ, analytics tools)
   - Memory update (saves to database)
   - Trace logger (logs to LangSmith if enabled)
4. **Frontend** → Displays response with markdown rendering

---

## 📁 Key Modules at a Glance

| Module | Purpose | Key Files |
|--------|---------|-----------|
| **frontend/** | UI templates & client JS | `templates/chat.html`, `static/js/chat.js` |
| **backend/api/** | REST endpoints | `routes.py` (14 endpoints) |
| **backend/graph/** | LangGraph workflow | `nodes.py`, `builder.py` (6 processing nodes) |
| **rag/** | Document ingestion & search | `ingest.py`, `retriever.py`, `reranker.py` |
| **backend/memory/** | Database models | `store.py` (4 SQLAlchemy models) |

---

## 🔐 Test Accounts

| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | Admin |
| demo_mfd | demo123 | MFD Partner |
| demo_wealth | demo123 | Wealth Platform |

---

## 🛠️ Tech Stack

- **Backend:** Flask + LangChain + LangGraph
- **LLM:** OpenAI GPT-4o-mini (with Gemini fallback)
- **Vector DB:** FAISS
- **Database:** SQLite + SQLAlchemy
- **Frontend:** Vanilla JS + Markdown rendering (marked.js)
- **Auth:** Flask-Login with password hashing

---

## 📚 Documentation

- **`FOLDER_STRUCTURE.md`** - Detailed module breakdown, review checklist, import guide
- **`PROJECT_DOCUMENTATION.md`** - Comprehensive system design, API reference, setup instructions

---

## 💡 For Senior Developers

This project is structured for **easy code review**:

✅ **Clear separation of concerns:**
- Frontend code is isolated in `frontend/`
- API logic in `backend/api/`
- Core workflow in `backend/graph/`
- Data processing in `rag/`
- Config in one place

✅ **Review Guide:**
See **`FOLDER_STRUCTURE.md`** → "Code Review Checklist" section for what to review in each module.

✅ **Key Review Files:**
- Workflow orchestration: `backend/chatbot/graph/builder.py`, `nodes.py`
- API endpoints: `backend/chatbot/api/routes.py`
- RAG pipeline: `rag/ingest.py`, `retriever.py`
- Frontend logic: `frontend/static/js/chat.js`

---

## 🔧 Commands Reference

```bash
# Start server
python app.py

# Initialize database
python rag/scripts/create_db.py

# Create test users
python rag/scripts/seed_users.py

# Build FAISS index
python rag/scripts/ingest_documents.py

# Run linting (if set up)
# flake8 backend/ rag/ config/
```

---

## 📝 Environment Variables

Essential variables in `.env`:

```env
OPENAI_API_KEY=sk-...              # LLM provider
EMBEDDING_MODEL=text-embedding-3-large
LLM_MODEL=gpt-4o-mini

DATABASE_URL=sqlite:///lisa.db
PORT=5001
DEBUG=True

VECTOR_DB_PATH=vectorstore
CHUNK_SIZE=500
TOP_K=5
```

See `config/config.py` for all available options.

---

## 🎯 Next Steps

1. ✅ Review the **folder structure** in `FOLDER_STRUCTURE.md`
2. ✅ Start the server with `python app.py`
3. ✅ Login with test account (demo_mfd / demo123)
4. ✅ Test a query to see the workflow in action
5. ✅ Review code in order: **frontend** → **backend/api** → **backend/graph** → **rag**

---

**Happy coding!** 🚀
