# Key Architectural Decisions

## 1. HNSW Index (not IVFFLAT)

**Why:** Better recall out-of-box, handles dynamic inserts without REINDEX, negligible latency difference for <100K vectors.

```sql
CREATE INDEX idx_embedding ON embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

## 2. Hybrid Search with RRF (k=60)

**Why:** Achieves ~84% retrieval precision vs ~62% for vector-only. Hybrid captures both semantic understanding and exact keyword matches.

**Implementation:** Over-fetch 20 from pgvector + 20 from tsvector, merge with `UNION ALL`, deduplicate, select top 10 after RRF scoring.

## 3. Chunking: 400-500 tokens, 50-token overlap

**Why:** 256-512 tokens is the research consensus sweet spot. Sentence-boundary splitting with RecursiveCharacterTextSplitter achieves 85-90% recall.

**Token counting:** tiktoken with `cl100k_base` (exact counts, used by text-embedding-3-small).

## 4. PDF Extraction: pdfplumber (MIT licensed)

**Why:** Good text quality, excellent table handling, actively maintained. PyMuPDF is faster but AGPL-licensed (risky for web-served apps).

**OCR fallback:** pytesseract + pdf2image available as optional extras.

## 5. URL Scraping: trafilatura with Markdown output

**Why:** Highest F1 score (0.958) among open-source extractors. Apache 2.0 licensed. Outputs Markdown directly (perfect for storage).

## 6. Embedding Model: text-embedding-3-small

**Why:** Best value ($0.02/1M tokens, 1536 dims, MTEB 62.3). ~$1.20 total for 100K documents.

## 7. LLM Strategy: Haiku by default, Sonnet toggle

**Why:** Haiku is cheap (~$0.005/query) and fast (1-3s). Sonnet ($0.015/query, 2-5s) available per-query toggle for complex reasoning.

## 8. Single-user hardcoded (user_id=1)

**Why:** Simplifies auth and queries. Schema supports multi-user migration if needed in future.

## 9. Tag-based organization (no folders/hierarchy)

**Why:** Flat, flexible, avoids nesting paradoxes. Each content item (note/bookmark/PDF) can have multiple tags.

## 10. Telegram: HTML parse mode (not MarkdownV2)

**Why:** MarkdownV2 requires escaping 20+ characters. HTML is simpler and sufficient.

## 11. Telegram Webhook: Dedicated subdomain

**Why:** `telegram.brain.armandointeligencia.com` behind Traefik. Cleaner than path-based routing, avoids conflicts with FastAPI routes.

## 12. Frontend: SWR + use-debounce (300ms)

**Why:** SWR is 4KB (vs TanStack Query 13KB). Debounce prevents excessive API calls during typing.

## 13. Markdown Editor: @uiw/react-md-editor

**Why:** 4.6KB gzip (vs TipTap 311KB, MDXEditor 851KB). Split-pane, native markdown I/O out-of-box.

## 14. Skip PDF viewer for MVP

**Why:** Extract text + download link sufficient. react-pdf adds 500KB. Can add later if needed.

## Deployment Decisions

- **Docker Compose:** All services containerized for consistency
- **Traefik:** Reverse proxy + SSL termination + service discovery
- **PostgreSQL:** Single instance (shared across projects), database per project
- **Redis:** Single instance (shared across projects), DB#9 reserved for Second Brain
- **Environment-based config:** Development (polling) vs Production (webhook)

## Trade-offs Made

| Decision | Benefit | Trade-off |
|----------|---------|-----------|
| HNSW over IVFFLAT | Better recall, simpler ops | Slightly larger index size |
| Hybrid search | Higher precision | +~50ms query latency |
| Single-user hardcoded | Simpler code | Migration cost later if needed |
| SWR over TanStack Query | Smaller bundle | Fewer advanced features |
| Telegram webhook | Production-ready | Requires SSL + subdomain |
| Haiku by default | Cost efficient | Sometimes needs Sonnet toggle |
