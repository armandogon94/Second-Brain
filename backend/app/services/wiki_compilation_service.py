"""Wiki compilation service — gathers sources, calls LLM, creates/updates wiki pages."""

import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Bookmark, CompilationLog, Note, Pdf, WikiPage, WikiSource
from app.services.llm_service import MODEL_MAP, _get_client
from app.utils.logger import logger
from app.utils.wiki_helpers import content_hash, extract_wikilinks, slugify


async def gather_uncompiled_sources(
    db: AsyncSession, *, user_id: int = 1, force: bool = False
) -> list[dict]:
    """Find raw sources (notes, bookmarks, PDFs) not yet compiled into wiki pages.

    If force=True, returns ALL sources regardless of compilation status.
    """
    sources: list[dict] = []

    # Subquery: source IDs already in wiki_sources
    compiled_note_ids = select(WikiSource.source_id).where(
        WikiSource.source_type == "note"
    )
    compiled_bookmark_ids = select(WikiSource.source_id).where(
        WikiSource.source_type == "bookmark"
    )
    compiled_pdf_ids = select(WikiSource.source_id).where(
        WikiSource.source_type == "pdf"
    )

    # Notes
    q = select(Note).where(Note.user_id == user_id, Note.is_archived == False)  # noqa: E712
    if not force:
        q = q.where(Note.id.not_in(compiled_note_ids))
    result = await db.execute(q)
    for note in result.scalars().all():
        sources.append({
            "source_type": "note",
            "source_id": note.id,
            "title": f"Note #{note.id}",
            "content": note.content,
        })

    # Bookmarks
    q = select(Bookmark).where(Bookmark.user_id == user_id, Bookmark.is_archived == False)  # noqa: E712
    if not force:
        q = q.where(Bookmark.id.not_in(compiled_bookmark_ids))
    result = await db.execute(q)
    for bm in result.scalars().all():
        if bm.scraped_content:
            sources.append({
                "source_type": "bookmark",
                "source_id": bm.id,
                "title": bm.title or bm.original_url,
                "content": bm.scraped_content,
            })

    # PDFs
    q = select(Pdf).where(Pdf.user_id == user_id, Pdf.is_archived == False)  # noqa: E712
    if not force:
        q = q.where(Pdf.id.not_in(compiled_pdf_ids))
    result = await db.execute(q)
    for pdf in result.scalars().all():
        if pdf.extracted_text:
            sources.append({
                "source_type": "pdf",
                "source_id": pdf.id,
                "title": pdf.filename,
                "content": pdf.extracted_text,
            })

    return sources


async def generate_wiki_page(
    sources: list[dict], model: str = "haiku"
) -> dict:
    """Call LLM to compile sources into a wiki page.

    Returns dict with 'answer' (markdown with frontmatter) and 'usage'.
    """
    client = _get_client()
    model_id = MODEL_MAP.get(model, MODEL_MAP["haiku"])

    source_texts = []
    for s in sources:
        source_texts.append(
            f"[{s['source_type']}:{s['source_id']} — \"{s['title']}\"]\n{s['content']}"
        )
    context = "\n\n---\n\n".join(source_texts)

    system_prompt = (
        "You are a knowledge compiler. Given raw source materials, produce a single "
        "wiki page in Markdown with YAML frontmatter.\n\n"
        "FORMAT:\n"
        "---\n"
        "title: <descriptive title>\n"
        "type: <concept|person|project|howto|reference|index|log>\n"
        "confidence: <0.0-1.0 based on source quality/coverage>\n"
        "---\n\n"
        "<markdown content>\n\n"
        "RULES:\n"
        "1. Use [[wikilinks]] for cross-references to related concepts.\n"
        "2. Synthesize, don't just concatenate sources.\n"
        "3. Organize with clear headers and structure.\n"
        "4. Be concise but thorough.\n"
        "5. Set confidence based on how well the sources cover the topic."
    )

    user_prompt = (
        f"Compile the following {len(sources)} source(s) into a wiki page:\n\n"
        f"{context}"
    )

    try:
        response = await client.messages.create(
            model=model_id,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return {
            "answer": response.content[0].text,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "model": model_id,
            },
        }
    except Exception:
        logger.exception("Wiki compilation LLM call failed")
        return {"answer": "", "usage": {}}


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from compiled markdown.

    Returns (frontmatter_dict, content_body).
    """
    fm: dict = {}
    body = text

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
    if match:
        fm_text, body = match.group(1), match.group(2)
        for line in fm_text.strip().split("\n"):
            if ":" in line:
                key, _, value = line.partition(":")
                value = value.strip()
                if key.strip() == "confidence":
                    try:
                        fm[key.strip()] = float(value)
                    except ValueError:
                        fm[key.strip()] = value
                else:
                    fm[key.strip()] = value

    return fm, body.strip()


async def compile_wiki(
    db: AsyncSession,
    *,
    user_id: int = 1,
    model: str = "haiku",
    force: bool = False,
    source_ids: list[int] | None = None,
) -> int:
    """Run the full compilation pipeline. Returns the compilation log ID."""
    log = CompilationLog(
        user_id=user_id,
        action="compile",
        status="running",
    )
    db.add(log)
    await db.flush()

    try:
        sources = await gather_uncompiled_sources(db, user_id=user_id, force=force)

        if source_ids:
            sources = [s for s in sources if s["source_id"] in source_ids]

        if not sources:
            log.status = "success"
            log.sources_processed = 0
            log.completed_at = datetime.now(timezone.utc)
            log.details = {"message": "No new sources to compile"}
            await db.flush()
            return log.id

        # For simplicity, compile all sources into one page per batch
        # A production version would cluster by topic first
        result = await generate_wiki_page(sources, model=model)

        if not result["answer"]:
            log.status = "failed"
            log.error_message = "LLM returned empty response"
            log.completed_at = datetime.now(timezone.utc)
            await db.flush()
            return log.id

        fm, content = parse_frontmatter(result["answer"])
        title = fm.get("title", "Untitled")
        page_type = fm.get("type", "concept")
        confidence = fm.get("confidence", 0.8)
        if isinstance(confidence, str):
            try:
                confidence = float(confidence)
            except ValueError:
                confidence = 0.8

        slug = slugify(title)

        # Check for existing page with same slug
        existing = await db.execute(
            select(WikiPage).where(WikiPage.user_id == user_id, WikiPage.slug == slug)
        )
        page = existing.scalar_one_or_none()

        pages_created = 0
        pages_updated = 0

        if page:
            page.content_markdown = content
            page.frontmatter = fm
            page.confidence = confidence
            page.is_stale = False
            page.version += 1
            page.compiled_at = datetime.now(timezone.utc)
            page.updated_at = datetime.now(timezone.utc)
            pages_updated = 1
        else:
            page = WikiPage(
                user_id=user_id,
                slug=slug,
                title=title,
                page_type=page_type,
                content_markdown=content,
                frontmatter=fm,
                confidence=confidence,
                compiled_at=datetime.now(timezone.utc),
            )
            db.add(page)
            pages_created = 1

        await db.flush()

        # Record sources
        for s in sources:
            ws = WikiSource(
                wiki_page_id=page.id,
                source_type=s["source_type"],
                source_id=s["source_id"],
                source_hash=content_hash(s["content"]),
                compiled_at=datetime.now(timezone.utc),
            )
            db.add(ws)

        await db.flush()

        log.status = "success"
        log.sources_processed = len(sources)
        log.pages_created = pages_created
        log.pages_updated = pages_updated
        log.token_usage = result.get("usage", {})
        log.completed_at = datetime.now(timezone.utc)
        await db.flush()

    except Exception as e:
        logger.exception("Compilation failed")
        log.status = "failed"
        log.error_message = str(e)
        log.completed_at = datetime.now(timezone.utc)
        await db.flush()

    return log.id
