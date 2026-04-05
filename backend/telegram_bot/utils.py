from functools import wraps

from telegram import Update

from app.config import settings


def restricted(func):
    """Restrict bot access to the configured Telegram user."""

    @wraps(func)
    async def wrapped(update: Update, context, *args, **kwargs):
        user_id = update.effective_user.id if update.effective_user else None
        if user_id != settings.telegram_user_id:
            return
        return await func(update, context, *args, **kwargs)

    return wrapped


def truncate(text: str, max_length: int = 4000) -> str:
    """Truncate text to fit Telegram's message limit (4096 chars)."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def format_source_preview(source_type: str, title: str | None, content: str) -> str:
    """Format a source for Telegram display."""
    icon = {"note": "📝", "bookmark": "🔗", "pdf": "📄"}.get(source_type, "📎")
    label = title or f"{source_type}"
    preview = content[:150].replace("\n", " ")
    return f"{icon} <b>{label}</b>\n{preview}"
