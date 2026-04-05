# Second Brain — Personal Knowledge Base with AI-Powered Search

A self-hosted personal knowledge management system that captures, organizes, and retrieves your notes, PDFs, and bookmarks using semantic search and AI-powered Retrieval-Augmented Generation (RAG).

**Ask questions in natural language and get answers grounded in your own knowledge — with clear citations distinguishing your notes from general AI knowledge.**

## Features

- **Smart Capture** — Save notes, upload PDFs, and bookmark URLs via web UI or Telegram bot
- **Semantic Search** — Find content by meaning, not just keywords, powered by vector embeddings
- **Hybrid Search** — Combines semantic similarity (pgvector) with full-text search (PostgreSQL tsvector) using Reciprocal Rank Fusion
- **RAG-Powered Answers** — Ask questions and get AI responses that cite your own notes vs. general knowledge
- **Telegram Bot** — Capture thoughts and search your knowledge base on the go
- **Tag-Based Organization** — Flexible, flat tag system for organizing all content types
- **PDF Processing** — Automatic text extraction, chunking, and embedding of uploaded PDFs
- **URL Scraping** — Extracts article content from bookmarked URLs for full-text search
- **LLM Flexibility** — Toggle between Claude Haiku (fast/cheap) and Sonnet (powerful) per query
- **Privacy-First** — Single-user, self-hosted on your own VPS — your data stays yours

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                      Traefik (SSL)                       │
│              brain.armandointeligencia.com                │
└───────────────┬──────────────────────┬───────────────────┘
                │                      │
    ┌───────────▼───────────┐ ┌───────▼────────────┐
    │   Next.js Frontend    │ │   FastAPI Backend   │
    │   (App Router + SSR)  │ │   (Async Python)    │
    │                       │ │                     │
    │  • Dashboard          │ │  • REST API         │
    │  • Search UI          │ │  • RAG Pipeline     │
    │  • Note Editor        │ │  • Embedding Svc    │
    │  • PDF Viewer         │ │  • Chunking Svc     │
    │  • Bookmark Manager   │ │  • PDF Extraction   │
    └───────────────────────┘ │  • URL Scraping     │
                              └──────────┬──────────┘
                                         │
    ┌────────────────────────┐ ┌─────────▼──────────┐
    │   Telegram Bot         │ │  PostgreSQL 16      │
    │   (python-telegram-bot)│ │  + pgvector         │
    │                        │ │                     │
    │  • /add - Quick notes  │ │  • Notes, PDFs,     │
    │  • /search - RAG query │ │    Bookmarks        │
    │  • /bookmark - Save URL│ │  • Chunks + Vectors │
    │  • /list - Recent items│ │  • Full-Text Search  │
    └────────────────────────┘ │  • Tags             │
                               └─────────────────────┘
                                         │
                    ┌────────────────────┬┘
                    │                    │
           ┌───────▼──────┐    ┌───────▼──────────┐
           │ OpenAI API   │    │ Anthropic API     │
           │ Embeddings   │    │ Claude Haiku /    │
           │ (1536-dim)   │    │ Sonnet (RAG LLM)  │
           └──────────────┘    └──────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 14+, TypeScript, TailwindCSS, Shadcn/UI, SWR, Zustand |
| **Backend** | FastAPI, SQLAlchemy 2.0 (async), Pydantic 2.0, asyncpg |
| **Database** | PostgreSQL 16 + pgvector (vector search) + tsvector (full-text) |
| **Embeddings** | OpenAI text-embedding-3-small (1536 dimensions) |
| **LLM** | Anthropic Claude 3.5 Haiku / Sonnet |
| **Telegram** | python-telegram-bot 20.x (async) |
| **Infrastructure** | Docker Compose, Traefik 2.10+ (SSL/routing) |
| **Testing** | pytest (backend), vitest (frontend) |
| **Package Management** | uv (Python), npm (Node.js) |

## RAG Pipeline

The search pipeline combines two retrieval strategies for maximum recall:

1. **Semantic Search** — User query is embedded using OpenAI's text-embedding-3-small model. The query vector is compared against all stored chunk embeddings via pgvector's cosine similarity operator (`<=>`), returning the top 50 most semantically similar chunks.

2. **Full-Text Search** — The same query runs through PostgreSQL's built-in full-text search engine (tsvector + GIN index), catching exact keyword matches that semantic search might miss.

3. **Reciprocal Rank Fusion (RRF)** — Results from both searches are merged using the RRF formula: `score = Σ 1/(k + rank)` with k=60. This produces a unified ranking that benefits from both semantic understanding and keyword precision.

4. **RAG Generation** — The top 10 chunks are formatted with source metadata and sent to Claude as context. The prompt instructs the LLM to clearly distinguish between information from the user's notes (with citations) and supplementary general knowledge.

### Chunking Strategy

| Content Type | Chunk Size | Overlap | Strategy |
|-------------|-----------|---------|----------|
| Notes (<500 tokens) | Whole document | — | Single chunk |
| Notes (>500 tokens) | ~500 tokens | 50 tokens | Sentence-boundary splitting |
| PDFs | ~500 tokens | 50 tokens | Page-aware sentence splitting |
| Bookmarks | ~500 tokens | 50 tokens | Paragraph-aware splitting |

## API Endpoints

### Content Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/notes` | Create a new note |
| `GET` | `/api/v1/notes` | List notes (paginated, filterable) |
| `GET` | `/api/v1/notes/{id}` | Get note with tags |
| `PUT` | `/api/v1/notes/{id}` | Update note content |
| `DELETE` | `/api/v1/notes/{id}` | Archive/delete note |
| `POST` | `/api/v1/bookmarks` | Save and scrape a URL |
| `GET` | `/api/v1/bookmarks` | List bookmarks |
| `POST` | `/api/v1/pdfs/upload` | Upload and process PDF |
| `GET` | `/api/v1/pdfs` | List uploaded PDFs |

### Search & RAG
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/search` | Hybrid search with RAG answer |
| `POST` | `/api/v1/search/raw` | Raw chunk search (no LLM) |

### Organization
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/tags` | List all tags |
| `POST` | `/api/v1/tags` | Create tag |
| `GET` | `/api/v1/settings` | Get user settings |
| `PUT` | `/api/v1/settings` | Update settings |

## Telegram Bot Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/add <text>` | Quick note capture | `/add Learned about pgvector today` |
| `/search <query>` | Search with RAG | `/search What is backpropagation?` |
| `/bookmark <url>` | Save and scrape URL | `/bookmark https://example.com/article` |
| `/list` | Show recent items | `/list` |
| `/tags` | Show all tags | `/tags` |
| `/settings` | View/toggle LLM model | `/settings` |
| `/help` | Show commands | `/help` |

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker & Docker Compose
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- OpenAI API key (for embeddings)
- Anthropic API key (for Claude LLM)
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/armandogonzalez/second-brain.git
   cd second-brain
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

3. **Start the database**
   ```bash
   docker compose up -d postgres
   ```

4. **Run the backend**
   ```bash
   cd backend
   uv sync
   uv run uvicorn app.main:app --reload --port 8110
   ```

5. **Run the frontend**
   ```bash
   cd frontend
   npm install
   npm run dev -- -p 3110
   ```

6. **Run the Telegram bot**
   ```bash
   cd backend
   uv run python -m telegram_bot.bot
   ```

### Docker Compose (Production)

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f backend

# Stop all services
docker compose down
```

The application will be available at:
- **Frontend:** http://localhost:3110
- **Backend API:** http://localhost:8110/api/v1
- **API Docs:** http://localhost:8110/docs

### Production Deployment

Deploy to a VPS with Traefik for SSL termination:

```bash
# On your VPS
git clone https://github.com/armandogonzalez/second-brain.git
cd second-brain
cp .env.example .env
# Configure production environment variables
docker compose -f docker-compose.yml up -d
```

Production URLs:
- **Frontend:** https://brain.armandointeligencia.com
- **API:** https://api.brain.armandointeligencia.com

## Project Structure

```
second-brain/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── config.py            # Environment configuration
│   │   ├── models.py            # SQLAlchemy ORM models
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── database.py          # Async database connection
│   │   ├── api/                 # Route handlers
│   │   │   ├── notes.py         # Notes CRUD
│   │   │   ├── bookmarks.py     # Bookmarks CRUD + scraping
│   │   │   ├── pdfs.py          # PDF upload + processing
│   │   │   ├── search.py        # Hybrid search + RAG
│   │   │   ├── tags.py          # Tag management
│   │   │   └── settings.py      # User settings
│   │   ├── services/            # Business logic
│   │   │   ├── chunking_service.py   # Text chunking
│   │   │   ├── embedding_service.py  # OpenAI embeddings
│   │   │   ├── rag_service.py        # RAG orchestration
│   │   │   ├── llm_service.py        # Claude API
│   │   │   ├── pdf_service.py        # PDF text extraction
│   │   │   └── scraping_service.py   # URL article extraction
│   │   └── utils/
│   │       ├── tokenizer.py     # Token counting
│   │       └── logger.py        # Structured logging
│   ├── telegram_bot/
│   │   ├── bot.py               # Bot initialization
│   │   ├── handlers.py          # Command handlers
│   │   └── utils.py             # Formatting helpers
│   ├── tests/                   # pytest test suite
│   ├── pyproject.toml           # Python dependencies (uv)
│   └── Dockerfile
├── frontend/
│   ├── app/                     # Next.js App Router pages
│   │   ├── page.tsx             # Dashboard
│   │   ├── search/page.tsx      # Search results
│   │   ├── notes/               # Notes list + editor
│   │   ├── bookmarks/page.tsx   # Bookmarks
│   │   ├── pdfs/page.tsx        # PDF library
│   │   ├── tags/page.tsx        # Tag management
│   │   └── settings/page.tsx    # Settings
│   ├── components/              # Reusable UI components
│   ├── lib/                     # API client, stores, utils
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── Makefile
├── .env.example
└── README.md
```

## Testing

```bash
# Backend tests
cd backend
uv run pytest -v

# Frontend tests
cd frontend
npx vitest

# Run all tests
make test
```

### Test Coverage

- **Backend (pytest):** API endpoints, chunking logic, embedding pipeline, search quality, Telegram bot handlers
- **Frontend (vitest):** Search component, note editor, PDF viewer, tag management

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `OPENAI_API_KEY` | OpenAI API key (embeddings) | Yes |
| `ANTHROPIC_API_KEY` | Anthropic API key (Claude) | Yes |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | Yes |
| `TELEGRAM_USER_ID` | Authorized Telegram user ID | Yes |
| `SECRET_KEY` | Application secret key | Yes |
| `ENVIRONMENT` | `development` or `production` | No |
| `LOG_LEVEL` | Logging level (default: INFO) | No |
| `LETSENCRYPT_EMAIL` | Email for SSL certificates | Prod only |

## Database Schema

The system uses 8 tables in PostgreSQL with the pgvector extension:

- **users** — Single user with LLM preference
- **notes** — Text content with markdown support
- **bookmarks** — Scraped URLs with extracted article text
- **pdfs** — Uploaded documents with extracted text
- **chunks** — Text segments for embedding (~500 tokens each)
- **embeddings** — 1536-dimensional vectors linked to chunks
- **tags** — User-defined labels with colors
- **tag_assignments** — Polymorphic many-to-many (tags ↔ notes/bookmarks/pdfs)

## License

MIT

## Author

**Armando Gonzalez** — [armandointeligencia.com](https://armandointeligencia.com)
