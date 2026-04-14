# Project Structure

## Directory Tree

```
11-Second-Brain/
├── .claude/                         # Session context (read FIRST)
│   ├── memory.md                    # Architectural decisions, gotchas, performance
│   ├── scratchpad.md                # Session history & next steps
│   ├── file-map.md                  # File inventory with purposes
│   └── research-findings.md         # Research from 4 parallel agents
│
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point, CORS, lifespan
│   │   ├── config.py                # Pydantic Settings from env vars
│   │   ├── database.py              # Async engine, session factory, get_db dependency
│   │   ├── models.py                # SQLAlchemy ORM: 8 tables (users, notes, bookmarks, pdfs, chunks, embeddings, tags, tag_assignments)
│   │   ├── schemas.py               # Pydantic request/response schemas
│   │   ├── api/                     # 6 route modules
│   │   │   ├── notes.py             # CRUD + tag assignment
│   │   │   ├── bookmarks.py         # CRUD + URL scraping
│   │   │   ├── pdfs.py              # Upload + text extraction
│   │   │   ├── search.py            # Hybrid search + RAG answer
│   │   │   ├── tags.py              # CRUD with item counts
│   │   │   └── settings.py          # LLM preference
│   │   ├── services/                # 6 business logic modules
│   │   │   ├── chunking_service.py  # Sentence splitting + token accumulation
│   │   │   ├── embedding_service.py # OpenAI batch embedding
│   │   │   ├── llm_service.py       # Claude Haiku/Sonnet RAG
│   │   │   ├── rag_service.py       # Hybrid search (pgvector + tsvector + RRF)
│   │   │   ├── pdf_service.py       # pdfplumber extraction
│   │   │   └── scraping_service.py  # trafilatura URL extraction
│   │   └── utils/
│   │       ├── tokenizer.py         # tiktoken token counting
│   │       └── logger.py            # Standard logging setup
│   ├── telegram_bot/
│   │   ├── bot.py                   # Dual mode (polling/webhook)
│   │   ├── handlers.py              # 7 commands + callbacks + auto-URL
│   │   └── utils.py                 # @restricted decorator, formatters
│   ├── tests/                       # 44 pytest tests (6 files)
│   ├── migrations/
│   │   └── schema.sql               # Full DB schema with HNSW index + GENERATED tsvector
│   ├── pyproject.toml               # uv project config + pytest + ruff
│   ├── Dockerfile                   # Backend API image
│   ├── Dockerfile.telegram          # Telegram bot image
│   └── uploads/.gitkeep             # PDF uploads directory
│
├── frontend/
│   ├── app/                         # Next.js App Router pages (11 pages)
│   │   ├── layout.tsx               # Root layout + ThemeProvider + Toaster
│   │   ├── page.tsx                 # Dashboard
│   │   ├── search/page.tsx          # RAG answer + sources
│   │   ├── notes/page.tsx           # Notes list
│   │   ├── notes/new/page.tsx       # Create note
│   │   ├── notes/[id]/page.tsx      # Edit note
│   │   ├── bookmarks/page.tsx       # Bookmarks list
│   │   ├── pdfs/page.tsx            # PDF list + upload
│   │   ├── tags/page.tsx            # Tag management
│   │   └── settings/page.tsx        # Settings
│   ├── components/                  # 9 components
│   │   ├── SearchBar.tsx            # Debounced search (300ms) + Cmd+K hint
│   │   ├── Sidebar.tsx              # Navigation + mobile collapse
│   │   ├── Header.tsx               # Page header + hamburger
│   │   ├── ThemeProvider.tsx        # next-themes wrapper
│   │   └── ui/                      # shadcn components
│   ├── lib/
│   │   ├── api.ts                   # Typed fetch wrapper for all endpoints
│   │   ├── store.ts                 # Zustand: searchQuery, sidebarOpen
│   │   └── utils.ts                 # cn() for class merging
│   ├── __tests__/                   # 17 vitest tests (3 files)
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── vitest.config.ts
│   ├── types.d.ts                   # react-highlight-words module declaration
│   └── Dockerfile                   # Multi-stage: deps → build → runner
│
├── docker-compose.yml               # 4 services + Traefik labels
├── Makefile                         # dev, build, test, deploy, db-reset
├── .env.example                     # All env var templates
├── .gitignore                       # Python/Node/Docker/IDE ignores
├── PLAN.md                          # Original project plan (reference)
├── AGENTS.md                        # 7 specialist agent roles
├── PORT-MAP.md                      # Global port allocation
├── README.md                        # GitHub README
└── CLAUDE.md                        # Main context (this file)
```

## File Organization

- **Backend:** FastAPI + SQLAlchemy ORM with async patterns throughout
- **Frontend:** Next.js 14 with TypeScript, React 18, TailwindCSS
- **Database:** PostgreSQL 16 + pgvector for semantic search
- **Infrastructure:** Docker Compose with Traefik reverse proxy
- **Testing:** pytest (backend), vitest (frontend) with >95% coverage
