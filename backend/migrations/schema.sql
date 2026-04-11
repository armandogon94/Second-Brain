-- Second Brain Database Schema
-- PostgreSQL 16 + pgvector

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Users table (single user for now, schema supports multi-user)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    telegram_user_id BIGINT,
    llm_preference VARCHAR(50) DEFAULT 'haiku',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    settings JSONB DEFAULT '{}'
);

-- Insert default user
INSERT INTO users (username, llm_preference)
VALUES ('armando', 'haiku')
ON CONFLICT (username) DO NOTHING;

-- Notes table
CREATE TABLE IF NOT EXISTS notes (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL DEFAULT 1,
    content TEXT NOT NULL,
    markdown_content TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(50) NOT NULL DEFAULT 'web_ui',
    is_archived BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}',
    CONSTRAINT fk_notes_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Bookmarks table
CREATE TABLE IF NOT EXISTS bookmarks (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL DEFAULT 1,
    original_url TEXT NOT NULL,
    title VARCHAR(500),
    scraped_content TEXT,
    source_domain VARCHAR(255),
    captured_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    is_read BOOLEAN DEFAULT FALSE,
    is_archived BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}',
    CONSTRAINT fk_bookmarks_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, original_url)
);

-- PDFs table
CREATE TABLE IF NOT EXISTS pdfs (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL DEFAULT 1,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    extracted_text TEXT,
    page_count INT,
    file_size INT,
    uploaded_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    is_archived BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}',
    CONSTRAINT fk_pdfs_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Chunks table (segmented text for embedding)
CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL DEFAULT 1,
    source_type VARCHAR(50) NOT NULL,
    source_id INT NOT NULL,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    character_count INT,
    token_count INT,
    search_vector TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_chunks_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Embeddings table
CREATE TABLE IF NOT EXISTS embeddings (
    id SERIAL PRIMARY KEY,
    chunk_id INT NOT NULL UNIQUE,
    embedding vector(1536),
    embedding_model VARCHAR(100) DEFAULT 'text-embedding-3-small',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_embeddings_chunk FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
);

-- Tags table
CREATE TABLE IF NOT EXISTS tags (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL DEFAULT 1,
    name VARCHAR(100) NOT NULL,
    color VARCHAR(7),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tags_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, name)
);

-- Tag assignments (polymorphic many-to-many)
CREATE TABLE IF NOT EXISTS tag_assignments (
    id SERIAL PRIMARY KEY,
    tag_id INT NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    source_id INT NOT NULL,
    assigned_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tag_assignments_tag FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
    UNIQUE(tag_id, source_type, source_id)
);

-- Indexes
-- HNSW vector index for semantic search (cosine similarity)
CREATE INDEX IF NOT EXISTS idx_embeddings_hnsw ON embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- GIN index for full-text search on chunks (auto-generated tsvector column)
CREATE INDEX IF NOT EXISTS idx_chunks_fts ON chunks USING GIN (search_vector);

-- Full-text search on notes
CREATE INDEX IF NOT EXISTS idx_notes_fts ON notes
    USING GIN (to_tsvector('english', content));

-- Full-text search on bookmarks
CREATE INDEX IF NOT EXISTS idx_bookmarks_fts ON bookmarks
    USING GIN (to_tsvector('english', COALESCE(scraped_content, '')));

-- Query performance indexes
CREATE INDEX IF NOT EXISTS idx_notes_user_created ON notes(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_bookmarks_user_created ON bookmarks(user_id, captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_pdfs_user_uploaded ON pdfs(user_id, uploaded_at DESC);
CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_chunks_user ON chunks(user_id);
CREATE INDEX IF NOT EXISTS idx_tags_user ON tags(user_id, name);
CREATE INDEX IF NOT EXISTS idx_tag_assignments_source ON tag_assignments(source_type, source_id);

-- ─── Wiki tables ────────────────────────────────────────────────────────────

-- Wiki pages (LLM-compiled articles with markdown + frontmatter)
CREATE TABLE IF NOT EXISTS wiki_pages (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL DEFAULT 1,
    slug VARCHAR(255) NOT NULL,
    title VARCHAR(500) NOT NULL,
    page_type VARCHAR(50) NOT NULL DEFAULT 'concept',
    content_markdown TEXT NOT NULL DEFAULT '',
    frontmatter JSONB DEFAULT '{}',
    confidence FLOAT DEFAULT 0.8,
    is_published BOOLEAN DEFAULT TRUE,
    is_stale BOOLEAN DEFAULT FALSE,
    version INT DEFAULT 1,
    compiled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    search_vector TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', title), 'A') ||
        setweight(to_tsvector('english', content_markdown), 'B')
    ) STORED,
    CONSTRAINT fk_wiki_pages_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, slug)
);

-- Wiki links (graph edges between wiki pages)
CREATE TABLE IF NOT EXISTS wiki_links (
    id SERIAL PRIMARY KEY,
    from_page_id INT NOT NULL,
    to_page_id INT NOT NULL,
    link_text VARCHAR(255) NOT NULL,
    context_snippet TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_wiki_links_from FOREIGN KEY (from_page_id) REFERENCES wiki_pages(id) ON DELETE CASCADE,
    CONSTRAINT fk_wiki_links_to FOREIGN KEY (to_page_id) REFERENCES wiki_pages(id) ON DELETE CASCADE,
    UNIQUE(from_page_id, to_page_id, link_text)
);

-- Wiki sources (tracks which raw sources compiled into which pages)
CREATE TABLE IF NOT EXISTS wiki_sources (
    id SERIAL PRIMARY KEY,
    wiki_page_id INT NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    source_id INT NOT NULL,
    source_hash VARCHAR(64),
    compiled_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_wiki_sources_page FOREIGN KEY (wiki_page_id) REFERENCES wiki_pages(id) ON DELETE CASCADE,
    UNIQUE(wiki_page_id, source_type, source_id)
);

-- Compilation log (append-only log of compilation runs)
CREATE TABLE IF NOT EXISTS compilation_log (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL DEFAULT 1,
    action VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    sources_processed INT DEFAULT 0,
    pages_created INT DEFAULT 0,
    pages_updated INT DEFAULT 0,
    token_usage JSONB DEFAULT '{}',
    error_message TEXT,
    started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    details JSONB DEFAULT '{}',
    CONSTRAINT fk_compilation_log_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Wiki indexes
CREATE INDEX IF NOT EXISTS idx_wiki_pages_slug ON wiki_pages(user_id, slug);
CREATE INDEX IF NOT EXISTS idx_wiki_pages_user_type ON wiki_pages(user_id, page_type);
CREATE INDEX IF NOT EXISTS idx_wiki_pages_fts ON wiki_pages USING GIN (search_vector);
CREATE INDEX IF NOT EXISTS idx_wiki_links_from ON wiki_links(from_page_id);
CREATE INDEX IF NOT EXISTS idx_wiki_links_to ON wiki_links(to_page_id);
CREATE INDEX IF NOT EXISTS idx_wiki_sources_source ON wiki_sources(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_wiki_sources_page ON wiki_sources(wiki_page_id);
CREATE INDEX IF NOT EXISTS idx_compilation_log_status ON compilation_log(user_id, status);
