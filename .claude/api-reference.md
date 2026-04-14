# API Reference

**Base URL:**
- Local: `http://localhost:8110/api/v1`
- Production: `https://api.brain.armandointeligencia.com/api/v1`

## Content Management Endpoints

### Notes

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/notes` | Create note (auto-chunks + embeds) |
| `GET` | `/notes` | List notes (paginated, filterable) |
| `GET` | `/notes/{id}` | Get note with tags |
| `PUT` | `/notes/{id}` | Update note (re-chunks + embeds) |
| `DELETE` | `/notes/{id}` | Archive/delete note |

### Bookmarks

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/bookmarks` | Save URL (auto-scrapes + chunks + embeds) |
| `GET` | `/bookmarks` | List bookmarks |
| `GET` | `/bookmarks/{id}` | Get bookmark |
| `PUT` | `/bookmarks/{id}` | Mark read, update tags |

### PDFs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/pdfs/upload` | Upload PDF (auto-extracts + chunks + embeds) |
| `GET` | `/pdfs` | List PDFs |
| `GET` | `/pdfs/{id}` | Get PDF metadata + text preview |

## Search & RAG Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/search` | Hybrid search (pgvector + tsvector + RRF) + RAG answer |
| `POST` | `/search/raw` | Raw chunk search (no LLM) |

### Search Request Body

```json
{
  "query": "What is backpropagation?",
  "top_k": 10,
  "use_sonnet": false,
  "include_sources": true
}
```

### Search Response

```json
{
  "answer": "Backpropagation is...",
  "sources": [
    {
      "id": "chunk_123",
      "content": "...",
      "source_type": "note",
      "source_id": 5
    }
  ],
  "model_used": "claude-haiku"
}
```

## Organization Endpoints

### Tags

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/tags` | List all tags |
| `POST` | `/tags` | Create tag |
| `DELETE` | `/tags/{id}` | Delete tag |

### Settings

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/settings` | Get user settings (LLM preference) |
| `PUT` | `/settings` | Update settings |

## Health Check

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

## Telegram Bot Commands

### Commands

| Command | Example | Description |
|---------|---------|-------------|
| `/add` | `/add Learned about pgvector today` | Quick note capture |
| `/search` | `/search What is backpropagation?` | Search with RAG answer |
| `/bookmark` | `/bookmark https://example.com/article` | Save + scrape URL |
| `/list` | `/list` | Show recent 5 items |
| `/tags` | `/tags` | Show all tags + counts |
| `/settings` | `/settings` | View/toggle LLM (Haiku/Sonnet) |
| `/help` | `/help` | Show all commands |

### Inline Button Callbacks

After `/add`: "Add Tags" → enter comma-separated tags
After `/search`: "Full Note", "Sonnet" (rerun with Sonnet model)
After `/bookmark`: "Save", "Skip"
After `/list` results: "View", "Tag", "Delete"

### Auto-URL Detection

Any message containing a URL is automatically saved as a bookmark (no command needed).

---

## Common Request Headers

```
Authorization: Bearer {token}  (if auth implemented)
Content-Type: application/json
```

## Error Responses

All errors follow this format:

```json
{
  "detail": "Detailed error message",
  "code": "ERROR_CODE"
}
```

### Common Status Codes

- `200 OK` — Successful request
- `201 Created` — Resource created successfully
- `400 Bad Request` — Invalid input
- `404 Not Found` — Resource not found
- `422 Unprocessable Entity` — Validation error
- `500 Internal Server Error` — Server error

## Interactive API Documentation

Once the backend is running locally, visit:
```
http://localhost:8110/docs
```

This provides an interactive Swagger UI to test all endpoints.
