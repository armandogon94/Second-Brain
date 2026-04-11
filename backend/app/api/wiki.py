"""Wiki CRUD API — pages with slug routing, wikilink parsing, backlinks."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import WikiLink, WikiPage, WikiSource
from app.schemas import (
    WikiLinkRef,
    WikiPageCreate,
    WikiPageListResponse,
    WikiPageResponse,
    WikiPageUpdate,
    WikiSourceRef,
)
from app.utils.wiki_helpers import slugify

router = APIRouter()


async def _build_response(db: AsyncSession, page: WikiPage) -> WikiPageResponse:
    """Build a WikiPageResponse with backlinks and sources."""
    # Backlinks: pages that link TO this page
    backlink_q = (
        select(WikiPage.slug, WikiPage.title, WikiPage.page_type)
        .join(WikiLink, WikiLink.from_page_id == WikiPage.id)
        .where(WikiLink.to_page_id == page.id)
    )
    result = await db.execute(backlink_q)
    backlinks = [
        WikiLinkRef(slug=row.slug, title=row.title, page_type=row.page_type)
        for row in result.all()
    ]

    # Sources
    source_q = select(WikiSource).where(WikiSource.wiki_page_id == page.id)
    result = await db.execute(source_q)
    sources = [WikiSourceRef.model_validate(s) for s in result.scalars().all()]

    return WikiPageResponse(
        id=page.id,
        slug=page.slug,
        title=page.title,
        page_type=page.page_type,
        content_markdown=page.content_markdown,
        frontmatter=page.frontmatter,
        confidence=page.confidence,
        is_stale=page.is_stale,
        version=page.version,
        compiled_at=page.compiled_at,
        created_at=page.created_at,
        updated_at=page.updated_at,
        backlinks=backlinks,
        sources=sources,
    )


@router.post("", response_model=WikiPageResponse, status_code=201)
async def create_wiki_page(
    page_in: WikiPageCreate, db: AsyncSession = Depends(get_db)
):
    slug = slugify(page_in.title)

    # Check slug uniqueness
    existing = await db.execute(
        select(WikiPage).where(WikiPage.user_id == 1, WikiPage.slug == slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Page with slug '{slug}' already exists")

    page = WikiPage(
        user_id=1,
        slug=slug,
        title=page_in.title,
        page_type=page_in.page_type,
        content_markdown=page_in.content_markdown,
        frontmatter=page_in.frontmatter,
        confidence=page_in.confidence,
    )
    db.add(page)
    await db.flush()

    return await _build_response(db, page)


@router.get("", response_model=WikiPageListResponse)
async def list_wiki_pages(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    page_type: str | None = None,
    search: str | None = None,
    stale: bool | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(WikiPage).where(WikiPage.user_id == 1, WikiPage.is_published == True)  # noqa: E712

    if page_type:
        query = query.where(WikiPage.page_type == page_type)
    if stale is not None:
        query = query.where(WikiPage.is_stale == stale)
    if search:
        # Simple LIKE search for SQLite compatibility in tests
        pattern = f"%{search}%"
        query = query.where(
            WikiPage.title.ilike(pattern) | WikiPage.content_markdown.ilike(pattern)
        )

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Fetch
    query = query.order_by(WikiPage.updated_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    pages = result.scalars().all()

    page_responses = [await _build_response(db, p) for p in pages]
    return WikiPageListResponse(pages=page_responses, total=total)


@router.get("/{slug}", response_model=WikiPageResponse)
async def get_wiki_page(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WikiPage).where(WikiPage.user_id == 1, WikiPage.slug == slug)
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Wiki page not found")

    return await _build_response(db, page)


@router.put("/{slug}", response_model=WikiPageResponse)
async def update_wiki_page(
    slug: str, page_in: WikiPageUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(WikiPage).where(WikiPage.user_id == 1, WikiPage.slug == slug)
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Wiki page not found")

    if page_in.title is not None:
        page.title = page_in.title
        page.slug = slugify(page_in.title)
    if page_in.content_markdown is not None:
        page.content_markdown = page_in.content_markdown
    if page_in.page_type is not None:
        page.page_type = page_in.page_type
    if page_in.frontmatter is not None:
        page.frontmatter = page_in.frontmatter
    if page_in.confidence is not None:
        page.confidence = page_in.confidence
    if page_in.is_published is not None:
        page.is_published = page_in.is_published
    if page_in.is_stale is not None:
        page.is_stale = page_in.is_stale

    page.version += 1
    page.updated_at = datetime.now(timezone.utc)
    await db.flush()

    return await _build_response(db, page)


@router.delete("/{slug}", status_code=204)
async def delete_wiki_page(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WikiPage).where(WikiPage.user_id == 1, WikiPage.slug == slug)
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Wiki page not found")

    await db.delete(page)
    await db.flush()
