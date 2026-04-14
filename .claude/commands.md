# Development Commands

## Backend (Python + uv)

```bash
# Install dependencies
cd backend
uv sync

# Run dev server
uv run uvicorn app.main:app --reload --port 8110

# Run tests
uv run pytest -v

# Format/lint
uv run ruff check .
uv run ruff format .
```

## Frontend (Next.js)

```bash
# Install dependencies
cd frontend
npm install

# Run dev server
npm run dev -- -p 3110

# Build for production
npm run build

# Run tests
npx vitest run
```

## Docker

```bash
# Build all images
docker compose build

# Start all services
docker compose up -d

# View logs
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f telegram-bot

# Stop all services
docker compose down

# Reset database
docker compose exec postgres psql -U armando -d second_brain_db -f /docker-entrypoint-initdb.d/01-schema.sql

# Health check
curl http://localhost:8110/health
```

## Makefile Targets

```bash
make dev          # Start all services in foreground
make build        # Build all Docker images
make test         # Run all tests (backend + frontend)
make deploy       # Deploy to production (requires SSH)
make db-reset     # Reset PostgreSQL database
make setup        # Initial setup (.env, dependencies)
make clean        # Remove containers, volumes, build artifacts
```

## Common Workflows

### Development with Live Reload

```bash
# Terminal 1: Backend
cd backend && uv run uvicorn app.main:app --reload --port 8110

# Terminal 2: Frontend
cd frontend && npm run dev -- -p 3110

# Terminal 3: PostgreSQL + Redis (or use existing instances)
docker compose up postgres redis
```

### Run Full Test Suite

```bash
make test
# or individually:
cd backend && uv run pytest -v
cd frontend && npm test
```

### Local Docker Testing

```bash
docker compose build
docker compose up -d
curl http://localhost:8110/health  # verify backend
```

### Database Migrations

```bash
# View current schema
cat backend/migrations/schema.sql

# Reset to clean state
make db-reset

# Or manually via psql
docker compose exec postgres psql -U armando -d second_brain_db
```
