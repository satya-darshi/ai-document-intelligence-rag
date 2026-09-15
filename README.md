# AI-Powered Document Intelligence & RAG Platform

A production-style document question-answering system built around **Retrieval-Augmented Generation (RAG)**. The application runs its databases and services locally in Docker, while the AI inference layer uses Google's **Gemini API**.

## AI architecture: cloud inference, local infrastructure

The AI inference layer uses Google's Gemini API for generation and embeddings, while application infrastructure runs locally in Docker.

The code uses:

- **Gemini 2.5 Flash** — cloud LLM for grounded answers and agent/tool calling.
- **Gemini Embedding 2** — cloud embeddings for semantic retrieval, configured to 768 dimensions.
- **Qdrant** — local vector database in Docker.
- **PostgreSQL** — local application and conversation persistence.
- **Redis** — local response caching.
- **LangChain + LangGraph** — RAG and agent orchestration.
- **FastAPI** — backend API.
- **React + Vite** — frontend.
- **Docker Compose** — local infrastructure.

Gemini 2.5 Flash supports function calling and is a stable model. Gemini Embedding 2 supports 128–3072 dimensions, with 768 recommended as one of the standard reduced sizes.

### What runs on your PC vs. the cloud

```text
                         Your PC
┌────────────────────────────────────────────────────────────┐
│                                                            │
│  React UI ──> FastAPI                                     │
│                 │                                          │
│       ┌─────────┼──────────┐                               │
│       │         │          │                               │
│   PostgreSQL  Redis      Qdrant                            │
│       │         │          │                               │
│       └─────────┼──────────┘                               │
│                 │                                          │
│          RAG / Agent layer                                │
└─────────────────┼──────────────────────────────────────────┘
                  │ HTTPS API
                  ▼
        ┌───────────────────────┐
        │ Google Gemini API     │
        │                       │
        │ Gemini 2.5 Flash      │
        │ Gemini Embedding 2    │
        └───────────────────────┘
```

## Features

### RAG mode
1. Upload PDF/TXT/Markdown documents.
2. Extract page-aware text.
3. Split text into overlapping chunks.
4. Generate Gemini embeddings for each chunk.
5. Store vectors and metadata in Qdrant.
6. Retrieve semantic candidates for a question.
7. Rerank candidates using a combination of vector similarity and lexical overlap.
8. Give only the retrieved context to Gemini.
9. Return a grounded answer with source citations.

### Agent mode
The agent is built with LangChain's agent API and Gemini function calling. It has three tools:

- `search_documents` — semantic search over selected documents.
- `inspect_source` — inspect the exact text of a retrieved chunk.
- `compare_documents` — retrieve evidence across selected documents for comparison.

The agent is instructed to search before making factual claims and to explicitly report insufficient evidence.

### Engineering features

- PostgreSQL persistence for documents, conversations, and messages.
- Redis caching for repeated RAG questions.
- Qdrant metadata filtering by selected document IDs.
- Two-stage retrieval: semantic candidate retrieval followed by lightweight reranking.
- Page-aware citations for PDFs.
- Background document ingestion using FastAPI background tasks.
- Dockerized PostgreSQL, Redis, Qdrant, backend, and frontend.
- Evaluation harness for retrieval experiments.
- Automated smoke tests.
- AI inference is handled through the Gemini API rather than a locally hosted LLM.

## Prerequisites

- Docker Desktop with Docker Compose.
- A Google account for Google AI Studio.
- A Gemini API key.

## 1. Get a Gemini API key

Create a key in Google AI Studio. The application reads the key from your local `.env` file.

Do **not** put the key directly in source code and do **not** commit `.env` to Git.

## 2. Configure environment

From the project root:

```bash
cp .env.example .env
```

On Windows PowerShell, you can use:

```powershell
Copy-Item .env.example .env
```

Open `.env` and replace:

```text
GEMINI_API_KEY=your_gemini_api_key_here
```

Keep the other defaults unless you have a reason to change them.

## 3. Start the application

```bash
docker compose up --build
```

Open:

- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Qdrant dashboard: http://localhost:6333/dashboard

Stop it with:

```bash
docker compose down
```

The database/vector/cache data remains in Docker volumes. To remove those volumes too:

```bash
docker compose down -v
```

## 4. First test

1. Open the frontend.
2. Upload a PDF, TXT, or Markdown file.
3. Wait until its status becomes `ready`.
4. Select the document.
5. Ask a question whose answer is contained in the document.
6. Try the **Agentic** mode for a multi-step question or comparison.

## API flow

### Upload

```http
POST /api/v1/documents
```

The API saves the file, creates a PostgreSQL record, and schedules ingestion in a FastAPI background task.

### Chat

```http
POST /api/v1/chat
```

Example:

```json
{
  "message": "What is virtual memory?",
  "document_ids": ["DOCUMENT_UUID"],
  "mode": "rag"
}
```

Agentic mode:

```json
{
  "message": "Compare the scheduling approaches in these documents.",
  "document_ids": ["DOC_UUID_1", "DOC_UUID_2"],
  "mode": "agent"
}
```

## Retrieval pipeline

```text
Document upload
      │
      ▼
PDF/TXT/MD extraction
      │
      ▼
Recursive chunking
      │
      ▼
Gemini Embedding 2
      │
      ▼
Qdrant + metadata
      │
      │  user question
      ▼
Gemini query embedding
      │
      ▼
Top semantic candidates
      │
      ▼
Vector + lexical reranking
      │
      ▼
Top context chunks
      │
      ▼
Gemini 2.5 Flash
      │
      ▼
Grounded answer + citations
```

## Development without Docker for the backend

You can run FastAPI directly if PostgreSQL, Redis, and Qdrant are already available locally:

```bash
cd backend
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Then:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

For this mode, change the infrastructure URLs in `.env` to `localhost`:

```text
DATABASE_URL=postgresql+psycopg://raguser:ragpassword@localhost:5432/ragdb
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333
```

## Project structure

```text
ai-document-intelligence-rag/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI routes
│   │   ├── core/            # settings/configuration
│   │   ├── db/              # SQLAlchemy setup
│   │   ├── models/          # PostgreSQL entities
│   │   ├── schemas/         # request/response models
│   │   └── services/
│   │       ├── agent.py         # LangChain agent + tools
│   │       ├── embeddings.py     # Gemini Embedding 2 adapter
│   │       ├── ingestion.py      # parsing/chunking/indexing
│   │       ├── retrieval.py      # vector retrieval + reranking
│   │       ├── llm.py            # Gemini 2.5 Flash
│   │       └── chat.py           # chat orchestration/cache
│   └── tests/
├── frontend/
├── data/uploads/
├── docs/
├── docker-compose.yml
├── .env.example
└── README.md
```

## Evaluation

The repository contains a small retrieval evaluation harness. Run it after uploading and indexing documents:

```bash
docker compose exec api python -m app.services.evaluation
```

## Tests and linting

Inside `backend/`:

```bash
pytest -q
ruff check .
```

## Official references

- Google Gemini models: https://ai.google.dev/gemini-api/docs/models
- Gemini 2.5 Flash: https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash
- Gemini embeddings: https://ai.google.dev/gemini-api/docs/embeddings
- Qdrant local quickstart: https://qdrant.tech/documentation/quickstart/
- LangChain Google GenAI integration: https://python.langchain.com/docs/integrations/chat/google_generative_ai/
