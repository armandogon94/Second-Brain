import os
import sys

# Add parent directory to path so app module is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from app.config import settings
from app.utils.logger import logger
from telegram_bot.handlers import (
    add_handler,
    auto_url_handler,
    bookmark_handler,
    callback_handler,
    error_handler,
    help_handler,
    list_handler,
    search_handler,
    settings_handler,
    start_handler,
    tags_handler,
)


def main():
    if not settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        sys.exit(1)

    user_filter = filters.User(user_id=settings.telegram_user_id) if settings.telegram_user_id else filters.ALL

    application = ApplicationBuilder().token(settings.telegram_bot_token).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start_handler, filters=user_filter))
    application.add_handler(CommandHandler("help", help_handler, filters=user_filter))
    application.add_handler(CommandHandler("add", add_handler, filters=user_filter))
    application.add_handler(CommandHandler("search", search_handler, filters=user_filter))
    application.add_handler(CommandHandler("bookmark", bookmark_handler, filters=user_filter))
    application.add_handler(CommandHandler("list", list_handler, filters=user_filter))
    application.add_handler(CommandHandler("tags", tags_handler, filters=user_filter))
    application.add_handler(CommandHandler("settings", settings_handler, filters=user_filter))

    # Callback query handler (inline keyboard buttons)
    application.add_handler(CallbackQueryHandler(callback_handler))

    # Auto-detect URLs in plain messages
    application.add_handler(
        MessageHandler(filters.Entity("url") & ~filters.COMMAND & user_filter, auto_url_handler)
    )

    # Error handler
    application.add_error_handler(error_handler)

    # Run in appropriate mode
    if settings.environment == "production" and settings.webhook_url:
        logger.info("Starting bot in webhook mode: %s", settings.webhook_url)
        application.run_webhook(
            listen="0.0.0.0",
            port=8001,
            webhook_url=settings.webhook_url,
            secret_token=settings.webhook_secret,
        )
    else:
        logger.info("Starting bot in polling mode")
        application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
