# SPEC.md — Second Brain v2: LLM Wiki Integration

> Version: 2.0
> Date: 2026-04-11
> Status: Draft
> Decisions: See [DECISIONS.md](DECISIONS.md)

---

## 1. Objective

Evolve the Second Brain from a CRUD + RAG search tool into a **knowledge compiler** by integrating Andrej Karpathy's [LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

**The core shift:** Instead of re-deriving structure on every query (current RAG), the LLM pre-compiles raw sources (notes, bookmarks, PDFs) into structured wiki pages with `[[wikilinks]]`, maintaining an interlinked knowledge graph that compounds over time. Queries navigate compiled knowledge first, falling back to embedding search when needed.

### Target User

Armando (single user) — captures notes, bookmarks, and PDFs; wants AI to organize and cross-reference them automatically.

### Success Criteria

- Compilation of raw sources into structured wiki pages with `[[wikilinks]]`
- Interactive knowledge graph visualization in the browser
- Wiki-first query mode that checks compiled knowledge before RAG search
- Obsidian-compatible export (`.md` files with YAML frontmatter + wikilinks)
- Incremental compilation (only recompile when sources change)
- Health checks: detect orphan pages, broken links, stale content

---

## 2. Current State (v1 MVP — Complete)

| Area | Status |
|------|--------|
| Backend (FastAPI + async) | 44/44 tests pass |
| Frontend (Next.js 14) | 17/17 tests pass, builds clean |
| Docker Compose | 4 services, all healthy |
| Database | 8 tables, pgvector HNSW + GIN indexes |
| API | 22+ endpoints (notes, bookmarks, PDFs, search, tags, settings) |
| Frontend pages | 10 (dashboard, search, notes CRUD, bookmarks, PDFs, tags, settings) |
| Telegram bot | 7 commands, auto-URL detection, webhook/polling dual mode |
| RAG pipeline | Hybrid search (pgvector + tsvector RRF) + Claude Haiku/Sonnet |

### Existing Tables

`users`, `notes`, `bookmarks`, `pdfs`, `chunks`, `embeddings`, `tags`, `tag_assignments`

### Existing Services

`chunking_service`, `embedding_service`, `rag_service`, `llm_service`, `pdf_service`, `scraping_service`

---

## 3. New Feature: LLM Wiki Layer

### 3.1 Three-Layer Architecture (Karpathy-adapted)

```
Layer 1: Raw Sources (existing)       Layer 2: Wiki (new)           Layer 3: Schema
┌────────────────────────┐    LLM     ┌─────────────────────┐     ┌──────────────┐
│ notes                  │  compile   │ wiki_pages          │     │ Compilation  │
│ bookmarks              │ ───────>   │   [[wikilinks]]     │     │ prompts +    │
│ pdfs                   │            │   YAML frontmatter  │     │ page type    │
└────────────────────────┘            │   index.md          │     │ definitions  │
                                      └─────────────────────┘     └──────────────┘
```

- **Raw sources** = existing notes, bookmarks, PDFs (immutable during compilation)
- **Wiki** = LLM-generated wiki pages stored in `wiki_pages` table
- **Schema** = compilation system prompts defining page structure and types

### 3.2 Core Concepts

**Wiki pages** — LLM-compiled markdown articles with:
- YAML frontmatter: `title`, `type`, `sources`, `related`, `confidence`, `summary`
- `[[wikilinks]]` — bidirectional links between pages (stored as graph edges)
- Version tracking — bumped on each recompilation

**Page types:**

| Type | Purpose | Example |
|------|---------|---------|
| `concept` | Explanation of a topic | "Machine Learning", "REST APIs" |
| `person` | Person profile | "Geoffrey Hinton", "Andrej Karpathy" |
| `project` | Project documentation | "Second Brain", "MedVista Dashboard" |
| `howto` | Step-by-step guide | "Setting up pgvector", "Docker multi-stage builds" |
| `reference` | Technical reference | "Python async patterns", "SQL window functions" |
| `index` | Auto-generated catalog | Master index of all pages |
| `log` | Append-only operation log | Compilation history |

**Compilation pipeline:**
1. Gather uncompiled or stale sources
2. Cluster by topic (LLM call, Haiku)
3. For each cluster: create or update wiki page (LLM call, Sonnet for new / Haiku for updates)
4. Parse `[[wikilinks]]` from generated markdown
5. Upsert `wiki_links` graph edges
6. Chunk + embed wiki page for RAG participation
7. Regenerate index page
8. Log to `compilation_log`

**Incremental compilation** — each source's content is SHA-256 hashed. On compilation, compare against stored hash in `wiki_sources`. Skip unchanged sources. Mark affected wiki pages stale when sources change.

### 3.3 How RAG and Wiki Complement Each Other

| Query Type | Strategy | Why |
|------------|----------|-----|
| "What is X?" (concept lookup) | Wiki-first | Return compiled page directly |
| "What did I save about X?" (recall) | Hybrid | Wiki index + embedding search on raw sources |
| "Compare X and Y" (synthesis) | Wiki-first + RAG fallback | Wiki pages for X/Y provide pre-compiled context |
| "Find the article about..." (needle) | Search-first | Embedding search over raw chunks |
| Free-form question | Hybrid | Wiki + RAG combined, LLM synthesizes |

Wiki chunks get a **1.2x RRF score boost** because they represent higher-quality pre-compiled text.

---

## 4. Data Model

### 4.1 New Tables (4)

#### `wiki_pages`

| Column | Type | Notes |
|--------|------|-------|
| `id` | `SERIAL PK` | |
| `user_id` | `INT FK(users.id)` | Default 1 |
| `slug` | `VARCHAR(255)` | UNIQUE(user_id, slug), URL-safe |
| `title` | `VARCHAR(500)` | NOT NULL |
| `page_type` | `VARCHAR(50)` | concept/person/project/howto/reference/index/log |
| `content_markdown` | `TEXT` | Full markdown body including `[[wikilinks]]` |
| `frontmatter` | `JSONB` | Karpathy-style metadata (see 4.2) |
| `confidence` | `FLOAT` | 0.0-1.0, LLM self-assessed |
| `is_published` | `BOOLEAN` | Default true |
| `is_stale` | `BOOLEAN` | Set true when sources change |
| `version` | `INT` | Bumped on recompilation |
| `compiled_at` | `TIMESTAMPTZ` | Last LLM compilation time |
| `created_at` | `TIMESTAMPTZ` | |
| `updated_at` | `TIMESTAMPTZ` | |
| `search_vector` | `TSVECTOR` | GENERATED ALWAYS from title + content |

#### `wiki_links`

| Column | Type | Notes |
|--------|------|-------|
| `id` | `SERIAL PK` | |
| `from_page_id` | `INT FK(wiki_pages.id)` | ON DELETE CASCADE |
| `to_page_id` | `INT FK(wiki_pages.id)` | ON DELETE CASCADE |
| `link_text` | `VARCHAR(255)` | Text inside `[[...]]` |
| `context_snippet` | `TEXT` | Surrounding sentence for preview |
| `created_at` | `TIMESTAMPTZ` | |

UNIQUE(from_page_id, to_page_id, link_text)

#### `wiki_sources`

| Column | Type | Notes |
|--------|------|-------|
| `id` | `SERIAL PK` | |
| `wiki_page_id` | `INT FK(wiki_pages.id)` | ON DELETE CASCADE |
| `source_type` | `VARCHAR(50)` | 'note', 'bookmark', 'pdf' only |
| `source_id` | `INT` | |
| `source_hash` | `VARCHAR(64)` | SHA-256 of source content at compile time |
| `compiled_at` | `TIMESTAMPTZ` | |

UNIQUE(wiki_page_id, source_type, source_id)

#### `compilation_log`

| Column | Type | Notes |
|--------|------|-------|
| `id` | `SERIAL PK` | |
| `user_id` | `INT FK(users.id)` | Default 1 |
| `action` | `VARCHAR(50)` | compile/recompile/merge/lint/prune |
| `status` | `VARCHAR(50)` | pending/running/success/failed |
| `sources_processed` | `INT` | |
| `pages_created` | `INT` | |
| `pages_updated` | `INT` | |
| `token_usage` | `JSONB` | {input_tokens, output_tokens, model, cost_estimate} |
| `error_message` | `TEXT` | |
| `started_at` | `TIMESTAMPTZ` | |
| `completed_at` | `TIMESTAMPTZ` | |
| `details` | `JSONB` | Arbitrary metadata per run |

### 4.2 Frontmatter Schema (JSONB)

```python
class WikiFrontmatter(BaseModel):
    title: str
    type: str                           # concept, person, project, howto, reference
    sources: list[str]                  # ["note:42", "bookmark:17", "pdf:3"]
    related: list[str]                  # ["[[Machine Learning]]", "[[Python]]"]
    tags: list[str] = []
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    created: str                        # ISO date
    last_compiled: str                  # ISO date
    summary: str                        # 1-2 sentence summary for index
```

### 4.3 New Indexes

```sql
-- Full-text search on wiki pages
CREATE INDEX idx_wiki_pages_fts ON wiki_pages USING GIN (search_vector);

-- Graph traversal
CREATE INDEX idx_wiki_links_from ON wiki_links(from_page_id);
CREATE INDEX idx_wiki_links_to ON wiki_links(to_page_id);

-- Source tracking
CREATE INDEX idx_wiki_sources_source ON wiki_sources(source_type, source_id);
CREATE INDEX idx_wiki_sources_page ON wiki_sources(wiki_page_id);

-- Stale detection
CREATE INDEX idx_wiki_pages_stale ON wiki_pages(user_id, is_stale) WHERE is_stale = TRUE;

-- Slug lookup
CREATE INDEX idx_wiki_pages_slug ON wiki_pages(user_id, slug);

-- Compilation log
CREATE INDEX idx_compilation_log_status ON compilation_log(user_id, status, started_at DESC);
```

### 4.4 Existing Code Changes

Wiki pages also participate in RAG via the existing `chunks` + `embeddings` pipeline:
- `source_type = 'wiki_page'` in `chunks` table
- Add `WHEN 'wiki_page' THEN (SELECT wp.title FROM wiki_pages wp WHERE wp.id = c.source_id)` to `rag_service.py` CASE statement
- Apply 1.2x RRF score boost for wiki-derived chunks

---

## 5. API Endpoints

### 5.1 Wiki Pages CRUD — `/api/v1/wiki/pages`

```
POST   /api/v1/wiki/pages
  Body:     {title, content_markdown, page_type?, frontmatter?}
  Response: WikiPageResponse (201)
  Notes:    Auto-generates slug. Parses [[wikilinks]], creates wiki_links rows. Chunks + embeds.

GET    /api/v1/wiki/pages
  Query:    ?type=concept&stale=false&search=term&skip=0&limit=20
  Response: {pages: WikiPageResponse[], total: int}

GET    /api/v1/wiki/pages/{slug}
  Response: WikiPageResponse (includes backlinks[] and sources[])

PUT    /api/v1/wiki/pages/{slug}
  Body:     {content_markdown?, title?, page_type?, frontmatter?}
  Response: WikiPageResponse
  Notes:    Bumps version. Re-parses wikilinks. Re-embeds.

DELETE /api/v1/wiki/pages/{slug}
  Response: 204
  Notes:    Cascades to wiki_links, wiki_sources, chunks, embeddings.
```

### 5.2 Compilation — `/api/v1/wiki/compile`

```
POST   /api/v1/wiki/compile
  Body:     {source_ids?: [{type, id}], force?: bool, model?: "haiku"|"sonnet"}
  Response: {log_id: int, status: "pending"} (202 Accepted)
  Notes:    Background task via FastAPI BackgroundTasks. If source_ids omitted,
            compiles all uncompiled sources. force=true recompiles even if hashes match.

GET    /api/v1/wiki/compile/{log_id}
  Response: CompilationLogResponse
  Notes:    Poll for compilation status.

GET    /api/v1/wiki/compile/history
  Query:    ?limit=20&status=success
  Response: CompilationLogResponse[]
```

### 5.3 Graph — `/api/v1/wiki/graph`

```
GET    /api/v1/wiki/graph
  Query:    ?center_slug=machine-learning&depth=2
  Response: {
    nodes: [{id, slug, title, type, link_count}],
    edges: [{source, target, label}]
  }
  Notes:    Recursive CTE for depth-limited subgraph. Full graph if no center_slug.
```

### 5.4 Lint / Health Check — `/api/v1/wiki/lint`

```
POST   /api/v1/wiki/lint
  Response: {
    orphan_pages: [{slug, title}],
    broken_links: [{from_slug, link_text}],
    stale_pages: [{slug, title, stale_since}],
    low_confidence: [{slug, title, confidence}],
    stats: {total_pages, total_links, avg_confidence, uncompiled_sources}
  }
```

### 5.5 Wiki-Aware Query — `/api/v1/wiki/query`

```
POST   /api/v1/wiki/query
  Body:     {query: str, mode?: "wiki_first"|"search_first"|"hybrid"}
  Response: {
    answer: str,
    wiki_pages: [{slug, title, relevance}],
    search_sources: [{source_type, source_id, score}],
    strategy_used: str
  }
  Notes:    wiki_first checks index for matching page first, falls back to RAG.
```

### 5.6 Export — `/api/v1/wiki/export`

```
GET    /api/v1/wiki/export
  Response: application/zip
  Notes:    All wiki pages as .md files with YAML frontmatter + [[wikilinks]].
            Obsidian-compatible vault structure.
```

### 5.7 Pydantic Schemas (new in schemas.py)

```python
# Wiki pages
class WikiPageCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    content_markdown: str = Field(min_length=1)
    page_type: str = Field(default="concept",
        pattern=r"^(concept|person|project|howto|reference|index|log)$")
    frontmatter: dict = Field(default_factory=dict)

class WikiPageUpdate(BaseModel):
    title: str | None = None
    content_markdown: str | None = None
    page_type: str | None = None
    frontmatter: dict | None = None

class WikiPageResponse(BaseModel):
    id: int
    slug: str
    title: str
    page_type: str
    content_markdown: str
    frontmatter: dict
    confidence: float
    is_stale: bool
    version: int
    compiled_at: datetime
    created_at: datetime
    updated_at: datetime
    backlinks: list[WikiLinkRef] = Field(default_factory=list)
    sources: list[WikiSourceRef] = Field(default_factory=list)
    model_config = {"from_attributes": True}

class WikiLinkRef(BaseModel):
    slug: str
    title: str
    direction: str  # "outgoing" or "incoming"

class WikiSourceRef(BaseModel):
    source_type: str
    source_id: int
    compiled_at: datetime

class WikiPageListResponse(BaseModel):
    pages: list[WikiPageResponse]
    total: int

# Compilation
class CompileRequest(BaseModel):
    source_ids: list[dict] | None = None
    force: bool = False
    model: str = Field(default="haiku", pattern=r"^(haiku|sonnet)$")

class CompilationLogResponse(BaseModel):
    id: int
    action: str
    status: str
    sources_processed: int
    pages_created: int
    pages_updated: int
    token_usage: dict
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None

# Graph
class GraphNode(BaseModel):
    id: int
    slug: str
    title: str
    type: str
    link_count: int

class GraphEdge(BaseModel):
    source: int
    target: int
    label: str

class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]

# Lint
class LintResponse(BaseModel):
    orphan_pages: list[dict]
    broken_links: list[dict]
    stale_pages: list[dict]
    low_confidence: list[dict]
    stats: dict

# Wiki query
class WikiQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    mode: str = Field(default="wiki_first",
        pattern=r"^(wiki_first|search_first|hybrid)$")

class WikiQueryResponse(BaseModel):
    answer: str
    wiki_pages: list[dict]
    search_sources: list[dict]
    strategy_used: str
    usage: dict = Field(default_factory=dict)
```

---

## 6. Backend Services

### 6.1 Wiki Compilation Service (`wiki_compilation_service.py`)

Core pipeline:

```
compile_sources(db, user_id, source_ids?, force?)
  ├── gather_uncompiled_sources(db, user_id)
  ├── cluster_by_topic(sources) ← Haiku call (titles + 200-char snippets)
  ├── for each topic cluster:
  │     ├── check_existing_wiki_page(db, topic)
  │     ├── if exists + not stale: merge_into_page(db, page, new_sources) ← Haiku
  │     ├── if not exists: create_wiki_page(db, sources) ← Sonnet
  │     ├── parse_wikilinks(page.content_markdown)
  │     ├── upsert_wiki_links(db, page, wikilinks)
  │     ├── upsert_wiki_sources(db, page, sources, content_hashes)
  │     └── chunk_and_embed(db, page) ← existing pipeline
  ├── regenerate_index_page(db, user_id)
  └── create_compilation_log(db, results)
```

**LLM compilation prompt:**
```
System: You are a wiki compiler for a personal knowledge base. Read the source
materials and create a structured wiki page in Markdown format.

RULES:
1. Use [[Double Bracket Links]] to reference related concepts
2. Start with YAML frontmatter (title, type, sources, related, confidence)
3. Write in clear, concise encyclopedic style
4. Preserve factual claims from sources exactly
5. Set confidence: 0.9+ if sources agree, 0.5-0.8 if extrapolating, <0.5 if uncertain
6. Include a 1-2 sentence summary at the top

EXISTING WIKI PAGES (for linking):
{list of existing page titles}

SOURCE MATERIALS:
{source content}
```

**Token management:**
- Budget: 8000 tokens per source batch (configurable)
- If total exceeds budget: summarize longest sources first (Haiku pre-pass)
- Max 5 sources per compilation call
- Cost tracking in `compilation_log.token_usage`

**Helper functions:**

```python
def slugify(title: str) -> str:
    """'Machine Learning Basics' -> 'machine-learning-basics'"""

def content_hash(text: str) -> str:
    """SHA-256 of source content for change detection."""

def extract_wikilinks(markdown: str) -> list[str]:
    """Extract all [[wikilink]] targets from markdown. Regex: r'\\[\\[([^\\]]+)\\]\\]'"""
```

### 6.2 Wiki Maintenance Service (`wiki_maintenance_service.py`)

```python
async def lint_wiki(db, user_id) -> LintResponse:
    """Detect: orphan pages (no inbound links), broken links (target doesn't exist),
    stale pages (source changed), low confidence (<0.5). Return stats."""

async def regenerate_index(db, user_id):
    """Rebuild the _index page: list all pages grouped by type with summaries."""
```

### 6.3 Modified Existing Services

**`rag_service.py`:**
- Add `wiki_page` CASE branch in both semantic and FTS queries
- Apply `WIKI_BOOST = 1.2` multiplier to RRF scores for wiki-sourced chunks

**`notes.py` API handler (PUT):**
- After updating a note, run: `UPDATE wiki_pages SET is_stale = TRUE WHERE id IN (SELECT wiki_page_id FROM wiki_sources WHERE source_type = 'note' AND source_id = :note_id)`

**`bookmarks.py` API handler (PUT):**
- Same staleness propagation for bookmarks

### 6.4 Config Additions (`config.py`)

```python
# Wiki compilation
wiki_compile_model: str = "haiku"
wiki_compile_max_sources: int = 5
wiki_compile_max_tokens: int = 8000
wiki_boost_factor: float = 1.2
wiki_auto_compile: bool = False
```

---

## 7. Frontend

### 7.1 New Pages

| Route | Page | Description |
|-------|------|-------------|
| `/wiki` | WikiListPage | Grid of wiki page cards with type filter + search |
| `/wiki/[slug]` | WikiArticlePage | Rendered markdown, clickable wikilinks, backlinks section, source references |
| `/graph` | GraphPage | Force-directed graph (react-force-graph-2d), type-colored nodes, click-to-navigate |
| `/compilation` | CompilationPage | Status card, trigger button, log list, health check panel |

### 7.2 New Components

**Graph (5):**
- `ForceGraph` — wraps react-force-graph-2d, dynamic import (ssr: false), node coloring by type, click → `/wiki/{slug}`
- `GraphToolbar` — type filter buttons, search input, reset zoom
- `GraphTooltip` — hover tooltip with title + type badge + link count
- `MobileGraphFallback` — searchable list for viewports < 768px
- `GraphSkeleton` — loading state

**Wiki (7):**
- `WikiPageCard` — card with title, type badge, confidence dot, date, link count
- `WikiFrontmatter` — horizontal metadata bar (type, confidence, dates, source count)
- `WikiMarkdownRenderer` — react-markdown + remark-gfm, converts `[[wikilinks]]` to `<Link>` components
- `WikiBacklinks` — "Pages that link here" section
- `WikiSourceReferences` — original sources (notes/bookmarks/PDFs) that compiled into this page
- `WikiPageSkeleton` — loading state
- `ObsidianExportButton` — client-side zip generation (jszip + file-saver)

**Compilation (5):**
- `CompilationStatusCard` — last run, pages compiled, pending count, running indicator
- `CompilationActions` — "Run Compilation" button, disables while running
- `CompilationLog` — scrollable list of operations with action badges
- `HealthCheckPanel` — collapsible sections for orphans, broken links, stale claims
- `CompilationSkeleton` — loading state

**Shared (1):**
- `Pagination` — extracted from notes page, reusable for bookmarks + wiki

### 7.3 API Client Additions (`lib/api.ts`)

New types: `WikiPage`, `WikiGraphData`, `WikiGraphNode`, `WikiGraphLink`, `CompilationStatus`, `CompilationLogEntry`, `HealthCheckResult`

New functions: `fetchWikiPages()`, `fetchWikiPage(slug)`, `fetchWikiGraph()`, `fetchCompilationStatus()`, `triggerCompilation()`, `fetchCompilationLog()`, `fetchHealthCheck()`, `exportWiki()`

### 7.4 State Management (`lib/store.ts`)

New Zustand slice:
```typescript
graphFilter: string | null          // type filter for graph nodes
graphSearchQuery: string            // search within graph
highlightedNodeId: string | null    // hover/search highlight
compilationPolling: boolean         // SWR refreshInterval toggle
```

### 7.5 New Dependencies

```
react-force-graph-2d    # ~40KB, canvas-based graph
react-markdown          # markdown rendering for wiki
remark-gfm              # GFM tables, checkboxes
rehype-raw              # raw HTML in markdown
jszip                   # client-side zip for export
file-saver              # browser download trigger
```

### 7.6 Sidebar Updates

Add three nav items to `Sidebar.tsx`:
- Wiki (BookOpen icon) → `/wiki`
- Knowledge Graph (GitBranch icon) → `/graph`
- Compilation (Cog icon) → `/compilation`

### 7.7 Wikilink Rendering

Convert `[[Page Name]]` to Next.js `<Link>` before markdown rendering:
```typescript
function processWikilinks(markdown: string): string {
  return markdown.replace(/\[\[([^\]]+)\]\]/g, (_, title) => {
    const slug = title.toLowerCase().replace(/\s+/g, "-").replace(/[^\w-]/g, "");
    return `[${title}](/wiki/${slug})`;
  });
}
```

### 7.8 Graph Node Colors

| Type | Color |
|------|-------|
| concept | `hsl(210, 70%, 55%)` — blue |
| person | `hsl(150, 60%, 45%)` — green |
| project | `hsl(30, 80%, 55%)` — orange |
| howto | `hsl(280, 60%, 55%)` — purple |
| reference | `hsl(0, 70%, 55%)` — red |

Node size proportional to `link_count`.

### 7.9 MVP Improvements (bundled)

- Extract `Pagination` from notes page → reusable component
- Add pagination to bookmarks page (backend already supports it)
- Add tag filtering to bookmarks page

---

## 8. Project Structure (new/modified files)

```
backend/
  app/
    api/
      wiki.py                        # NEW — wiki router (all endpoints)
    services/
      wiki_compilation_service.py    # NEW — LLM compilation pipeline
      wiki_maintenance_service.py    # NEW — lint + maintenance
      rag_service.py                 # MODIFY — add wiki_page source type + boost
    models.py                        # MODIFY — add 4 new models
    schemas.py                       # MODIFY — add wiki Pydantic schemas
    config.py                        # MODIFY — add wiki settings
    main.py                          # MODIFY — register wiki router
  migrations/
    schema.sql                       # MODIFY — add 4 tables + indexes
  tests/
    conftest.py                      # MODIFY — SQLite adapters for new types
    test_api_wiki.py                 # NEW
    test_wiki_compilation.py         # NEW
    test_wiki_maintenance.py         # NEW

frontend/
  app/
    wiki/
      page.tsx                       # NEW — wiki list
      [slug]/page.tsx                # NEW — wiki article
    graph/page.tsx                   # NEW — knowledge graph
    compilation/page.tsx             # NEW — compilation dashboard
  components/
    graph/
      ForceGraph.tsx                 # NEW
      GraphToolbar.tsx               # NEW
      GraphTooltip.tsx               # NEW
      MobileGraphFallback.tsx        # NEW
    wiki/
      WikiPageCard.tsx               # NEW
      WikiFrontmatter.tsx            # NEW
      WikiMarkdownRenderer.tsx       # NEW
      WikiBacklinks.tsx              # NEW
      WikiSourceReferences.tsx       # NEW
      ObsidianExportButton.tsx       # NEW
    compilation/
      CompilationStatusCard.tsx      # NEW
      CompilationActions.tsx         # NEW
      CompilationLog.tsx             # NEW
      HealthCheckPanel.tsx           # NEW
    Pagination.tsx                   # NEW (extracted from notes)
    Sidebar.tsx                      # MODIFY — add nav items
  lib/
    api.ts                           # MODIFY — wiki types + functions
    store.ts                         # MODIFY — wiki state slice
    hooks/useMediaQuery.ts           # NEW
  __tests__/
    wiki-api.test.ts                 # NEW
    wikilinks.test.ts                # NEW
```

---

## 9. Commands

### Development

```bash
# Backend (unchanged)
cd backend && uv run uvicorn app.main:app --reload --port 8110
cd backend && uv run pytest
cd backend && uv run pytest tests/test_api_wiki.py -v
cd backend && uv run ruff check app/

# Frontend (unchanged)
cd frontend && npm run dev -- -p 3110
cd frontend && npx vitest
cd frontend && npm run build

# Docker (unchanged)
docker compose up -d
docker compose build
docker compose logs -f backend
```

### Wiki-specific

```bash
# Trigger compilation via API
curl -X POST http://localhost:8110/api/v1/wiki/compile \
  -H "Content-Type: application/json" \
  -d '{"model": "haiku"}'

# Check compilation status
curl http://localhost:8110/api/v1/wiki/compile/{log_id}

# Run lint
curl -X POST http://localhost:8110/api/v1/wiki/lint

# Get graph data
curl http://localhost:8110/api/v1/wiki/graph

# Export Obsidian vault
curl http://localhost:8110/api/v1/wiki/export -o wiki.zip
```

---

## 10. Testing Strategy

### Backend (TDD — RED then GREEN)

| Test File | Coverage | Test Count (est.) |
|-----------|----------|-------------------|
| `test_api_wiki.py` | CRUD endpoints, slug generation, wikilink parsing, backlinks | ~12 |
| `test_wiki_compilation.py` | Compilation pipeline (mocked LLM), incremental detection, index regen | ~10 |
| `test_wiki_maintenance.py` | Lint (orphans, broken links, stale), stats | ~8 |

**Total new backend tests: ~30**

Mocking strategy:
- Mock `llm_service.generate_answer` for compilation tests (no real API calls)
- Mock `embedding_service.embed_single` and `embed_batch` (no real API calls)
- Use SQLite in-memory with `@compiles` adapters (existing pattern)

### Frontend

| Test File | Coverage | Test Count (est.) |
|-----------|----------|-------------------|
| `wiki-api.test.ts` | Wiki API functions, types | ~6 |
| `wikilinks.test.ts` | Wikilink regex, slug generation | ~5 |
| `pagination.test.ts` | Pagination component props | ~4 |

**Total new frontend tests: ~15**

### Integration

- Docker Compose build + start all services
- Create note via API → trigger compilation → verify wiki page created
- Graph endpoint returns valid nodes + edges
- Export endpoint returns valid zip with `.md` files

---

## 11. Code Style

### Python (same as v1)

- Python 3.12+, async/await throughout
- Type hints on all function signatures
- Pydantic 2.0 models with `model_config = {"from_attributes": True}`
- SQLAlchemy 2.0 style (`mapped_column`, `DeclarativeBase`)
- Linting: ruff

### TypeScript (same as v1)

- TypeScript strict mode
- `"use client"` only for interactive pages
- SWR for data fetching, Zustand for state
- TailwindCSS + shadcn/ui
- Dynamic imports for heavy client libs (react-force-graph-2d)

---

## 12. Boundaries

### Always Do

- TDD: write failing test before implementation
- Docker: verify all images build and services start after each slice
- Incremental: only chunk/embed/compile what changed
- Track costs: log token usage in `compilation_log.token_usage`
- Preserve existing tests: all 44 backend + 17 frontend tests must keep passing

### Ask First About

- Changing existing API response shapes (could break frontend)
- Adding new Docker services or ports
- Modifying the Telegram bot

### Never Do

- Replace RAG with wiki (they complement each other)
- Add Celery/Redis for background jobs (FastAPI BackgroundTasks suffices)
- Add a separate graph database (PostgreSQL handles it)
- Make real API calls in tests (mock LLM + embedding services)
- Allow wiki pages as compilation sources (prevents circular compilation)
- Ship to production (local Docker testing only for now)

---

## 13. Implementation Order

10 vertical TDD slices, each: RED test → implement → GREEN → commit.

| Slice | Scope | Dependencies |
|-------|-------|-------------|
| 1 | Database tables + SQLAlchemy models + Pydantic schemas | None |
| 2 | Wiki CRUD API + slug gen + wikilink parsing | Slice 1 |
| 3 | Source tracking + staleness propagation | Slices 1-2 |
| 4 | Compilation service (LLM pipeline) | Slices 1-3 |
| 5 | Graph API + lint/health check | Slices 1-2 |
| 6 | Wiki-aware search (RAG integration) | Slices 1-4 |
| 7 | Frontend: wiki browser | Slices 1-2 |
| 8 | Frontend: knowledge graph | Slices 1-2, 5 |
| 9 | Frontend: compilation dashboard | Slices 1-2, 4 |
| 10 | Frontend: Obsidian export + MVP fixes | Slices 1-2 |

---

## 14. Workflow Skills Per Phase

| Phase | Primary Skill | Also Invoke |
|-------|---------------|-------------|
| `/spec` (this phase) | `spec-driven-development` | `api-and-interface-design`, `idea-refine` |
| `/plan` | `planning-and-task-breakdown` | `incremental-implementation`, `test-driven-development` |
| `/build` (per slice) | `incremental-implementation` | `test-driven-development`, `source-driven-development`, `api-and-interface-design` (backend), `frontend-ui-engineering` (frontend) |
| `/test` | `test-driven-development` | `browser-testing-with-devtools`, `debugging-and-error-recovery` |
| `/review` | `code-review-and-quality` | `security-and-hardening`, `performance-optimization`, `code-simplification` |

---

## Next Step

After this spec is approved, run:

```
/plan Break SPEC.md into 10 implementation slices as defined in the spec (Section 13). Each slice is a vertical TDD slice: write RED test first, implement to GREEN, commit. Start with Slice 1 (database tables + models).
```
