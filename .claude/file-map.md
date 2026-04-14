# Second Brain — File Map

> Complete inventory of every file in the project, what it does, and its current state.
> Use this to quickly find where things are without re-reading every file.

---

## Root Files

| File | Purpose | Status |
|------|---------|--------|
| `PLAN.md` | Original project plan (930 lines) — DB schema, API endpoints, RAG pipeline, Telegram commands, frontend pages | Reference (some details superseded by research) |
| `AGENTS.md` | 7 specialist agent roles with quality checklists | Reference |
| `PORT-MAP.md` | Global port allocation across all projects | Reference |
| `CLAUDE.md` | Main project context file for Claude Code | Active |
| `README.md` | GitHub README with architecture diagram, setup instructions | Active |
| `.env.example` | Template for environment variables | Active |
| `.gitignore` | Python/Node/Docker/IDE ignores | Active |
| `docker-compose.yml` | 4 services: postgres, backend, frontend, telegram-bot + Traefik labels | Active |
| `Makefile` | dev, build, test, deploy, db-reset, setup targets | Active |

## Backend — `/backend/`

### Config & Entry

| File | Purpose |
|------|---------|
| `pyproject.toml` | Python deps (uv), test config, ruff config |
| `app/__init__.py` | Empty |
| `app/main.py` | FastAPI app, CORS, router includes, health check, lifespan |
| `app/config.py` | Pydantic Settings — all env vars with defaults |
| `app/database.py` | Async engine + session factory + `get_db` dependency |
| `app/models.py` | SQLAlchemy ORM models: User, Note, Bookmark, Pdf, Chunk, Embedding, Tag, TagAssignment |
| `app/schemas.py` | Pydantic request/response schemas for all endpoints |

### API Routes — `/backend/app/api/`

| File | Endpoints | Key Logic |
|------|-----------|-----------|
| `notes.py` | CRUD `/notes`, tags assignment | Creates chunks+embeddings on create/update |
| `bookmarks.py` | CRUD `/bookmarks` | Scrapes URL on create, creates chunks+embeddings |
| `pdfs.py` | Upload `/pdfs/upload`, list, get, delete | Extracts text on upload, creates chunks+embeddings |
| `search.py` | `POST /search` (RAG), `POST /search/raw` | Calls rag_service for hybrid search + LLM |
| `tags.py` | CRUD `/tags` with item counts | Tag names normalized to lowercase |
| `settings.py` | GET/PUT `/settings` | LLM preference (haiku/sonnet) |

### Services — `/backend/app/services/`

| File | Purpose | External Deps |
|------|---------|---------------|
| `chunking_service.py` | Sentence-boundary text splitting with overlap | tiktoken |
| `embedding_service.py` | OpenAI batch embedding + chunk DB creation | openai SDK |
| `llm_service.py` | Claude Haiku/Sonnet RAG answer generation | anthropic SDK |
| `rag_service.py` | Hybrid search (pgvector + tsvector + RRF) + full RAG pipeline | pgvector, PostgreSQL |
| `pdf_service.py` | PDF text extraction via pdfplumber | pdfplumber |
| `scraping_service.py` | URL article extraction via trafilatura | trafilatura |

### Utils — `/backend/app/utils/`

| File | Purpose |
|------|---------|
| `tokenizer.py` | `count_tokens()` and `truncate_to_tokens()` using tiktoken cl100k_base |
| `logger.py` | Standard logging setup with configurable level |

### Telegram Bot — `/backend/telegram_bot/`

| File | Purpose |
|------|---------|
| `bot.py` | Main entry point — builds Application, registers handlers, runs polling/webhook |
| `handlers.py` | All command handlers (/add, /search, /bookmark, /list, /tags, /settings, /help), callback handler, auto-URL handler |
| `utils.py` | `@restricted` decorator, `truncate()`, `format_source_preview()` |

### Tests — `/backend/tests/`

| File | Tests | Count |
|------|-------|-------|
| `conftest.py` | SQLite type adapters, fixtures (db_engine, db_session, client, mocks) | — |
| `test_chunking.py` | split_into_sentences, chunk_text (short, long, overlap, min size) | 11 |
| `test_tokenizer.py` | count_tokens, truncate_to_tokens | 5 |
| `test_api_notes.py` | CRUD (create, list, pagination, get, update, delete soft/hard), health | 10 |
| `test_api_bookmarks.py` | CRUD (create, duplicate, invalid URL, list, mark read, delete) | 6 |
| `test_api_tags.py` | CRUD (create, duplicate, normalized, list, delete, not found, invalid color) | 7 |
| `test_search.py` | Empty query, valid query, model selection, raw search, query too long | 5 |
| **Total** | | **44** |

### Other Backend Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Backend API image (python:3.12-slim + uv) |
| `Dockerfile.telegram` | Telegram bot image (same base, different CMD) |
| `migrations/schema.sql` | Full DB schema with HNSW index, GENERATED tsvector, all indexes |
| `uploads/.gitkeep` | Placeholder for PDF uploads directory |

## Frontend — `/frontend/`

### Config Files

| File | Purpose |
|------|---------|
| `package.json` | Deps: next, react, tailwindcss, swr, zustand, use-debounce, lucide-react, sonner, etc. |
| `tsconfig.json` | Strict mode, `@/*` path alias, excludes vitest config |
| `next.config.js` | `output: "standalone"` for Docker |
| `tailwind.config.ts` | darkMode: "class", shadcn CSS variable color system |
| `postcss.config.js` | tailwindcss + autoprefixer |
| `vitest.config.ts` | jsdom environment, React plugin, path alias |
| `next-env.d.ts` | Next.js TypeScript reference |
| `types.d.ts` | Module declaration for react-highlight-words |
| `Dockerfile` | Multi-stage: deps → build → runner (node:20-alpine) |

### Library Files — `/frontend/lib/`

| File | Purpose |
|------|---------|
| `api.ts` | Fetch wrapper + typed API functions for all endpoints (base URL: `/api/v1`) |
| `store.ts` | Zustand store: searchQuery, sidebarOpen |
| `utils.ts` | `cn()` (clsx + tailwind-merge) |

### Components — `/frontend/components/`

| File | Purpose |
|------|---------|
| `SearchBar.tsx` | Debounced search input (300ms), Cmd+K hint, navigates to /search |
| `Sidebar.tsx` | Navigation links, active highlighting, mobile collapse, dark mode toggle |
| `Header.tsx` | Mobile hamburger, page title, desktop search bar |
| `ThemeProvider.tsx` | next-themes wrapper |
| `ui/button.tsx` | CVA button with 6 variants, 4 sizes |
| `ui/input.tsx` | forwardRef input |
| `ui/badge.tsx` | Tag pill with custom color support |
| `ui/card.tsx` | Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter |
| `ui/skeleton.tsx` | Animate-pulse loading placeholder |

### Pages — `/frontend/app/`

| Page | Route | Key Features |
|------|-------|--------------|
| `layout.tsx` | Root | ThemeProvider, Toaster (sonner), Sidebar + main layout |
| `page.tsx` | `/` | Dashboard: welcome, search bar, quick actions, recent items grid |
| `search/page.tsx` | `/search` | RAG answer card, source cards with highlights, Haiku/Sonnet toggle |
| `notes/page.tsx` | `/notes` | Notes list with pagination, tag filter, "New Note" button |
| `notes/new/page.tsx` | `/notes/new` | Markdown editor, tag input, save/cancel |
| `notes/[id]/page.tsx` | `/notes/:id` | Edit note, markdown editor, tag management, save/delete |
| `bookmarks/page.tsx` | `/bookmarks` | Bookmark list, add URL form, read/unread toggle |
| `pdfs/page.tsx` | `/pdfs` | Upload area, PDF list with expandable text preview |
| `tags/page.tsx` | `/tags` | Create form with color picker, tags table with counts |
| `settings/page.tsx` | `/settings` | LLM model toggle, theme toggle |

### Tests — `/frontend/__tests__/`

| File | Tests | Count |
|------|-------|-------|
| `api.test.ts` | GET/POST/DELETE, 204 handling, error handling, notes/tags/search | 9 |
| `utils.test.ts` | cn() merging, conditional classes, tailwind merge | 5 |
| `store.test.ts` | searchQuery, toggleSidebar | 3 |
| **Total** | | **17** |

### Styles

| File | Purpose |
|------|---------|
| `app/globals.css` | TailwindCSS base + shadcn CSS variables (light/dark themes) |
