# Port Allocation — Project 11: Second Brain

> All host-exposed ports are globally unique across all 16 projects so every project can run simultaneously. See `../PORT-MAP.md` for the full map.

## Current Assignments

| Service | Host Port | Container Port | File |
|---------|-----------|---------------|------|
| Frontend (Next.js) | **3110** | 3000 | docker-compose.yml |
| Backend (FastAPI) | **8110** | 8000 | docker-compose.yml |
| Telegram Bot | **8111** | 8001 | docker-compose.yml |
| PostgreSQL | **5436** | 5432 | docker-compose.yml (via `${DB_PORT:-5436}`) |

## Allowed Range for New Services

If you need to add a new service to this project, pick from these ranges **only**:

| Type | Allowed Host Ports |
|------|--------------------|
| Frontend / UI | `3110 – 3119` |
| Backend / API | `8110 – 8119` |
| PostgreSQL | `5436` (already assigned — do not spin up a second instance) |
| Redis | Not assigned. If needed, request an assignment in `../PORT-MAP.md`. |

Available slots: `3111-3119`, `8112-8119`.

## Do Not Use

Every port outside the ranges above is reserved by another project. Always check `../PORT-MAP.md` before picking a port.

Key ranges already taken:
- `3100-3109 / 8100-8109` → Project 10
- `3120-3129 / 8120-8129` → Project 12
- `5432` → P02, `5433` → P03, `5434` → P04, `5435` → P05
- `5437-5439` → Projects 12, 13, 15 PostgreSQL
- `6379-6385` → Projects 02, 05, 10, 12, 13, 15, 16 Redis
