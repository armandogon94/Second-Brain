# Second Brain — Research Findings

> Complete research findings from 4 parallel research agents run on 2026-04-01.
> These findings informed all architectural decisions in memory.md.

---

## 1. RAG Pipeline Research

### pgvector on PostgreSQL 16
- **Docker image:** `pgvector/pgvector:pg16` (official, pre-installed)
- **HNSW vs IVFFLAT:** HNSW wins for our use case — better recall, handles inserts, no reindex needed
  - HNSW: query 2-6ms, build 29s for 25K vectors, good recall out-of-box
  - IVFFLAT: query 2-10ms, build 5s, requires tuning `lists`/`probes`, needs periodic REINDEX
- **Performance at scale:** 10-50K vectors → 2-10ms, 100K → ~18ms, 1M → ~45ms
- **Distance operator:** Cosine (`<=>`) with `vector_cosine_ops`. OpenAI returns normalized vectors so cosine = inner product in rankings. CRITICAL: operator must match index operator class or PostgreSQL silently falls back to sequential scan.

### Embedding Models
| Model | Dims | Price/1M tokens | MTEB |
|-------|------|-----------------|------|
| text-embedding-3-small | 1536 | $0.02 | 62.3 |
| text-embedding-3-large | 3072 | $0.13 | 64.6 |
| Cohere embed-v3 | 1024 | $0.10 | 64.5 |
| Voyage voyage-3.5 | 1024 | $0.06 | ~67 |
| all-MiniLM-L6-v2 (local) | 384 | Free | ~58 |

**Chosen:** text-embedding-3-small — best value, $1.20 for 100K docs total.

### Chunking Strategy
- **Optimal:** 256-512 tokens (research consensus from NVIDIA, Firecrawl)
- **Overlap:** 10-20% (50 tokens for 500 target). One study found no measurable benefit from overlap, but we keep it as low-cost insurance.
- **Best splitter:** RecursiveCharacterTextSplitter (85-90% recall). Semantic chunking gives ~9% better at much higher cost.
- **Token counting:** tiktoken with `cl100k_base` encoding (used by text-embedding-3-small/large)

### Hybrid Search
- **Vector-only:** ~62% precision. **Hybrid (vector + FTS + RRF):** ~84% precision
- **RRF formula:** `score = 1 / (k + rank)`, k=60 is standard
- **Implementation:** UNION ALL both result sets, GROUP BY chunk_id, SUM RRF scores, ORDER BY score DESC
- **Over-fetch:** Get 20 from each method, select top 10 after fusion
- **tsvector:** Use `GENERATED ALWAYS AS` column for auto-sync (no triggers)
- **Performance:** Combined search <20ms on 50K rows

### RAG Prompt Engineering
- **System prompt:** Explicit rules: check context first, cite sources, distinguish notes vs general knowledge, never fabricate
- **Citation format:** [Source N] identifiers in prompt, post-process to link back to metadata
- **Context:** 5-10 chunks (we use 10), ordered by relevance (highest first)
- **No-match handling:** Similarity threshold 0.3. Below threshold: "I didn't find anything about this in your notes."
- **Anti-hallucination:** Citation requirement, chain-of-thought quoting, confidence classification

---

## 2. Content Ingestion Research

### PDF Extraction
| Library | Speed | Quality | License | Notes |
|---------|-------|---------|---------|-------|
| pdfplumber | Moderate (~0.1s/page) | Good tables | MIT | Best for structured docs |
| PyMuPDF/fitz | Fastest (5-10x) | Highest F1 (0.973) | AGPL-3.0 | License risk |
| pypdf | Fast (0.024s) | Adequate | BSD | Simple text only |
| pymupdf4llm | Fastest | Best (outputs Markdown) | AGPL-3.0 | Auto-OCR, but AGPL |

**Chosen:** pdfplumber (MIT). OCR fallback: pytesseract + pdf2image (optional extras).

### URL Scraping
| Library | F1 Score | Output | Status |
|---------|----------|--------|--------|
| trafilatura | 0.958 | Markdown, TXT, XML, JSON | Active (v2.0.0) |
| newspaper4k | 0.949 | Text | Active (fork of newspaper3k) |
| readability-lxml | 0.922 | HTML | Stable |

**Chosen:** trafilatura with Markdown output. No JS rendering needed for MVP.
**Rate limiting:** 2s delay between same-domain requests, exponential backoff on 429s.

### Markdown Storage
**Decision:** Store raw markdown only. Render on frontend with react-markdown + remark-gfm + rehype-highlight.
**Rationale:** Single source of truth, searchable, portable, no sync issues. Notion stores proprietary JSON (cautionary tale).

---

## 3. Telegram Bot Research

### python-telegram-bot v22.x
- Fully async since v20.0, now at v22.7 with Bot API 9.5 support
- Key classes: Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler
- Handler signature: `async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE)`
- Inline keyboards: 64-byte callback_data limit, 100 buttons max per message
- File downloads: 20MB max via Bot API
- Typing indicator: lasts 5 seconds, resend for longer operations

### Bot UX Patterns
- **Auto-detect URLs:** `MessageHandler(filters.Entity("url"), auto_bookmark)` catches plain URLs
- **HTML parse mode:** Much simpler than MarkdownV2 (20+ chars need escaping in MarkdownV2)
- **Edit messages in-place:** For button actions, cleaner than sending new messages
- **Single-user filter:** `filters.User(user_id=ALLOWED_USER_ID)` on every handler
- **Pagination:** `python-telegram-bot-pagination` library for inline keyboard pages

### Webhook vs Polling
- **Polling:** `run_polling()` — simple, no public URL needed, good for dev
- **Webhook:** `run_webhook()` — lower latency, no wasted calls, requires HTTPS
- **Behind Traefik:** Use dedicated subdomain (`telegram.brain.armandointeligencia.com`), Traefik handles SSL, bot receives plain HTTP on port 8001
- **Dual mode:** Switch via `ENVIRONMENT` env var

---

## 4. Frontend Research

### Search UX
- **Debounce:** `use-debounce` v10.1 (300ms delay), ~1KB
- **Cmd+K:** shadcn `<CommandDialog>` (built on cmdk by Paco Coursey)
- **Highlighting:** `react-highlight-words` — wraps matches in `<mark>` tags
- **Data fetching:** SWR for client search, Suspense for initial page loads

### Markdown Editor
| Library | Bundle (gzip) | Markdown I/O | Notes |
|---------|--------------|--------------|-------|
| @uiw/react-md-editor | 4.6 KB | Native | Split-pane, toolbar, GFM |
| TipTap + markdown ext | 311 KB | Via extension | Overkill for personal notes |
| MDXEditor | 851 KB | Native MDX | Rendering issues |

**Chosen:** @uiw/react-md-editor — smallest bundle, native markdown, split-pane out of box.

### PDF Viewer
**Skip for MVP.** Show extracted text preview + download link. Add react-pdf v10.x later if needed (~500KB pdf.js bundle saved).

### UI Stack
- **SWR** (4KB) over TanStack Query (13KB) — sufficient for this project
- **Sonner** for toasts — shadcn/ui's official toast, promise API
- **next-themes** for dark mode — `darkMode: 'class'` in tailwind
- **Total additional JS:** ~16KB gzip

### Shadcn Components Used
command, dialog, sheet, tabs, card, input, button, badge, dropdown-menu, skeleton, textarea, toggle, tooltip
```bash
npx shadcn@latest add command dialog sheet tabs card input button badge dropdown-menu skeleton textarea toggle tooltip
```
