# Gotchas & Known Issues

## pgvector Index/Operator Mismatch

If index uses `vector_cosine_ops` but query uses `<->` (L2), PostgreSQL silently falls back to sequential scan. Always verify operator matches.

**Fix:** Always use `<->` with `vector_cosine_ops` index, or switch to `<#>` for L2 distance.

## Telegram MarkdownV2 Escaping

20+ special characters need escaping (underscore, asterisk, brackets, etc.). Use HTML parse mode instead (much simpler).

**Current approach:** All bot messages use HTML parse_mode. Avoids escaping nightmare.

## Telegram callback_data Limit

InlineKeyboardButton callback_data limited to 64 bytes. Use short prefixes: `tag:123`, `page:2`.

**Solution:** For longer data, store in Redis with key, pass only key in callback_data.

## Telegram Typing Indicator Duration

Typing indicator lasts only 5 seconds. If operation takes longer (e.g., embedding), resend every 4 seconds via asyncio.create_task.

**Current approach:** Long operations resend typing indicator as needed.

## SQLite Tests for PostgreSQL-specific Types

Backend tests use SQLite (in-memory) for speed. PostgreSQL types (JSONB, TSVECTOR, Vector) handled via SQLAlchemy `@compiles` decorators in `tests/conftest.py`.

**Key:** Don't expect `Vector` or `TSVECTOR` to work in test SQLite. Mock at service level.

## Mock Patching Location

Patch at the **import location** (where used), not **definition location** (where defined).

```python
# WRONG:
from app.services import embedding_service
mock_patch('app.services.embedding_service.OpenAIClient')

# RIGHT:
mock_patch('app.api.notes.embedding_service.OpenAIClient')
```

## SQLAlchemy onupdate with Async SQLite

`onupdate=func.now()` can cause `MissingGreenlet` errors in async SQLite tests. Set explicitly in handlers instead.

**Fix:** Use a custom setter or update explicitly in the service layer.

## next-themes Import Path

Import from `"next-themes"`, not `"next-themes/dist/types"`.

```typescript
// WRONG:
import type { ThemeProvider } from "next-themes/dist/types";

// RIGHT:
import { ThemeProvider } from "next-themes";
```

## vitest.config.ts and Next.js Build

vitest config can cause type conflicts during `next build`. Exclude it from tsconfig:

```json
{
  "exclude": ["node_modules", "vitest.config.ts"]
}
```

## PDF Extraction Performance

pdfplumber can be slow on large PDFs (>100 pages). Disable OCR by default; only enable on user request.

**Current approach:** OCR is opt-in via query parameter.

## OpenAI Embedding Rate Limits

text-embedding-3-small has 3000 requests/min and 125M tokens/min limits. Batch calls in groups of 100 to be safe.

**Current approach:** `EmbeddingService` batches up to 100 texts per API call.

## Anthropic Token Counting

Claude models may have slight token count variance. Use official `anthropic.messages.CountTokensResponse` for accurate accounting.

**Current approach:** Count tokens before sending to LLM for cost estimation.

## PostgreSQL Connection Pooling

With 3 projects sharing one PostgreSQL instance, ensure connection pool settings are conservative to avoid exhaustion.

**Current approach:** Max pool size = 20 per service, idle timeout = 30s.

## Docker Compose Service Name Resolution

Services can access each other by hostname (e.g., `postgres:5432`), but this only works within the compose network. Local development must use `localhost`.

**Current approach:** `DATABASE_URL` env var adjusts for local vs Docker.

## Traefik SSL Certificate Generation

First boot of Traefik may fail if `acme.json` doesn't exist. Create empty file or let Traefik initialize it.

```bash
touch acme.json
chmod 600 acme.json
```

## Duplicate Chunk Prevention

If a note is updated multiple times, chunks from old versions aren't automatically deleted. Implement soft-delete on chunk updates.

**Current approach:** Old chunks are archived via is_archived flag.

## CORS Headers and Cookies

CORS is configured to allow `localhost:3110` in development. For production, update allowed origins in `config.py`.

**Current approach:** `CORS_ORIGINS` env var controls allowed domains.

## Environment Variable Defaults

Some env vars have defaults (e.g., `LOG_LEVEL=INFO`), others are required. Check `config.py` for the distinction.

**Required vars:** DATABASE_URL, OPENAI_API_KEY, ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN, SECRET_KEY

## Session Cleanup

The `AsyncSessionLocal` context manager may leave connections open if exceptions occur. Always use `async with` pattern or ensure cleanup in finally blocks.

**Current approach:** All database operations use dependency injection with automatic cleanup.

## Hybrid Search RRF Scoring

The Reciprocal Rank Fusion formula is: `score = 1 / (k + rank)` where k=60. Ensure both vector and full-text queries return consistent result sets for proper scoring.

**Current approach:** Over-fetch 20 from each source, then merge and re-rank.
