.PHONY: dev dev-backend dev-frontend dev-bot build up down logs test test-backend test-frontend lint clean db-reset

# Development
dev: ## Start all services for local development
	docker compose up -d postgres
	@echo "Waiting for PostgreSQL..."
	@sleep 3
	$(MAKE) dev-backend &
	$(MAKE) dev-frontend &
	wait

dev-backend: ## Start backend in development mode
	cd backend && uv run uvicorn app.main:app --reload --port 8110

dev-frontend: ## Start frontend in development mode
	cd frontend && npm run dev -- -p 3110

dev-bot: ## Start Telegram bot in development mode
	cd backend && uv run python -m telegram_bot.bot

# Docker
build: ## Build all Docker images
	docker compose build

up: ## Start all services via Docker Compose
	docker compose up -d

down: ## Stop all services
	docker compose down

logs: ## Follow logs for all services
	docker compose logs -f

logs-backend: ## Follow backend logs
	docker compose logs -f backend

logs-bot: ## Follow telegram bot logs
	docker compose logs -f telegram-bot

# Testing
test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend tests
	cd backend && uv run pytest -v --tb=short

test-frontend: ## Run frontend tests
	cd frontend && npx vitest run

# Linting
lint: ## Run linters
	cd backend && uv run ruff check .
	cd frontend && npm run lint

lint-fix: ## Fix linting issues
	cd backend && uv run ruff check --fix .

# Database
db-reset: ## Reset database (WARNING: destroys all data)
	docker compose down -v
	docker compose up -d postgres
	@echo "Database reset. Run 'make up' to start all services."

db-shell: ## Open PostgreSQL shell
	docker compose exec postgres psql -U $${DB_USER:-armando} -d $${DB_NAME:-second_brain_db}

# Cleanup
clean: ## Remove build artifacts and caches
	find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find backend -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf frontend/.next frontend/node_modules 2>/dev/null || true

# Setup
setup: ## Initial project setup
	cd backend && uv sync
	cd frontend && npm install
	cp -n .env.example .env 2>/dev/null || true
	@echo "Setup complete. Edit .env with your API keys, then run 'make dev'"

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
