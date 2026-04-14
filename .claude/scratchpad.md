# Second Brain — Session History & Scratchpad

> This file tracks what was done in each session so future sessions can pick up where we left off.

---

## Session 1: 2026-04-01 — Research & Planning

### What was done
1. Read PLAN.md (930 lines), AGENTS.md (200 lines), PORT-MAP.md (275 lines)
2. Created CLAUDE.md (project context file)
3. Created .claude/memory.md and .claude/scratchpad.md
4. Launched 4 parallel research agents:
   - **RAG Pipeline** — pgvector HNSW vs IVFFLAT, embedding models, chunking, hybrid search, prompt engineering
   - **Content Ingestion** — pdfplumber vs PyMuPDF, trafilatura vs newspaper3k, markdown storage
   - **Telegram Bot** — python-telegram-bot v22.x, UX patterns, webhook vs polling
   - **Frontend Libraries** — search UX, markdown editors, PDF viewers, shadcn components
5. Created README.md for GitHub
6. Consolidated all research findings into memory

### Research Findings Summary
- **HNSW over IVFFLAT** — better recall, dynamic inserts, no reindex
- **pdfplumber** (MIT) over PyMuPDF (AGPL) — license safety
- **trafilatura** (F1=0.958) — best article extraction
- **python-telegram-bot v22.7** — update from 20.5+ in PLAN.md
- **@uiw/react-md-editor** (4.6KB) — lightweight markdown editor
- **Skip PDF viewer for MVP** — extracted text + download link
- **tiktoken** for exact token counting — replace len/4 estimate
- **HTML parse mode** for Telegram — avoid MarkdownV2 escaping hell

---

## Session 2: 2026-04-02 — Full Implementation

### What was done
1. **Git init** + .gitignore + .env.example
2. **Backend scaffold** — pyproject.toml (uv), app package structure, config.py, database.py, main.py
3. **Database** — migrations/schema.sql with HNSW index + GENERATED tsvector, SQLAlchemy models for all 8 tables
4. **Pydantic schemas** — request/response schemas for all 6 endpoint groups
5. **Core services:**
   - `chunking_service.py` — sentence-boundary splitting with token accumulation + overlap
   - `embedding_service.py` — OpenAI batch embedding + chunk creation pipeline
   - `llm_service.py` — Claude Haiku/Sonnet with RAG system prompt
   - `rag_service.py` — hybrid search (pgvector + tsvector) with RRF, full RAG pipeline
6. **Content services:**
   - `pdf_service.py` — pdfplumber extraction via asyncio.to_thread
   - `scraping_service.py` — trafilatura with markdown output
7. **API routes** — 6 routers: notes, bookmarks, pdfs, search, tags, settings
8. **Telegram bot** — bot.py (dual mode), handlers.py (7 commands + auto-URL + callbacks), utils.py
9. **Frontend** (via background agent) — Next.js 14, 10 pages, 9 components, API client, Zustand store
10. **Docker** — docker-compose.yml, 3 Dockerfiles (backend, telegram, frontend multi-stage), Makefile
11. **Backend tests** — 44 tests across 6 test files (chunking, tokenizer, notes, bookmarks, tags, search)
12. **Frontend tests** — 17 tests across 3 files (API client, utils, store)
13. **Verification:**
    - `uv run pytest` — 44/44 pass
    - `npx vitest run` — 17/17 pass
    - `npm run build` — builds clean (11 pages)
    - `docker compose build` — all 3 images built
    - `docker compose up` — all services start
    - Health check: `{"status":"healthy"}`
    - API endpoints: notes, tags, settings all respond correctly
    - Frontend: serves full HTML with sidebar, search, navigation

### Issues Encountered & Resolved
1. **SQLite can't handle JSONB/TSVECTOR/Vector** — Fixed with `@compiles` decorators in conftest.py
2. **Mock not applying to bookmark route** — Fixed by patching at import location (`app.api.bookmarks.scrape_url`)
3. **onupdate=func.now() greenlet error** — Fixed by setting `updated_at` explicitly in handler
4. **next-themes import path changed** — Fixed: import from `"next-themes"` not `"next-themes/dist/types"`
5. **react-highlight-words missing types** — Fixed with types.d.ts declaration
6. **vitest/vite type conflict in next build** — Fixed by excluding vitest.config.ts from tsconfig
7. **Port 5432 already in use** — Made postgres port configurable via `DB_PORT` env var

---

## Next Steps (for future sessions)

### Immediate (polish & deploy)
- [ ] Add real API keys to .env and test full RAG pipeline end-to-end
- [ ] Create a note via API, verify chunking + embedding works
- [ ] Search via API, verify hybrid search + Claude answer works
- [ ] Test Telegram bot locally (polling mode)
- [ ] Deploy to VPS via Docker Compose
- [ ] Set up Traefik on VPS for SSL
- [ ] Configure Telegram webhook on VPS

### Short-term improvements
- [ ] Add pagination to frontend notes/bookmarks lists (currently shows all)
- [ ] Add tag filter UI to notes/bookmarks pages
- [ ] Add "Mark as Read" toggle to bookmark cards
- [ ] Add loading states to all pages (currently shows skeleton placeholders via SWR)
- [ ] Add error toasts when API calls fail
- [ ] Add auto-save to note editor
- [ ] Add Cmd+K command dialog (shadcn Command component)

### Medium-term
- [ ] Add PDF upload drag-and-drop UI improvements
- [ ] Add tag management to note/bookmark detail views
- [ ] Add search result highlighting in source cards
- [ ] Add export functionality (markdown, JSON)
- [ ] Add dark mode refinements
- [ ] Add mobile responsive testing
- [ ] Set up GitHub Actions CI (lint → test → build)

### Known limitations
- No authentication (single-user, no JWT) — fine for personal use behind Traefik
- No rate limiting on API endpoints yet
- No Redis caching yet (allocated DB #9)
- No Alembic migrations yet (using raw SQL init script)
- Frontend API types don't perfectly match backend Pydantic schemas (some field names differ)
- Bookmark scraping is synchronous in the request cycle (should be background task for slow URLs)
