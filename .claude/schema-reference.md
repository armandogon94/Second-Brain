# Database Schema Reference

**Location:** `backend/migrations/schema.sql`

## Tables Overview

### users
Single user table (MVP uses hardcoded user_id=1, but schema supports multi-user).

**Columns:**
- `id` (PK) — User identifier
- `username` — Username
- `email` — Email address
- `created_at` — Account creation timestamp

### notes
Text content with full-text indexing.

**Columns:**
- `id` (PK) — Note identifier
- `user_id` (FK) — Owner
- `title` — Note title
- `content` — Markdown text
- `source` — Creation source (web_ui, telegram)
- `is_archived` — Soft-delete flag
- `created_at` — Timestamp
- `updated_at` — Last modified timestamp

### bookmarks
Saved URLs with scraped content.

**Columns:**
- `id` (PK) — Bookmark identifier
- `user_id` (FK) — Owner
- `url` — Original URL (unique per user)
- `title` — Page title
- `domain` — Extracted domain
- `scraped_content` — Article text in Markdown
- `is_read` — Read status flag
- `is_archived` — Soft-delete flag
- `captured_at` — Save timestamp

### pdfs
Uploaded document metadata and extracted text.

**Columns:**
- `id` (PK) — PDF identifier
- `user_id` (FK) — Owner
- `filename` — Original filename
- `extracted_text` — Full text extracted by pdfplumber
- `page_count` — Number of pages
- `file_size` — Size in bytes
- `uploaded_at` — Upload timestamp
- `is_archived` — Soft-delete flag

### chunks
Text segments extracted from notes, bookmarks, and PDFs.

**Columns:**
- `id` (PK) — Chunk identifier
- `source_type` — (note, bookmark, pdf)
- `source_id` — Foreign key to source
- `chunk_index` — Position in sequence
- `content` — Text segment (~500 tokens)
- `token_count` — Exact token count (using tiktoken)
- `tsvector` — GENERATED ALWAYS full-text search vector

**Indexes:**
- GIN on tsvector for full-text search
- Foreign keys enforced

### embeddings
Vector embeddings (1536-dimensional).

**Columns:**
- `id` (PK) — Embedding identifier
- `chunk_id` (FK, unique) — Linked chunk
- `embedding` — pgvector (1536 dims, cosine distance)

**Indexes:**
- HNSW on embedding with vector_cosine_ops (m=16, ef_construction=64)

### tags
User-defined labels.

**Columns:**
- `id` (PK) — Tag identifier
- `user_id` (FK) — Owner
- `name` — Tag name (unique per user)
- `color` — Hex color (e.g., #FF5733)

### tag_assignments
Polymorphic many-to-many linking tags to notes, bookmarks, and PDFs.

**Columns:**
- `id` (PK)
- `tag_id` (FK) — Link to tags
- `assignable_type` — (Note, Bookmark, PDF)
- `assignable_id` — Foreign key to resource
- `created_at` — Assignment timestamp

**Unique constraint:** (tag_id, assignable_type, assignable_id)

## Key Indexes

| Index | Table | Type | Purpose |
|-------|-------|------|---------|
| `idx_embedding` | embeddings | HNSW | Semantic search (pgvector cosine) |
| `idx_chunks_tsvector` | chunks | GIN | Full-text search |
| `pk_notes` | notes | B-tree | Primary key |
| `fk_notes_user_id` | notes | B-tree | User lookup |
| `fk_bookmarks_user_id` | bookmarks | B-tree | User lookup |
| `fk_pdfs_user_id` | pdfs | B-tree | User lookup |
| `fk_embeddings_chunk_id` | embeddings | B-tree | Chunk lookup (unique) |
| `fk_chunks_source` | chunks | B-tree | Source lookup |
| `unique_bookmarks_url` | bookmarks | B-tree | URL uniqueness per user |
| `unique_tags_name` | tags | B-tree | Tag name uniqueness per user |

## Data Flow

1. **Content Ingestion:**
   - Note/Bookmark/PDF created → stored in respective table
   - Extracted text chunked → chunks table
   - Each chunk embedded → embeddings table (with HNSW index)

2. **Full-Text Search:**
   - tsvector GENERATED ALWAYS from chunks.content
   - GIN index enables fast prefix/phrase search

3. **Vector Search:**
   - Query text embedded → 1536-dim vector
   - HNSW nearest-neighbor search → top-k chunks

4. **Hybrid Search:**
   - Both searches executed in parallel
   - Results merged with Reciprocal Rank Fusion
   - Top 10 returned to LLM for RAG

## Schema Constraints

- All tables have `user_id` for multi-user support
- Foreign keys cascade on delete (soft-delete via is_archived also available)
- Unique constraints on (user_id, name) for tags
- Unique constraints on (user_id, url) for bookmarks
- Chunk token_count must be >0
- Embedding must be NOT NULL

## Performance Tuning

| Operation | Expected Latency |
|-----------|-----------------|
| Vector search (HNSW) | 2-20ms |
| Full-text search (GIN) | 7-15ms |
| Combined hybrid search | <20ms |
| Index creation | ~2-5s per 100K documents |
| Bulk insert chunks | 50-100K/sec |
