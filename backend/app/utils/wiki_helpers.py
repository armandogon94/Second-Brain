"""Wiki helper functions: slug generation, wikilink parsing, content hashing, staleness."""

import hashlib
import re
from unicodedata import normalize

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

WIKILINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")


def slugify(title: str) -> str:
    """Convert a title to a URL-safe slug.

    'Machine Learning Basics' -> 'machine-learning-basics'
    """
    slug = normalize("NFKD", title).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^\w\s-]", "", slug).strip().lower()
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug or "untitled"


def extract_wikilinks(markdown: str) -> list[str]:
    """Extract all [[wikilink]] targets from markdown content."""
    return WIKILINK_PATTERN.findall(markdown)


def content_hash(text: str) -> str:
    """SHA-256 hash of text content for change detection."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def mark_wiki_pages_stale(
    db: AsyncSession, source_type: str, source_id: int
) -> int:
    """Mark wiki pages as stale when a source they cite is updated.

    Returns the number of pages marked stale.
    """
    from app.models import WikiPage, WikiSource

    # Find wiki pages that cite this source
    subq = select(WikiSource.wiki_page_id).where(
        WikiSource.source_type == source_type,
        WikiSource.source_id == source_id,
    )
    stmt = (
        update(WikiPage)
        .where(WikiPage.id.in_(subq))
        .values(is_stale=True)
    )
    result = await db.execute(stmt)
    return result.rowcount
