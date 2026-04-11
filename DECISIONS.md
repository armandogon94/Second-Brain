# DECISIONS.md — Second Brain v2 Design Decisions

> Date: 2026-04-11
> Context: Autonomous design decisions made during planning for the LLM Wiki integration.
> These were made without user input per request ("I don't currently have time to answer open questions").

---

## D1: Combine RAG + Wiki (Don't Replace RAG)

**Decision:** Keep the existing pgvector RAG pipeline. Add the wiki layer on top as a complementary system.

**Alternatives considered:**
- (a) Replace RAG entirely with wiki (Karpathy's pure approach for small collections)
- (b) Keep RAG only, add wiki metadata as tags
- **(c) Hybrid: wiki-first queries fall back to RAG** (chosen)

**Why (c):** RAG and wiki solve different query types. "What is X?" is best answered by a pre-compiled wiki page. "Find the article where I mentioned Y" is best answered by embedding search over raw chunks. At personal scale (<100K docs), both systems are cheap to maintain. Removing RAG would lose fuzzy semantic search. Removing wiki would lose structured knowledge compilation.

**Impact:** The `/wiki/query` endpoint accepts a `mode` parameter (`wiki_first`, `search_first`, `hybrid`). Default is `wiki_first`. No existing functionality is removed.

---

## D2: PostgreSQL for Graph Storage (No Separate Graph DB)

**Decision:** Store the wikilink graph (nodes = wiki pages, edges = `[[wikilinks]]`) in PostgreSQL using a `wiki_links` junction table with recursive CTEs for traversal.

**Alternatives considered:**
- (a) Neo4j (dedicated graph DB)
- (b) Memgraph (in-memory graph)
- **(c) PostgreSQL with wiki_links table + recursive CTE** (chosen)
- (d) In-memory graph computed from markdown on each request

**Why (c):** The graph will have <10K nodes at personal scale. PostgreSQL handles this trivially with indexed foreign keys. A recursive CTE with depth limit provides efficient subgraph traversal. Adding Neo4j or Memgraph doubles the Docker infrastructure for a graph that fits in a single table. This aligns with the existing "no separate vector DB" decision (pgvector over Pinecone/Weaviate).

**Trade-off:** No native graph algorithms (shortest path, community detection). If needed later, can add pg_graph extension or export to NetworkX for analysis.

---

## D3: JSONB Frontmatter (Not Normalized Columns)

**Decision:** Store Karpathy-style YAML frontmatter as a JSONB column on `wiki_pages`, not as normalized relational columns.

**Alternatives considered:**
- (a) Separate columns for each frontmatter field (title, type, sources, related, confidence, etc.)
- **(b) Single JSONB column** (chosen)
- (c) Separate `wiki_metadata` table

**Why (b):** Frontmatter is always read and written as a unit. It maps directly to YAML for Obsidian export. Schema can evolve (add new fields) without migrations. JSONB supports GIN indexing for queries if needed. The key fields that need indexed access (slug, page_type, confidence, is_stale) are stored as dedicated columns anyway.

**Trade-off:** Can't enforce foreign keys on `sources` list inside JSONB. Validation happens at the Pydantic schema layer (`WikiFrontmatter` model).

---

## D4: FastAPI BackgroundTasks (Not Celery/Redis)

**Decision:** Run wiki compilation as a FastAPI `BackgroundTask`, tracking status in the `compilation_log` table.

**Alternatives considered:**
- (a) Celery + Redis broker
- (b) arq (async Redis queue)
- **(c) FastAPI BackgroundTasks + DB status tracking** (chosen)
- (d) asyncio.create_task (no status tracking)

**Why (c):** This is a single-user system. There's never more than one compilation running at a time. FastAPI BackgroundTasks provide fire-and-forget execution with zero infrastructure. Status tracking goes in the `compilation_log` table, which doubles as the Karpathy `log.md` equivalent. If the system ever needs queuing (multi-user, large batch), Redis (already allocated at DB #9) can be added with arq.

**Trade-off:** If the FastAPI process crashes during compilation, the background task is lost. Mitigation: the `compilation_log` entry stays in `status='running'` and can be detected on restart.

---

## D5: react-force-graph-2d for Graph Visualization

**Decision:** Use `react-force-graph-2d` for the knowledge graph visualization in the browser.

**Alternatives considered:**
- (a) cytoscape.js (~170KB, DOM-based, full graph analysis API)
- (b) sigma.js (~100KB, WebGL, good for large graphs)
- (c) d3-force (raw d3, full control, steep API)
- **(d) react-force-graph-2d (~40KB, canvas, React API)** (chosen)
- (e) vis-network (~300KB, batteries-included)

**Why (d):** Smallest bundle (40KB gzip). Canvas-based renderer handles hundreds of nodes without DOM overhead. Wraps d3-force but exposes a React component API (fits codebase style). Built-in zoom, pan, click handlers. The 2D variant works on mobile (no WebGL requirement like 3D version).

**Mobile strategy:** Force-directed graphs are unusable on small touch screens. Below 768px viewport, show a `MobileGraphFallback` component — a searchable, type-grouped list of wiki pages. Detected via a `useMediaQuery` hook.

---

## D6: Haiku Default, Sonnet for Initial Page Creation

**Decision:** Use Claude Haiku for most compilation operations. Use Sonnet only for creating brand-new wiki pages from scratch.

**Alternatives considered:**
- (a) Sonnet for everything (best quality, 3x cost)
- **(b) Haiku default, Sonnet for initial creation** (chosen)
- (c) Haiku for everything (cheapest)
- (d) User selects model per compilation run

**Why (b):** Creating a new wiki page requires reasoning about structure, choosing wikilinks, and setting confidence. Sonnet handles this better. Subsequent updates (merging new information into an existing page) are simpler tasks that Haiku handles well. Topic clustering (titles + snippets only) uses Haiku because the input is small and the task is simple.

**Cost estimate:**
- Haiku: ~$0.25/M input, ~$1.25/M output tokens
- Sonnet: ~$3/M input, ~$15/M output tokens
- 100 sources at 500 tokens each, 500-token output pages
- Haiku-only: ~$0.03
- Mixed (new=Sonnet, updates=Haiku): ~$0.06
- Sonnet-only: ~$0.20

The `model` parameter on `/wiki/compile` allows overriding per request. Configurable default via `wiki_compile_model` setting.

---

## D7: On-Demand Compilation (Not Cron/Auto)

**Decision:** Compilation is triggered manually via `POST /wiki/compile`. No automatic or scheduled compilation.

**Alternatives considered:**
- (a) Auto-compile after every note/bookmark/PDF creation
- (b) Cron job (e.g., hourly)
- **(c) On-demand only, manual trigger** (chosen)
- (d) On-demand + optional auto-compile toggle

**Why (c):** Compilation costs real money (LLM API calls). A single user should control when it happens. Karpathy's own workflow is manual — he tells Claude to compile. Auto-compile could trigger on rapid-fire note creation, wasting tokens on partial data. The `wiki_auto_compile` config toggle exists (default false) for option (d) later.

**UX:** The compilation dashboard page shows pending (uncompiled) sources count and a "Run Compilation" button. Clear, intentional control.

---

## D8: Wiki Pages Participate in RAG (Also Embedded)

**Decision:** Wiki pages are chunked and embedded alongside raw sources. They participate in hybrid search with a 1.2x RRF score boost.

**Alternatives considered:**
- (a) Wiki pages are separate from RAG — only navigated via wikilinks
- **(b) Wiki pages are embedded and included in RAG search** (chosen)
- (c) Wiki pages replace raw source chunks in search results

**Why (b):** Wiki pages contain higher-quality, pre-structured text. Including them in RAG means the search pipeline benefits from compilation. The 1.2x boost is conservative — wiki chunks should surface above raw fragments of the same topic because they're more comprehensive. Raw chunks are still included (not replaced) because they provide original source evidence.

**Implementation:** After compilation, each wiki page is chunked and embedded using the existing `create_chunks_and_embeddings()` pipeline with `source_type = 'wiki_page'`. The only change to `rag_service.py` is adding a CASE branch for title resolution and applying the boost multiplier.

---

## D9: No Circular Compilation

**Decision:** Wiki pages cannot be sources for other wiki pages. Only `note`, `bookmark`, and `pdf` can appear in `wiki_sources.source_type`.

**Alternatives considered:**
- (a) Allow wiki-to-wiki compilation (meta-compilation)
- **(b) Restrict sources to raw content types only** (chosen)

**Why (b):** If wiki pages could compile from other wiki pages, a single source update could trigger an infinite cascade: source changes → page A recompiles → page B (which compiled from A) recompiles → page C (from B) recompiles... The wikilink graph provides cross-references between pages without requiring compilation dependency.

**How connections work without circular compilation:**
- `wiki_sources` = "this page was compiled FROM these raw sources" (data lineage)
- `wiki_links` = "this page MENTIONS these other wiki pages" (navigation)
- A page can link to any other page via `[[wikilinks]]` without needing to compile from it

---

## D10: Staleness Propagates Through Sources, Not Links

**Decision:** When a raw source (note/bookmark/PDF) is updated, only wiki pages that directly cite that source via `wiki_sources` are marked stale. Wiki pages that merely link to the affected page via `[[wikilinks]]` are NOT marked stale.

**Alternatives considered:**
- (a) Cascade staleness through the entire link graph (transitive)
- **(b) Mark stale only through wiki_sources (direct)** (chosen)
- (c) No automatic staleness — user runs lint to find stale pages

**Why (b):** Transitive staleness causes a domino effect. If page A links to page B, and B's source changes, A doesn't need recompilation — A's content about its own topic hasn't changed, only the page it links to has. This keeps recompilation focused on pages whose actual source material changed.

**SQL for staleness propagation:**
```sql
UPDATE wiki_pages SET is_stale = TRUE
WHERE id IN (
    SELECT wiki_page_id FROM wiki_sources
    WHERE source_type = :type AND source_id = :id
);
```

---

## D11: Obsidian Export as Zip Download

**Decision:** Export wiki pages as a downloadable `.zip` containing `.md` files with YAML frontmatter and `[[wikilinks]]`. Not a live sync.

**Alternatives considered:**
- (a) Live filesystem sync (inotify/fswatch)
- (b) Obsidian plugin that reads from API
- **(c) Download zip, drop into Obsidian vault** (chosen)
- (d) WebDAV mount

**Why (c):** Simplest implementation, no sync infrastructure. The export produces files that are immediately compatible with Obsidian's graph view, backlinks panel, and Dataview plugin. The user exports when they want a local copy. If they want continuous sync, option (a) can be added later.

**Export format per file:**
```markdown
---
title: Machine Learning Basics
type: concept
confidence: 0.85
sources:
  - note:42
  - bookmark:17
created: 2026-04-11
updated: 2026-04-11
---

Content with [[wikilinks]] preserved...
```

---

## D12: Slug-Based Routing for Wiki Pages

**Decision:** Wiki pages are identified by URL-safe slugs derived from titles.

**Alternatives considered:**
- (a) Numeric IDs in URLs (`/wiki/42`)
- **(b) Slug-based URLs (`/wiki/machine-learning-basics`)** (chosen)
- (c) Title-based URLs with encoding (`/wiki/Machine%20Learning%20Basics`)

**Why (b):** Human-readable, shareable URLs. Matches Obsidian's file naming convention (spaces → hyphens). `[[Machine Learning Basics]]` resolves to slug `machine-learning-basics` for both wikilink navigation and Obsidian file names.

**Slug generation:**
```python
import re
from unicodedata import normalize

def slugify(title: str) -> str:
    slug = normalize("NFKD", title).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^\w\s-]", "", slug).strip().lower()
    return re.sub(r"[-\s]+", "-", slug)
```

**Uniqueness:** UNIQUE constraint on `(user_id, slug)`. If collision, append `-2`, `-3`, etc.

---

## Decision Summary

| # | Decision | Key Trade-off |
|---|----------|---------------|
| D1 | Combine RAG + Wiki | Complexity of two systems vs. coverage of all query types |
| D2 | PostgreSQL graph | No native graph algorithms vs. zero infra overhead |
| D3 | JSONB frontmatter | No FK enforcement on sources list vs. schema flexibility |
| D4 | BackgroundTasks | No crash recovery vs. zero infrastructure |
| D5 | react-force-graph-2d | Limited graph analysis vs. smallest bundle + React API |
| D6 | Haiku + Sonnet mix | Slight quality inconsistency vs. 3x cost savings |
| D7 | On-demand compilation | Manual trigger vs. surprising LLM costs |
| D8 | Wiki in RAG | Slight ranking complexity vs. better search quality |
| D9 | No circular compilation | Can't build meta-knowledge vs. no infinite loops |
| D10 | Direct staleness only | Missing transitive changes vs. focused recompilation |
| D11 | Zip export | No live sync vs. zero sync infrastructure |
| D12 | Slug routing | Collision handling needed vs. human-readable URLs |
