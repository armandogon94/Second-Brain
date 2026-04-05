# Project 11: Second Brain / Personal Knowledge Base
## Comprehensive Implementation Plan for Armando

---

## PROJECT OVERVIEW

**Project Name:** Second Brain / Personal Knowledge Base
**Subdomain:** brain.armandointeligencia.com
**Owner:** Armando Gonzalez
**Purpose:** A personal knowledge management system that captures, organizes, and retrieves Armando's notes, PDFs, and bookmarks using semantic search and AI-powered retrieval-augmented generation (RAG).

**Core Value Proposition:**
- Centralized capture of personal knowledge (notes, PDFs, bookmarks)
- Intelligent search that understands intent, not just keywords
- AI assistance that distinguishes between user's own knowledge and general AI knowledge
- Accessible via web UI and Telegram bot for fast capture on-the-go
- Single-user, privacy-focused (all data stored on personal VPS)

**Key Constraints & Design Decisions:**
- Single user (Armando only) — no multi-user authentication required
- Tag-based organization (no folders/hierarchy) for simplicity and flexibility
- Blended AI approach: user content + general knowledge, with clear citations
- Cheap-first LLM strategy: Haiku for most queries, optional Sonnet toggle for complex work
- No separate vector DB — leverage PostgreSQL's pgvector extension
- Docker Compose deployment on Hostinger VPS (2 vCPU, 8GB RAM)

---

## TECH STACK

**Backend:**
- FastAPI 0.104+ (async Python web framework)
- SQLAlchemy 2.0+ (ORM with async support)
- asyncpg (async PostgreSQL driver)
- Pydantic 2.0+ (data validation)
- python-telegram-bot 20.5+ (Telegram bot framework)
- httpx 0.25+ (async HTTP client)
- BeautifulSoup4 4.12+ (HTML parsing for URL scraping)
- pdfplumber 0.10+ (PDF text extraction)
- Anthropic SDK 0.20+ (Claude API integration)
- openai 1.3+ (embeddings API)

**Frontend:**
- Next.js 14+ (React framework with App Router)
- TypeScript 5.3+
- TailwindCSS 3.4+
- Shadcn/UI (component library)
- SWR 2.2+ (data fetching)
- zustand 4.4+ (state management)

**Database & Infrastructure:**
- PostgreSQL 16 (with pgvector extension 0.5+)
- Docker & Docker Compose (container orchestration)
- Traefik 2.10+ (reverse proxy for SSL/routing)
- Hostinger VPS (2 vCPU, 8GB RAM, Ubuntu 22.04 LTS)

**Development Tools:**
- uv (fast Python package installer)
- pytest 7.4+ (backend testing)
- vitest 1.0+ (frontend testing)
- Git (version control)

**ML/AI Components:**
- OpenAI text-embedding-3-small (1536-dim embeddings)
- Anthropic Claude Haiku & Sonnet (LLM inference)
- pgvector (PostgreSQL semantic search)

---

## DATABASE SCHEMA

### PostgreSQL Setup

```sql
-- Enable vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable full-text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Notes table (text capture)
CREATE TABLE notes (
    id SERIAL PRIMARY KEY,
    user_id INT DEFAULT 1,  -- Single user hardcoded for now
    content TEXT NOT NULL,
    markdown_content TEXT,  -- Original markdown
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(50) NOT NULL,  -- 'web_ui', 'telegram'
    is_archived BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}',  -- Custom metadata
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Bookmarks table (URLs scraped from links)
CREATE TABLE bookmarks (
    id SERIAL PRIMARY KEY,
    user_id INT DEFAULT 1,
    original_url TEXT NOT NULL,
    title VARCHAR(255),
    scraped_content TEXT,  -- Full article text from URL
    source_domain VARCHAR(255),
    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_read BOOLEAN DEFAULT FALSE,
    is_archived BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}',
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, original_url)
);

-- PDFs table (uploaded documents)
CREATE TABLE pdfs (
    id SERIAL PRIMARY KEY,
    user_id INT DEFAULT 1,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    extracted_text TEXT,  -- Full text from PDF
    page_count INT,
    file_size INT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_archived BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}',
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Chunks table (segmented text for embedding)
CREATE TABLE chunks (
    id SERIAL PRIMARY KEY,
    user_id INT DEFAULT 1,
    source_type VARCHAR(50) NOT NULL,  -- 'note', 'bookmark', 'pdf'
    source_id INT NOT NULL,  -- References notes.id, bookmarks.id, or pdfs.id
    chunk_index INT NOT NULL,  -- Order within source
    content TEXT NOT NULL,  -- Chunk text (~500 tokens)
    character_count INT,
    token_count INT,  -- Estimated from content length
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Embeddings table (vectors for semantic search)
CREATE TABLE embeddings (
    id SERIAL PRIMARY KEY,
    chunk_id INT NOT NULL UNIQUE,
    embedding vector(1536),  -- OpenAI text-embedding-3-small dimensionality
    embedding_model VARCHAR(100) DEFAULT 'text-embedding-3-small',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_chunk FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE,
    INDEX idx_embedding ON embeddings USING ivfflat (embedding vector_cosine_ops)
);

-- Tags table
CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    user_id INT DEFAULT 1,
    name VARCHAR(100) NOT NULL,
    color VARCHAR(7),  -- Hex color for UI
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, name)
);

-- Tag assignments (many-to-many)
CREATE TABLE tag_assignments (
    id SERIAL PRIMARY KEY,
    tag_id INT NOT NULL,
    source_type VARCHAR(50) NOT NULL,  -- 'note', 'bookmark', 'pdf'
    source_id INT NOT NULL,  -- References notes.id, bookmarks.id, or pdfs.id
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tag FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
    UNIQUE(tag_id, source_type, source_id)
);

-- Full-text search index for notes
CREATE INDEX idx_notes_fts ON notes USING GIN (to_tsvector('english', content));

-- Full-text search index for bookmarks
CREATE INDEX idx_bookmarks_fts ON bookmarks USING GIN (to_tsvector('english', scraped_content));

-- Full-text search index for chunks (for hybrid search)
CREATE INDEX idx_chunks_fts ON chunks USING GIN (to_tsvector('english', content));

-- Indexes for common queries
CREATE INDEX idx_notes_user_created ON notes(user_id, created_at DESC);
CREATE INDEX idx_bookmarks_user_created ON bookmarks(user_id, captured_at DESC);
CREATE INDEX idx_pdfs_user_uploaded ON pdfs(user_id, uploaded_at DESC);
CREATE INDEX idx_chunks_source ON chunks(source_type, source_id);
CREATE INDEX idx_tags_user ON tags(user_id, name);
```

### Users Table (minimal)
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    telegram_user_id BIGINT,  -- For Telegram bot integration
    llm_preference VARCHAR(50) DEFAULT 'haiku',  -- 'haiku' or 'sonnet'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    settings JSONB DEFAULT '{}'
);

-- Insert single user (Armando)
INSERT INTO users (username, telegram_user_id, llm_preference)
VALUES ('armando', NULL, 'haiku')
ON CONFLICT DO NOTHING;
```

---

## RAG PIPELINE

### Chunking Strategy

**Objective:** Break source text into semantically meaningful units for embedding and retrieval.

**Parameters:**
- Target chunk size: ~500 tokens (≈ 2000 characters for English prose)
- Overlap: ~50 tokens (≈ 200 characters) to maintain context across chunk boundaries
- Minimum chunk size: 100 tokens (discard very small fragments)
- Maximum chunk size: 1000 tokens (split larger chunks)

**Algorithm:**
1. Split source text by sentences (use NLTK or simple regex)
2. Group sentences into chunks, accumulating tokens until ~500 is reached
3. Add 50-token overlap from end of previous chunk to beginning of next
4. Store chunk_index in chunks table to track order
5. Estimate token count: `token_count ≈ len(chunk_text) / 4` (conservative)

**Implementation Details:**
- Use OpenAI's tokenizer (tiktoken) for accurate counts if available
- For PDFs: extract text per page, then chunk across pages
- For bookmarks: chunk the full article text (from scrape)
- For notes: if >500 tokens, chunk; otherwise store as single chunk

### Embedding Workflow

**Trigger Points:**
- New note saved → chunk → embed
- PDF uploaded → extract text → chunk → embed
- URL sent via Telegram/UI → scrape → chunk → embed

**Embedding Process:**
1. Get all chunks from source (e.g., new note created 3 chunks)
2. For each chunk, call OpenAI Embeddings API:
   - Model: `text-embedding-3-small`
   - Input: chunk.content (up to 8191 tokens per request)
   - Output: 1536-dim vector
3. Store vector in embeddings table linked to chunk_id
4. Handle rate limits (batch requests, exponential backoff)
5. Log failures and retry failed embeddings

### Retrieval + Reranking

**Search Flow (Hybrid Approach):**

1. **User submits query** → normalize to lowercase, max 500 chars
2. **Embed the query** using same text-embedding-3-small model
3. **Semantic search via pgvector:**
   ```sql
   SELECT
       c.id, c.source_type, c.source_id, c.content,
       1 - (e.embedding <=> query_embedding::vector) AS similarity
   FROM chunks c
   JOIN embeddings e ON c.id = e.chunk_id
   WHERE c.user_id = 1
   ORDER BY e.embedding <=> query_embedding::vector
   LIMIT 50  -- Retrieve top 50 for reranking
   ```
4. **Full-text search (fallback):**
   ```sql
   SELECT c.id, c.source_type, c.source_id, c.content,
       ts_rank(to_tsvector('english', c.content), query_ts) AS rank
   FROM chunks c
   WHERE c.user_id = 1 AND to_tsvector('english', c.content) @@ query_ts
   ORDER BY rank DESC
   LIMIT 20
   ```
5. **Combine results:**
   - Merge semantic + full-text results, deduplicate by chunk_id
   - Weight semantic results 70%, full-text 30%
   - Select top 10 chunks for LLM context
6. **Retrieve source metadata:**
   - For each chunk, fetch original note/bookmark/PDF title
   - Include source_type and source_id for citations

### RAG Prompt Template

**System Prompt:**
```
You are a helpful assistant that answers questions based on the user's personal knowledge base.

IMPORTANT: You must distinguish between:
1. Information FROM THE USER'S OWN NOTES (explicitly marked as "From your notes:")
2. General knowledge or reasoning YOU provide (explicitly marked as "From general knowledge:")

Always cite which information comes from where. If you use information from the user's notes,
always include the source (e.g., note title, PDF name).

When answering:
- Always check the provided notes first. If the answer is in the user's notes, use that and cite it.
- If the user's notes don't fully answer the question, supplement with general knowledge.
- Be clear about what is their knowledge vs. what is general knowledge.
- Never claim information from the user's notes if it's not actually there.
```

**Query Prompt:**
```
Question: {user_query}

---

From your notes:

{retrieved_chunks_with_sources}

---

Based on the information above from the user's notes and supplemented with general knowledge as needed,
please answer the question. Clearly distinguish what comes from the user's notes vs. general knowledge.

Format your answer with citations like this:
- "According to your notes on [source], ..."
- "From general knowledge, ..."
```

**Example Retrieved Chunks Section:**
```
[From your notes - "Machine Learning Basics" (note, 2026-03-15)]
Chunk 1: "Machine learning is a subset of AI where algorithms learn patterns from data.
Supervised learning uses labeled examples to train models..."

[From your notes - "ML_Book.pdf" (PDF, page 3)]
Chunk 2: "The backpropagation algorithm adjusts weights in neural networks by computing
gradients with respect to the loss function..."
```

**Expected Response Format:**
```
Machine learning is a subset of artificial intelligence where algorithms learn patterns from data
without being explicitly programmed. According to your notes on "Machine Learning Basics",
supervised learning uses labeled examples to train models.

From general knowledge, there are also unsupervised learning approaches (clustering, dimensionality
reduction) and reinforcement learning (learning from rewards and penalties).
```

---

## API ENDPOINTS

### Backend (FastAPI) - `/api/v1`

**Notes Endpoints:**
- `POST /notes` - Create new note
  - Body: `{ content: string, markdown_content?: string, tags?: string[] }`
  - Response: `{ id: int, created_at: datetime }`
- `GET /notes` - List user's notes (paginated)
  - Query: `?skip=0&limit=20&archived=false&tag=tagname`
  - Response: `{ notes: Note[], total: int }`
- `GET /notes/{id}` - Retrieve single note with tags
- `PUT /notes/{id}` - Update note content
- `DELETE /notes/{id}` - Archive (soft delete) or hard delete
- `POST /notes/{id}/tags` - Add tags to note
  - Body: `{ tag_ids: int[] }`

**Bookmarks Endpoints:**
- `POST /bookmarks` - Create bookmark (URL scraping)
  - Body: `{ url: string, tags?: string[] }`
  - Response: `{ id: int, title: string, captured_at: datetime }`
- `GET /bookmarks` - List bookmarks (paginated, filterable)
- `GET /bookmarks/{id}` - Retrieve bookmark with full content
- `PUT /bookmarks/{id}` - Mark as read, update tags
- `DELETE /bookmarks/{id}` - Archive or delete

**PDFs Endpoints:**
- `POST /pdfs/upload` - Upload PDF file (multipart form)
  - Triggers: text extraction → chunking → embedding
  - Response: `{ id: int, filename: string, page_count: int }`
- `GET /pdfs` - List user's PDFs (paginated)
- `GET /pdfs/{id}` - Retrieve PDF metadata + extracted text preview
- `DELETE /pdfs/{id}` - Archive or delete

**Search Endpoints:**
- `POST /search` - Hybrid semantic + full-text search
  - Body: `{ query: string, limit?: int, llm_model?: 'haiku' | 'sonnet' }`
  - Response: `{ answer: string, sources: Source[], usage: { input_tokens, output_tokens } }`
- `POST /search/raw` - Return raw chunks without RAG
  - Body: `{ query: string, limit?: int, include_scores?: bool }`
  - Response: `{ chunks: Chunk[], scores: float[] }`

**Tags Endpoints:**
- `GET /tags` - List all user's tags
  - Response: `{ tags: Tag[] }`
- `POST /tags` - Create new tag
  - Body: `{ name: string, color?: string }`
- `DELETE /tags/{id}` - Delete tag

**Settings Endpoints:**
- `GET /settings` - Retrieve user settings
  - Response: `{ llm_preference: 'haiku' | 'sonnet', ... }`
- `PUT /settings` - Update settings
  - Body: `{ llm_preference?: string }`

**Health/Admin:**
- `GET /health` - Health check
- `POST /admin/reindex` - Force re-embedding of all chunks (admin only)

---

## TELEGRAM BOT COMMANDS

**Bot Token:** Set via environment variable `TELEGRAM_BOT_TOKEN`
**User ID:** Accept commands only from Armando's Telegram user ID (via `TELEGRAM_USER_ID` env var)

**Commands:**

1. `/add <text>` - Capture quick note
   - Usage: `/add Learned about pgvector today, very fast for semantic search`
   - Response: "Note saved! Added tags: [+Add Tags]"
   - Auto-tags: optional inline button "Add Tags"

2. `/search <query>` - Search knowledge base with RAG
   - Usage: `/search What is pgvector?`
   - Response: Shows answer with sources, inline buttons:
     - "View Full Note" (links to web UI)
     - "Ask Claude Sonnet" (re-run with Sonnet model)

3. `/bookmark <url>` - Scrape URL and store
   - Usage: `/bookmark https://example.com/article`
   - Response: Shows extracted title, preview, and "Save" confirmation button
   - On confirm: stores, embeds, returns "Bookmark saved!"

4. `/list` - Show recent notes/bookmarks
   - Response: Last 5 items with inline "View" and "Tag" buttons

5. `/tags` - Show all tags and counts
   - Response: "Your tags (X total): #ai (5), #learning (3), ..."

6. `/settings` - Show current settings
   - Response: "Current settings: LLM=Haiku, Default Tags=None"
   - Inline button: "Toggle to Sonnet"

7. `/help` - Show available commands

**Inline Buttons:**
- After `/add`: "Add Tags" → prompts user to enter comma-separated tags
- After `/search`: "Full Note" (opens web UI), "Sonnet" (rerun with Sonnet)
- After `/bookmark`: "Save", "Skip"
- `/list` results: "View", "Tag", "Delete"

**Error Handling:**
- If URL scraping fails: "Couldn't extract content from that URL. Try again?"
- If query embedding fails: "Search temporarily unavailable. Try again in a moment."
- Rate limiting: "Too many requests. Please wait before trying again."

---

## FRONTEND PAGES

**Next.js App Router structure** (`app/` directory):

1. **Dashboard** (`/`)
   - Hero section with quick actions: "Add Note", "Upload PDF", "Paste URL"
   - Recent items grid (6 most recent across all types)
   - Tag cloud on sidebar
   - Search bar (prominent, center)

2. **Search Results** (`/search`)
   - Display RAG answer with highlighted sources
   - Source cards below answer (clickable to view full item)
   - "Refine Search" input field
   - Toggle: "Show sources" / "Full answer"
   - Copy answer button

3. **Notes** (`/notes`)
   - List view with pagination
   - Filters: Tag, date range, search within notes
   - New Note button (modal or dedicated page)
   - Each note shows: preview, tags, created date
   - Click to expand/view full content

4. **Note Editor** (`/notes/[id]`)
   - Full editor with markdown syntax highlighting
   - Tag manager on right sidebar (add/remove tags)
   - Save & Cancel buttons
   - Auto-save indicator
   - Delete option (confirm dialog)

5. **Bookmarks** (`/bookmarks`)
   - Grid or list of captured URLs
   - Filters: read/unread status, tag, domain
   - "Mark as Read" toggle
   - "Add Bookmark" button (modal: paste URL)
   - Bookmark preview card shows: title, domain, date, tags

6. **PDFs** (`/pdfs`)
   - List with PDF thumbnails (if possible) or file icon
   - File details: name, page count, size, upload date
   - Upload area (drag-drop or file input)
   - Click to view extracted text preview

7. **Tags** (`/tags`)
   - Table of all tags with counts
   - Edit tag (rename, change color)
   - Delete tag (with confirmation)
   - Create new tag form

8. **Settings** (`/settings`)
   - LLM model preference: Radio buttons (Haiku / Sonnet)
   - Default tags for new notes (optional)
   - Appearance: Dark/Light mode toggle
   - Danger zone: Export data, Delete all (confirm dialog)

9. **About** (`/about`)
   - Project info
   - Keyboard shortcuts guide
   - Version info

**Shared Components:**
- `SearchBar` - Featured search input
- `TagPill` - Clickable tag component
- `SourceCard` - Preview of note/bookmark/PDF source
- `Sidebar` - Navigation + tag cloud
- `Header` - Logo, settings link

---

## PROJECT STRUCTURE

```
second-brain/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── config.py               # Environment & settings
│   │   ├── models.py               # SQLAlchemy ORM models
│   │   ├── schemas.py              # Pydantic request/response schemas
│   │   ├── database.py             # Connection pool & session management
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── notes.py            # /api/v1/notes endpoints
│   │   │   ├── bookmarks.py        # /api/v1/bookmarks endpoints
│   │   │   ├── pdfs.py             # /api/v1/pdfs endpoints
│   │   │   ├── search.py           # /api/v1/search endpoints
│   │   │   ├── tags.py             # /api/v1/tags endpoints
│   │   │   └── settings.py         # /api/v1/settings endpoints
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── embedding_service.py    # OpenAI embedding calls
│   │   │   ├── chunking_service.py     # Text chunking logic
│   │   │   ├── pdf_service.py          # PDF extraction
│   │   │   ├── scraping_service.py     # URL scraping
│   │   │   ├── rag_service.py          # RAG search & prompt
│   │   │   └── llm_service.py          # Claude API calls
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── tokenizer.py        # Token counting
│   │       └── logger.py           # Logging setup
│   ├── telegram_bot/
│   │   ├── __init__.py
│   │   ├── bot.py                  # Main bot loop
│   │   ├── handlers.py             # Command handlers (/add, /search, etc.)
│   │   └── utils.py                # Helper functions
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_api_notes.py
│   │   ├── test_search.py
│   │   ├── test_chunking.py
│   │   └── test_embedding.py
│   ├── requirements.txt            # Python dependencies
│   ├── Dockerfile
│   └── README.md
├── frontend/
│   ├── app/
│   │   ├── layout.tsx              # Root layout
│   │   ├── page.tsx                # Dashboard page
│   │   ├── search/
│   │   │   └── page.tsx
│   │   ├── notes/
│   │   │   ├── page.tsx            # Notes list
│   │   │   ├── [id]/
│   │   │   │   └── page.tsx        # Note editor
│   │   │   └── new/
│   │   │       └── page.tsx        # New note modal
│   │   ├── bookmarks/
│   │   │   └── page.tsx
│   │   ├── pdfs/
│   │   │   └── page.tsx
│   │   ├── tags/
│   │   │   └── page.tsx
│   │   └── settings/
│   │       └── page.tsx
│   ├── components/
│   │   ├── SearchBar.tsx
│   │   ├── TagPill.tsx
│   │   ├── SourceCard.tsx
│   │   ├── Sidebar.tsx
│   │   ├── Header.tsx
│   │   └── ...
│   ├── lib/
│   │   ├── api.ts                  # Fetch wrappers
│   │   ├── store.ts                # Zustand stores
│   │   └── utils.ts
│   ├── styles/
│   │   └── globals.css
│   ├── public/                     # Static assets
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── Dockerfile
│   └── README.md
├── docker-compose.yml              # Services: postgres, backend, frontend, telegram-bot
├── .env.example                    # Template for environment variables
├── PLAN.md                         # This file
└── README.md
```

---

## DOCKER COMPOSE

**Note:** See PORT-MAP.md for the complete port allocation across all projects.

```yaml
version: '3.8'

services:
  # PostgreSQL database with pgvector
  postgres:
    image: pgvector/pgvector:pg16
    container_name: second-brain-db
    environment:
      POSTGRES_USER: ${DB_USER:-armando}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-changeme}
      POSTGRES_DB: ${DB_NAME:-second_brain}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/migrations/schema.sql:/docker-entrypoint-initdb.d/01-schema.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-armando}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - second-brain-network

  # FastAPI backend
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: second-brain-backend
    environment:
      DATABASE_URL: postgresql+asyncpg://${DB_USER:-armando}:${DB_PASSWORD:-changeme}@postgres:5432/${DB_NAME:-second_brain}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
      TELEGRAM_USER_ID: ${TELEGRAM_USER_ID}
      ENVIRONMENT: production
    ports:
      - "8110:8000"
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./backend:/app
      - uploads:/app/uploads
    networks:
      - second-brain-network
    restart: unless-stopped
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000

  # Next.js frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: second-brain-frontend
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8110
    ports:
      - "3110:3000"
    depends_on:
      - backend
    volumes:
      - ./frontend:/app
      - /app/.next
    networks:
      - second-brain-network
    restart: unless-stopped

  # Telegram bot service
  telegram-bot:
    build:
      context: ./backend
      dockerfile: Dockerfile.telegram
    container_name: second-brain-telegram
    environment:
      DATABASE_URL: postgresql+asyncpg://${DB_USER:-armando}:${DB_PASSWORD:-changeme}@postgres:5432/${DB_NAME:-second_brain}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
      TELEGRAM_USER_ID: ${TELEGRAM_USER_ID}
      ENVIRONMENT: production
    ports:
      - "8111:8001"
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./backend:/app
    networks:
      - second-brain-network
    restart: unless-stopped
    command: python -m telegram_bot.bot

  # Traefik reverse proxy (handles SSL, routing)
  traefik:
    image: traefik:v2.10
    container_name: second-brain-traefik
    command:
      - "--api.insecure=false"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
      - "--certificatesresolvers.letsencrypt.acme.email=${LETSENCRYPT_EMAIL}"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./traefik/letsencrypt:/letsencrypt
    networks:
      - second-brain-network
    restart: unless-stopped

volumes:
  postgres_data:
  uploads:

networks:
  second-brain-network:
    driver: bridge
```

**Traefik Labels for Services:**

See PORT-MAP.md for the complete port allocation across all projects.

Add to backend service:
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.backend.rule=Host(`api.brain.armandointeligencia.com`)"
  - "traefik.http.routers.backend.entrypoints=websecure"
  - "traefik.http.routers.backend.tls.certresolver=letsencrypt"
  - "traefik.http.services.backend.loadbalancer.server.port=8000"
```

Add to frontend service:
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.frontend.rule=Host(`brain.armandointeligencia.com`)"
  - "traefik.http.routers.frontend.entrypoints=websecure"
  - "traefik.http.routers.frontend.tls.certresolver=letsencrypt"
  - "traefik.http.services.frontend.loadbalancer.server.port=3000"
```

---

## TIMELINE & EFFORT ESTIMATION

**Total Estimated Duration: 65-75 hours**

### Phase 1: Foundation & Setup (10 hours)
- Project scaffolding, Docker Compose, environment setup: 3 hours
- PostgreSQL schema + migrations + pgvector setup: 4 hours
- Basic FastAPI app skeleton + async database layer: 3 hours

### Phase 2: Core API Backend (20 hours)
- Notes CRUD endpoints: 4 hours
- PDF upload + text extraction + chunking pipeline: 6 hours
- Bookmark scraping (URL → stored article): 5 hours
- Tag management & associations: 3 hours
- Error handling & validation: 2 hours

### Phase 3: Embedding & Search (18 hours)
- Embedding service (OpenAI API integration): 4 hours
- Chunking service (tokenization, overlap logic): 4 hours
- Hybrid search (pgvector semantic + PostgreSQL FTS): 6 hours
- RAG integration (Claude API + prompt templates): 4 hours

### Phase 4: Telegram Bot (10 hours)
- Bot initialization & command handlers: 4 hours
- Message formatting & inline keyboards: 3 hours
- Bot API integration (to backend): 2 hours
- Rate limiting & error handling: 1 hour

### Phase 5: Frontend (12 hours)
- Next.js setup + basic layout + Shadcn/UI: 3 hours
- Dashboard, Notes, Bookmarks, PDFs pages: 4 hours
- Search interface + RAG display: 3 hours
- Settings & tag management UI: 2 hours

### Phase 6: Testing & Deployment (5 hours)
- Unit tests (backend): 2 hours
- Integration tests: 2 hours
- Deploy to Hostinger (Docker Compose, Traefik, SSL): 1 hour

---

## FUTURE IMPROVEMENTS (Nice-to-Haves)

1. **Advanced Features:**
   - Spaced repetition system (SRS) for review of notes
   - Automatic backlinking (detect mentions of past notes)
   - Collections/workspaces for organizing projects
   - Collaborative features (limited sharing of specific notes)

2. **LLM Enhancements:**
   - Fine-tuning on user's notes corpus for better personalization
   - Multi-turn conversation with memory (not just single-query RAG)
   - Automatic note summarization & synthesis
   - Concept extraction (auto-tag based on content)

3. **Data Import/Export:**
   - Import from Notion, Obsidian, Roam Research
   - Export to Markdown, PDF, HTML
   - Backup scheduling to cloud (S3, etc.)

4. **Search Improvements:**
   - Date-range filtering
   - Advanced query syntax (AND, OR, NOT operators)
   - Saved searches / search history
   - Semantic auto-complete suggestions

5. **UI/UX:**
   - Rich text editor (vs. markdown)
   - Dark mode refinements
   - Mobile app (React Native or PWA)
   - Keyboard shortcuts cheatsheet

6. **Integrations:**
   - IFTTT / Zapier for auto-capture
   - Email-to-note (send email to special address)
   - Slack integration (capture messages, search from Slack)
   - Web clipper browser extension

7. **Analytics:**
   - Knowledge graph visualization (nodes = notes, edges = links)
   - Usage statistics dashboard
   - Most-referenced notes / bookmarks

8. **Performance:**
   - Caching layer (Redis) for frequent queries
   - Batch embedding to reduce API costs
   - Pagination optimization for large datasets
   - Search result pagination improvements

---

## ENVIRONMENT VARIABLES

Create `.env` file in project root:

```bash
# Database
DB_USER=armando
DB_PASSWORD=your_secure_password_here
DB_NAME=second_brain
DATABASE_URL=postgresql+asyncpg://armando:your_secure_password_here@postgres:5432/second_brain

# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_USER_ID=your_user_id

# Deployment
ENVIRONMENT=production
LETSENCRYPT_EMAIL=your_email@example.com
NEXT_PUBLIC_API_URL=https://api.brain.armandointeligencia.com

# App Settings
SECRET_KEY=your_random_secret_key_for_sessions
LOG_LEVEL=INFO
```

---

## SUCCESS CRITERIA

- All notes/bookmarks/PDFs can be captured, stored, and retrieved
- Semantic search returns relevant results (top-3 retrieval accuracy >80%)
- RAG correctly distinguishes user's content from general knowledge
- Telegram bot responds to commands within 2 seconds
- Web UI loads in <2 seconds on typical connection
- Full-text search works for queries without embeddings
- System handles 1000+ chunks without performance degradation
- All endpoints have proper error handling & logging

---

## NOTES FOR IMPLEMENTATION

- Start with single-user assumption hardcoded (user_id = 1)
- Use asyncio throughout for I/O-bound operations (database, API calls)
- Implement exponential backoff for external API failures
- Log all API calls and errors for debugging
- Use database transactions for consistency (notes + chunks + embeddings created together)
- Index embeddings with IVFFLAT for faster approximate nearest neighbor search
- Consider batch embedding requests to reduce API costs
- Monitor token usage for both embedding and LLM APIs
- Plan for future migration to multi-user if needed (schema already supports it)

---

**Document Version:** 1.0
**Last Updated:** 2026-04-01
**Status:** Implementation-Ready
