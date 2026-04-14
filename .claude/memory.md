# Second Brain — Persistent Memory

> Last updated: 2026-04-02
> This file contains all architectural decisions, research findings, gotchas, and conventions for the Second Brain project.
> Future Claude Code sessions should read this file first to regain full context.

---

## Project Status: MVP COMPLETE

The full MVP is implemented, tested, and verified running via Docker Compose.
- **Backend:** 44/44 pytest tests pass
- **Frontend:** 17/17 vitest tests pass, Next.js build succeeds
- **Docker:** All 3 images build, all services start and respond
- **Next phase:** Add API keys to .env, deploy to VPS, polish UI

---

## Architectural Decisions

### [Architect] Vector Index: HNSW over IVFFLAT
**Decision:** Use HNSW index instead of IVFFLAT as originally planned in PLAN.md.
**Why:** HNSW provides better recall out-of-the-box without parameter tuning, handles dynamic inserts without periodic REINDEX (critical since notes/bookmarks are added continuously), and at <100K vectors the build time difference is negligible (29s vs 5s). Query latency is comparable (2-6ms HNSW vs 2-10ms IVFFLAT).
**Parameters:** `m=16, ef_construction=64` (defaults, sufficient for <100K vectors).
```sql
CREATE INDEX idx_embedding ON embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

### [Architect] Cosine Distance Confirmed
**Decision:** Use cosine distance (`<=>`) with `vector_cosine_ops` for pgvector.
**Why:** OpenAI text-embedding-3-small returns normalized embeddings, so cosine and inner product produce identical rankings. Cosine is the ecosystem standard and avoids the negation confusion of inner product in pgvector.
**Critical:** The distance operator in queries MUST match the operator class in the index. Mismatched operators cause silent fallback to sequential scan (5ms → 30s+).

### [Architect] Hybrid Search with RRF (k=60)
**Decision:** Combine pgvector semantic search with PostgreSQL tsvector full-text search using Reciprocal Rank Fusion.
**Why:** Benchmarks show hybrid search achieves ~84% retrieval precision vs ~62% for vector-only. Exact-match queries (error codes, specific terms) are often missed by vector-only search.
**Implementation:** Over-fetch 20 results from each method, merge with `UNION ALL`, deduplicate with `GROUP BY`, select top 10 after RRF scoring. Use `GENERATED ALWAYS AS` for the tsvector column to auto-sync.
**Expected latency:** <20ms for hybrid search on <100K chunks.

### [Architect] Chunking: 400-500 tokens, 50 overlap, RecursiveCharacterTextSplitter
**Decision:** Use sentence-boundary splitting with token accumulation (custom implementation in `chunking_service.py`).
**Why:** Research shows 256-512 tokens is the sweet spot. 400-500 tokens balances context preservation with retrieval precision. Semantic chunking offers only ~9% improvement at much higher cost.
**Token counting:** Use tiktoken with `cl100k_base` encoding (exact counts, Rust-backed, fast). Replaced the `len(text)/4` estimate from PLAN.md.

### [Architect] PDF Extraction: pdfplumber (primary)
**Decision:** Use pdfplumber (MIT license) for PDF text extraction.
**Why:** Good text quality, excellent table extraction, actively maintained. PyMuPDF/pymupdf4llm is technically superior (faster, outputs Markdown, auto-OCR) but is AGPL-licensed — risky for a web-served application.
**OCR fallback:** If `len(extracted_text.strip()) < 50`, log warning. pytesseract + pdf2image available as optional extras (`uv sync --extra ocr`).

### [Architect] URL Scraping: trafilatura (primary)
**Decision:** Use trafilatura as the primary article extractor with Markdown output.
**Why:** Highest F1 score among open-source extractors (0.958). Outputs Markdown directly (perfect for storage format). Apache 2.0 licensed. No browser/JS rendering needed for MVP.
**Fallback chain:** trafilatura → readability-lxml fallback built into trafilatura's `no_fallback=False` mode.

### [Architect] Markdown: Store Raw Only, Render on Frontend
**Decision:** Store raw markdown in TEXT column, render on frontend with react-markdown.
**Why:** Single source of truth, directly searchable via full-text search, trivially exportable.

### [Architect] Telegram Bot: python-telegram-bot v22.x
**Decision:** Use python-telegram-bot v22.7 (not 20.5+ as in PLAN.md).
**Why:** Latest stable, supports Bot API 9.5, fully async. Key patterns:
- `filters.User(user_id=ALLOWED_USER_ID)` for single-user access control
- HTML parse mode (not MarkdownV2 — too many characters to escape in note content)
- Auto-detect URLs via `MessageHandler(filters.Entity("url"), auto_bookmark)`
- Edit messages in-place for button actions
- Dual mode: polling for dev, webhook for production via `ENVIRONMENT` env var

### [Architect] Telegram Webhook: Dedicated Subdomain
**Decision:** Use `telegram.brain.armandointeligencia.com` subdomain behind Traefik.
**Why:** Cleaner than path-based routing, avoids conflicts with FastAPI routes.

### [Architect] Frontend Search: SWR + use-debounce
**Decision:** SWR for data fetching, use-debounce (300ms) for search input.
**Why:** SWR is 4KB (vs TanStack Query 13KB), sufficient for this project's data patterns.

### [Architect] Markdown Editor: @uiw/react-md-editor
**Decision:** Use @uiw/react-md-editor for the note editor.
**Why:** 4.6KB gzip (vs TipTap 311KB, MDXEditor 851KB). Split-pane, native markdown I/O.

### [Architect] PDF Viewer: Skip for MVP
**Decision:** No in-browser PDF viewer for MVP. Show extracted text preview + download link.

### [Architect] Embedding Model: text-embedding-3-small
**Decision:** Use OpenAI text-embedding-3-small (1536 dimensions, $0.02/1M tokens).
**Why:** Best value. ~$1.20 total for 100K documents.

### [Architect] RAG Prompt: Structured Citation with Source IDs
**Decision:** Assign each chunk a `[Source N]` identifier in the prompt, instruct LLM to cite by identifier. Similarity threshold of 0.3 for "insufficient context" detection.

---

## Key Changes from Original PLAN.md

1. **IVFFLAT → HNSW** index for pgvector (better recall, handles dynamic inserts)
2. **python-telegram-bot 20.5+ → 22.7** (latest stable, Bot API 9.5)
3. **Token counting: len(text)/4 → tiktoken cl100k_base** (exact counts)
4. **Telegram parse mode: MarkdownV2 → HTML** (less escaping issues)
5. **Add tsvector GENERATED ALWAYS column** to chunks table (auto-sync)
6. **Add telegram subdomain** for webhook: telegram.brain.armandointeligencia.com
7. **Skip PDF viewer for MVP** — show extracted text + download link
8. **Markdown editor: @uiw/react-md-editor** (4.6KB vs TipTap 311KB)
9. **Docker postgres port: 5432 → configurable** via `DB_PORT` env var (5432 often in use locally)

---

## Gotchas & Lessons Learned

### pgvector Index/Operator Mismatch
If the index uses `vector_cosine_ops` but the query uses `<->` (L2 distance), PostgreSQL silently falls back to sequential scan with no error. Always verify the distance operator matches the index operator class.

### Telegram MarkdownV2 Escaping
MarkdownV2 requires escaping 20+ special characters. Since note/bookmark content naturally contains these characters, use HTML parse mode instead.

### Telegram callback_data Limit
InlineKeyboardButton callback_data is limited to 64 bytes. Use short prefixes like `tag:123`, `page:2`, `sonnet:456`.

### Telegram Typing Indicator
The typing indicator lasts only 5 seconds. For long operations (RAG search + LLM), resend it every 4 seconds via asyncio.create_task.

### PyMuPDF AGPL License
PyMuPDF/pymupdf4llm is AGPL-3.0. If serving over a network, AGPL requires open-sourcing the entire application. Use pdfplumber (MIT) to avoid this.

### tsvector Auto-Sync
Use `GENERATED ALWAYS AS (to_tsvector('english', content)) STORED` instead of triggers for automatic tsvector updates.

### SQLite Tests for PostgreSQL-specific Types
Backend tests use SQLite (in-memory) for speed. PostgreSQL-specific types (JSONB, TSVECTOR, Vector) are handled via SQLAlchemy `@compiles` decorators in `tests/conftest.py`:
```python
@compiles(JSONB, "sqlite") → "JSON"
@compiles(TSVECTOR, "sqlite") → "TEXT"
@compiles(Vector, "sqlite") → "TEXT"
```

### Mock Patching Location
When mocking imported functions in tests, patch at the **import location** (where used), not the **definition location** (where defined). Example:
- `scrape_url` defined in `app.services.scraping_service`
- Imported in `app.api.bookmarks`
- Must patch `app.api.bookmarks.scrape_url` (not `app.services.scraping_service.scrape_url`)

### SQLAlchemy onupdate with Async SQLite
`onupdate=func.now()` on mapped columns can cause `MissingGreenlet` errors with async SQLite. Set `updated_at` explicitly in update handlers instead:
```python
note.updated_at = datetime.now(timezone.utc)
```

### next-themes Import Path
`next-themes` v0.4+ exports `ThemeProviderProps` from the main package, not from `next-themes/dist/types`. Use:
```typescript
import { ThemeProvider, type ThemeProviderProps } from "next-themes";
```

### react-highlight-words Missing Types
No `@types/react-highlight-words` package exists. Add a `types.d.ts` file in the frontend root with `declare module "react-highlight-words"`.

### vitest.config.ts and Next.js Build
The vitest config file can cause TypeScript errors during `next build` due to vite/vitest type conflicts. Exclude it from the tsconfig: `"exclude": ["node_modules", "vitest.config.ts", "__tests__"]`.

---

## Performance Expectations

| Operation | Expected Latency |
|-----------|-----------------|
| pgvector HNSW query (<100K vectors) | 2-20ms |
| PostgreSQL full-text search | ~7ms |
| Combined hybrid search | <20ms |
| OpenAI embedding API call | 100-500ms |
| Claude Haiku response | 1-3s |
| Claude Sonnet response | 2-5s |
| Total RAG search (hybrid + LLM) | <4s |
| Telegram bot response target | <2s (simple), <5s (RAG) |

## Cost Estimates

| Resource | Estimated Cost |
|----------|---------------|
| text-embedding-3-small (100K docs) | ~$1.20 total |
| Claude Haiku per query (~5K input tokens) | ~$0.005 |
| Claude Sonnet per query (~5K input tokens) | ~$0.015 |
| Monthly usage (50 queries/day) | ~$8-15/month |

---

## User Preferences

- Armando uses `uv` for Python, `npm` for Node.js
- Project uses port convention: frontend=3110, backend=8110, telegram=8111
- PostgreSQL shared instance, database name `second_brain_db`
- Redis DB #9 allocated for this project
- Deploy to Hostinger VPS (2 vCPU, 8GB RAM) behind Traefik
- Production domains: brain.armandointeligencia.com, api.brain.armandointeligencia.com, telegram.brain.armandointeligencia.com
