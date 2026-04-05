from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes

from app.database import async_session
from app.models import Bookmark, Note, Tag, TagAssignment
from app.services.embedding_service import create_chunks_and_embeddings
from app.services.rag_service import hybrid_search, search_and_answer
from app.services.scraping_service import scrape_url
from app.utils.logger import logger
from sqlalchemy import func, select

from telegram_bot.utils import format_source_preview, restricted, truncate


@restricted
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "<b>Welcome to Second Brain!</b>\n\n"
        "I'm your personal knowledge assistant. Here's what I can do:\n\n"
        "/add &lt;text&gt; — Save a quick note\n"
        "/search &lt;query&gt; — Search with AI\n"
        "/bookmark &lt;url&gt; — Save a URL\n"
        "/list — Recent items\n"
        "/tags — Your tags\n"
        "/settings — Preferences\n"
        "/help — This message",
        parse_mode=ParseMode.HTML,
    )


@restricted
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start_handler(update, context)


@restricted
async def add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /add &lt;your note text&gt;", parse_mode=ParseMode.HTML)
        return

    text = " ".join(context.args)

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    async with async_session() as db:
        note = Note(content=text, markdown_content=text, source="telegram")
        db.add(note)
        await db.flush()

        await create_chunks_and_embeddings(db, "note", note.id, text)
        await db.commit()

        keyboard = [[InlineKeyboardButton("Add Tags", callback_data=f"add_tags:{note.id}")]]
        await update.message.reply_text(
            f"✅ <b>Note saved!</b> (ID: {note.id})",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


@restricted
async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "Usage: /search &lt;your question&gt;", parse_mode=ParseMode.HTML
        )
        return

    query = " ".join(context.args)

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    async with async_session() as db:
        result = await search_and_answer(db, query, limit=5, llm_model="haiku")

    answer = truncate(result["answer"])
    sources_text = ""
    if result["sources"]:
        source_lines = []
        for s in result["sources"][:3]:
            icon = {"note": "📝", "bookmark": "🔗", "pdf": "📄"}.get(s["source_type"], "📎")
            label = s.get("title") or s["source_type"]
            source_lines.append(f"  {icon} {label}")
        sources_text = "\n\n<b>Sources:</b>\n" + "\n".join(source_lines)

    keyboard = [
        [InlineKeyboardButton("🔄 Ask Sonnet", callback_data=f"sonnet:{query[:50]}")],
    ]

    await update.message.reply_text(
        f"{answer}{sources_text}",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


@restricted
async def bookmark_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "Usage: /bookmark &lt;url&gt;", parse_mode=ParseMode.HTML
        )
        return

    url = context.args[0]

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    try:
        scraped = await scrape_url(url)
    except Exception as e:
        await update.message.reply_text(f"❌ Could not extract content: {e}")
        return

    async with async_session() as db:
        bookmark = Bookmark(
            original_url=url,
            title=scraped["title"],
            scraped_content=scraped["content"],
            source_domain=scraped["domain"],
        )
        db.add(bookmark)
        await db.flush()

        if scraped["content"]:
            await create_chunks_and_embeddings(db, "bookmark", bookmark.id, scraped["content"])

        await db.commit()

        preview = truncate(scraped["content"], 200) if scraped["content"] else "No content extracted"
        keyboard = [
            [InlineKeyboardButton("Add Tags", callback_data=f"add_tags_b:{bookmark.id}")],
        ]
        await update.message.reply_text(
            f'✅ <b>Bookmark saved!</b>\n\n<b>{scraped["title"]}</b>\n{scraped["domain"]}\n\n{preview}',
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


@restricted
async def list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with async_session() as db:
        # Get recent notes
        notes_result = await db.execute(
            select(Note)
            .where(Note.user_id == 1, Note.is_archived == False)
            .order_by(Note.created_at.desc())
            .limit(3)
        )
        notes = notes_result.scalars().all()

        # Get recent bookmarks
        bookmarks_result = await db.execute(
            select(Bookmark)
            .where(Bookmark.user_id == 1, Bookmark.is_archived == False)
            .order_by(Bookmark.captured_at.desc())
            .limit(3)
        )
        bookmarks = bookmarks_result.scalars().all()

    lines = ["<b>Recent Items:</b>\n"]

    if notes:
        lines.append("<b>📝 Notes:</b>")
        for n in notes:
            preview = n.content[:80].replace("\n", " ")
            lines.append(f"  • {preview}...")

    if bookmarks:
        lines.append("\n<b>🔗 Bookmarks:</b>")
        for b in bookmarks:
            lines.append(f"  • {b.title or b.source_domain}")

    if not notes and not bookmarks:
        lines.append("No items yet. Use /add or /bookmark to get started!")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


@restricted
async def tags_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with async_session() as db:
        result = await db.execute(
            select(Tag, func.count(TagAssignment.id).label("count"))
            .outerjoin(TagAssignment, Tag.id == TagAssignment.tag_id)
            .where(Tag.user_id == 1)
            .group_by(Tag.id)
            .order_by(func.count(TagAssignment.id).desc())
        )
        tags = result.all()

    if not tags:
        await update.message.reply_text("No tags yet. Tags are created when you add them to notes.")
        return

    tag_lines = [f"#{t[0].name} ({t[1]})" for t in tags]
    await update.message.reply_text(
        f"<b>Your tags ({len(tags)} total):</b>\n" + ", ".join(tag_lines),
        parse_mode=ParseMode.HTML,
    )


@restricted
async def settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from app.models import User

    async with async_session() as db:
        result = await db.execute(select(User).where(User.id == 1))
        user = result.scalar_one_or_none()
        pref = user.llm_preference if user else "haiku"

    other = "sonnet" if pref == "haiku" else "haiku"
    keyboard = [
        [InlineKeyboardButton(f"Switch to {other.title()}", callback_data=f"set_llm:{other}")],
    ]
    await update.message.reply_text(
        f"<b>Settings:</b>\n\nLLM Model: <b>{pref.title()}</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


@restricted
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data or ""

    if data.startswith("set_llm:"):
        from app.models import User

        new_pref = data.split(":")[1]
        async with async_session() as db:
            result = await db.execute(select(User).where(User.id == 1))
            user = result.scalar_one_or_none()
            if user:
                user.llm_preference = new_pref
                await db.commit()

        other = "sonnet" if new_pref == "haiku" else "haiku"
        keyboard = [
            [InlineKeyboardButton(f"Switch to {other.title()}", callback_data=f"set_llm:{other}")],
        ]
        await query.edit_message_text(
            f"<b>Settings:</b>\n\nLLM Model: <b>{new_pref.title()}</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif data.startswith("sonnet:"):
        search_query = data[7:]
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action=ChatAction.TYPING
        )

        async with async_session() as db:
            result = await search_and_answer(db, search_query, limit=5, llm_model="sonnet")

        answer = truncate(result["answer"])
        await query.edit_message_text(
            f"<b>[Sonnet]</b>\n\n{answer}",
            parse_mode=ParseMode.HTML,
        )

    elif data.startswith("add_tags:") or data.startswith("add_tags_b:"):
        await query.edit_message_text(
            query.message.text + "\n\n<i>Reply to this message with comma-separated tags</i>",
            parse_mode=ParseMode.HTML,
        )


@restricted
async def auto_url_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Auto-detect URLs in plain messages and treat as bookmarks."""
    if not update.message or not update.message.entities:
        return

    for entity in update.message.entities:
        if entity.type == "url":
            url = update.message.text[entity.offset : entity.offset + entity.length]
            context.args = [url]
            await bookmark_handler(update, context)
            return


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Telegram bot error: %s", context.error, exc_info=context.error)
