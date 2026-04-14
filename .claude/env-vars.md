# Environment Variables

**Required:** All variables in `.env.example` must be populated before running.

## Database

| Variable | Example | Required | Purpose |
|----------|---------|----------|---------|
| `DATABASE_URL` | `postgresql+asyncpg://armando:pass@postgres:5432/second_brain_db` | Yes | PostgreSQL connection string with asyncpg driver |
| `DB_PORT` | `5432` | No | PostgreSQL host port (for local dev, when exposed) |

## API Keys

| Variable | Example | Required | Purpose |
|----------|---------|----------|---------|
| `OPENAI_API_KEY` | `sk-...` | Yes | OpenAI API key for embeddings (text-embedding-3-small) |
| `ANTHROPIC_API_KEY` | `sk-ant-...` | Yes | Anthropic API key for Claude LLM (Haiku/Sonnet) |

## Telegram Bot

| Variable | Example | Required | Purpose |
|----------|---------|----------|---------|
| `TELEGRAM_BOT_TOKEN` | `123456789:ABCdef...` | Yes | Bot token from Telegram BotFather |
| `TELEGRAM_USER_ID` | `12345678` | Yes | Your Telegram user ID (for access control) |

## Application

| Variable | Example | Required | Purpose |
|----------|---------|----------|---------|
| `SECRET_KEY` | `your-secret-random-string` | Yes | Used for hashing, tokens, CSRF protection |
| `ENVIRONMENT` | `development` or `production` | No | Controls Telegram polling/webhook mode |
| `LOG_LEVEL` | `INFO` | No | Logging level (DEBUG, INFO, WARNING, ERROR) |

## Frontend

| Variable | Example | Required | Purpose |
|----------|---------|----------|---------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8110` (dev) or `https://api.brain.armandointeligencia.com` (prod) | No | Backend API base URL (must be public for browser) |

## Infrastructure (Production Only)

| Variable | Example | Required | Purpose |
|----------|---------|----------|---------|
| `LETSENCRYPT_EMAIL` | `your@email.com` | Prod only | Email for Let's Encrypt SSL certificate registration |

## Redis (Optional, for scaling)

| Variable | Example | Required | Purpose |
|----------|---------|----------|---------|
| `REDIS_URL` | `redis://localhost:6379/9` | No | Redis connection (DB #9 reserved for Second Brain) |

---

## Setup Instructions

### Development

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Fill in required variables:
   - Get OPENAI_API_KEY from https://platform.openai.com/api-keys
   - Get ANTHROPIC_API_KEY from https://console.anthropic.com/
   - Get TELEGRAM_BOT_TOKEN from @BotFather on Telegram
   - Get your TELEGRAM_USER_ID from @userinfobot on Telegram
   - Generate SECRET_KEY with: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

3. Verify PostgreSQL is running (port 5432)

4. Start services:
   ```bash
   docker compose up -d postgres redis
   # or use existing shared instances
   ```

### Production

1. Add all required variables to production environment

2. Set `ENVIRONMENT=production` (enables webhook mode for Telegram)

3. Configure Telegram webhook:
   - Set webhook URL: `https://telegram.brain.armandointeligencia.com`
   - Traefik automatically routes to bot service

4. SSL certificates:
   - Traefik auto-provisions with Let's Encrypt
   - Provide `LETSENCRYPT_EMAIL` for certificate registration

---

## Security Notes

- Never commit `.env` to git (already in `.gitignore`)
- API keys should be read-only scoped (e.g., embeddings-only for OpenAI)
- Rotate `SECRET_KEY` periodically
- Use environment variable management for production (not shell export)
- For VPS deployment, use `.env` file with restricted permissions (600)

## Environment-based Behavior

| Setting | Development | Production |
|---------|-------------|-----------|
| Telegram mode | Polling | Webhook |
| Database URL | localhost:5432 | postgres service (DNS) |
| API URL | http://localhost:8110 | https://api.brain.armandointeligencia.com |
| CORS origins | localhost:3110 | brain.armandointeligencia.com |
| Log level | DEBUG | INFO |
