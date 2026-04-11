# CLAUDE.md — Second Brain / Personal Knowledge Base

> **Port allocation:** See [PORTS.md](PORTS.md) before changing any docker-compose ports. All ports outside the assigned ranges are taken by other projects.

## Project Overview

Personal knowledge management system with RAG-powered AI search. Captures notes, PDFs, and bookmarks via web UI and Telegram bot. Single-user (Armando), deployed at brain.armandointeligencia.com.

## Tech Stack

- **Backend:** FastAPI + SQLAlchemy 2.0 (async) + asyncpg + Pydantic 2.0
- **Frontend:** Next.js 14+ (App Router) + TypeScript + TailwindCSS + Shadcn/UI + SWR + Zustand
- **Database:** PostgreSQL 16 with pgvector (1536-dim embeddings) + full-text search (tsvector/GIN)
- **AI:** OpenAI text-embedding-3-small (embeddings) + Anthropic Claude Haiku/Sonnet (LLM)
- **Bot:** python-telegram-bot 22.x (async, Bot API 9.5)
- **Infra:** Docker Compose + Traefik 2.10+ (SSL) on Hostinger VPS (2 vCPU, 8GB RAM)

## Port Allocation (Project 11)

| Service | Host Port | Container Port |
|---------|-----------|---------------|
| Frontend (Next.js) | 3110 | 3000 |
| Backend (FastAPI) | 8110 | 8000 |
| Telegram Bot | 8111 | 8001 |

PostgreSQL: shared instance on port 5432, database `second_brain_db`
Redis: shared instance on port 6379, DB #9

## Project Structure

```
11-Second-Brain/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Settings (env vars)
│   │   ├── models.py            # SQLAlchemy ORM models
│   │   ├── schemas.py           # Pydantic schemas
│   │   ├── database.py          # Async DB connection
│   │   ├── api/                 # Route handlers
│   │   │   ├── notes.py
│   │   │   ├── bookmarks.py
│   │   │   ├── pdfs.py
│   │   │   ├── search.py
│   │   │   ├── tags.py
│   │   │   └── settings.py
│   │   ├── services/            # Business logic
│   │   │   ├── embedding_service.py
│   │   │   ├── chunking_service.py
│   │   │   ├── pdf_service.py
│   │   │   ├── scraping_service.py
│   │   │   ├── rag_service.py
│   │   │   └── llm_service.py
│   │   └── utils/
│   │       ├── tokenizer.py
│   │       └── logger.py
│   ├── telegram_bot/
│   │   ├── bot.py
│   │   ├── handlers.py
│   │   └── utils.py
│   ├── tests/
│   ├── pyproject.toml           # uv project config
│   └── Dockerfile
├── frontend/
│   ├── app/                     # Next.js App Router pages
│   ├── components/              # Shared React components
│   ├── lib/                     # API clients, stores, utils
│   ├── package.json
│   ├── tailwind.config.ts
│   └── Dockerfile
├── docker-compose.yml
├── Makefile
├── .env.example
├── PLAN.md
├── AGENTS.md
├── PORT-MAP.md
└── README.md
```

## Development Commands

```bash
# Python backend (use uv)
cd backend && uv run uvicorn app.main:app --reload --port 8110

# Frontend
cd frontend && npm run dev -- -p 3110

# Tests
cd backend && uv run pytest
cd frontend && npx vitest

# Docker
docker compose up -d
docker compose logs -f backend
```

## Key Architecture Decisions

1. **No separate vector DB** — pgvector extension on PostgreSQL 16. Simplifies infra, good enough for <100K embeddings.
2. **HNSW index** — Over IVFFLAT for better recall, dynamic insert support, and no periodic REINDEX. Parameters: m=16, ef_construction=64.
3. **Hybrid search** — pgvector semantic + PostgreSQL tsvector full-text via Reciprocal Rank Fusion (k=60). Over-fetch 20 from each, select top 10 after fusion.
4. **Chunking** — 400-500 token chunks with 50-token overlap using RecursiveCharacterTextSplitter. Token counting via tiktoken (cl100k_base). Notes <500 tokens as single chunk.
5. **LLM strategy** — Haiku for most queries (cheap/fast), Sonnet toggle for complex reasoning.
6. **Single user** — user_id=1 hardcoded. Schema supports multi-user for future migration.
7. **Tag-based organization** — No folders/hierarchy. Tags are flexible and flat.
8. **PDF extraction** — pdfplumber (MIT license). OCR fallback via pytesseract for scanned PDFs.
9. **URL scraping** — trafilatura with Markdown output. Fallback: readability-lxml.
10. **Telegram** — HTML parse mode, webhook via telegram.brain.armandointeligencia.com, dual mode (polling dev / webhook prod).

## API Base URL

- Local: `http://localhost:8110/api/v1`
- Production: `https://api.brain.armandointeligencia.com/api/v1`

## Database

- Schema in `backend/migrations/schema.sql`
- Tables: users, notes, bookmarks, pdfs, chunks, embeddings, tags, tag_assignments
- pgvector HNSW index on embeddings for cosine similarity (m=16, ef_construction=64)
- GIN indexes for full-text search on notes, bookmarks, chunks
- GENERATED ALWAYS tsvector column on chunks table for auto-sync with content

## Agent Roles (from AGENTS.md)

When working on this project, apply the relevant specialist roles:
- **Software Architect** — API design, module boundaries, patterns
- **UI/UX Designer** — Components, responsive layouts, accessibility
- **Test Engineer** — pytest (backend), vitest (frontend), test-first
- **DevOps Engineer** — Docker, Traefik, CI/CD, Makefile
- **Security Engineer** — Input validation, CORS, file uploads, rate limiting
- **Database Administrator** — Schema, indexes, query optimization
- **Code Reviewer** — Style, naming, error handling, types

## Environment Variables

See `.env.example` for all required variables. Key ones:
- `DATABASE_URL` — PostgreSQL connection string
- `OPENAI_API_KEY` — For embeddings
- `ANTHROPIC_API_KEY` — For Claude LLM
- `TELEGRAM_BOT_TOKEN` — From @BotFather
- `TELEGRAM_USER_ID` — Armando's Telegram user ID

## Coding Standards

### Python (Backend)
- Python 3.12+, async/await throughout
- Type hints on all function signatures
- Pydantic models for all request/response schemas
- SQLAlchemy 2.0 style (mapped_column, DeclarativeBase)
- Logging: structlog or standard logging with JSON format
- Linting: ruff (replaces black + isort + flake8)

### TypeScript (Frontend)
- TypeScript strict mode
- React Server Components where possible
- Client components only when interactivity needed
- TailwindCSS for styling (no CSS modules)
- Zod for form validation

## Memory & Notes (READ THESE FIRST in new sessions)

All project context is stored locally in `.claude/` (committed to git, portable):

- **`.claude/memory.md`** — Architectural decisions, gotchas, performance expectations, cost estimates, user preferences. **Read this first.**
- **`.claude/scratchpad.md`** — Session history: what was done, issues resolved, next steps. **Read this to know where we left off.**
- **`.claude/file-map.md`** — Complete file inventory with purpose and status for every file in the project.
- **`.claude/research-findings.md`** — Full research findings from 4 parallel agents (RAG pipeline, content ingestion, Telegram bot, frontend libraries).

## Current Status (as of 2026-04-02)

**MVP COMPLETE** — all code written, tested, Docker verified:
- Backend: 44/44 pytest tests pass
- Frontend: 17/17 vitest tests pass, builds clean
- Docker: all 3 images build, all services start
- Next: add API keys, test full RAG end-to-end, deploy to VPS
