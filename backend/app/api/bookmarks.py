from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Bookmark, Tag, TagAssignment
from app.schemas import (
    BookmarkCreate,
    BookmarkListResponse,
    BookmarkResponse,
    BookmarkUpdate,
    TagResponse,
)
from app.services.embedding_service import create_chunks_and_embeddings
from app.services.scraping_service import scrape_url

router = APIRouter()


async def _get_bookmark_tags(db: AsyncSession, bookmark_id: int) -> list[TagResponse]:
    result = await db.execute(
        select(Tag)
        .join(TagAssignment, Tag.id == TagAssignment.tag_id)
        .where(TagAssignment.source_type == "bookmark", TagAssignment.source_id == bookmark_id)
    )
    return [TagResponse.model_validate(t) for t in result.scalars().all()]


@router.post("", response_model=BookmarkResponse, status_code=201)
async def create_bookmark(bookmark_in: BookmarkCreate, db: AsyncSession = Depends(get_db)):
    url = str(bookmark_in.url)

    # Check for duplicate
    existing = await db.execute(
        select(Bookmark).where(Bookmark.original_url == url, Bookmark.user_id == 1)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Bookmark already exists for this URL")

    # Scrape
    try:
        scraped = await scrape_url(url)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Could not extract content from URL: {e}",
        )

    bookmark = Bookmark(
        original_url=url,
        title=scraped["title"],
        scraped_content=scraped["content"],
        source_domain=scraped["domain"],
    )
    db.add(bookmark)
    await db.flush()

    # Handle tags
    for tag_name in bookmark_in.tags:
        tag_name = tag_name.strip().lower()
        result = await db.execute(select(Tag).where(Tag.name == tag_name, Tag.user_id == 1))
        tag = result.scalar_one_or_none()
        if not tag:
            tag = Tag(name=tag_name)
            db.add(tag)
            await db.flush()
        db.add(TagAssignment(tag_id=tag.id, source_type="bookmark", source_id=bookmark.id))

    await db.flush()

    # Chunk and embed
    if scraped["content"]:
        await create_chunks_and_embeddings(db, "bookmark", bookmark.id, scraped["content"])

    tags = await _get_bookmark_tags(db, bookmark.id)
    return BookmarkResponse(
        id=bookmark.id,
        original_url=bookmark.original_url,
        title=bookmark.title,
        scraped_content=bookmark.scraped_content,
        source_domain=bookmark.source_domain,
        captured_at=bookmark.captured_at,
        is_read=bookmark.is_read,
        is_archived=bookmark.is_archived,
        tags=tags,
    )


@router.get("", response_model=BookmarkListResponse)
async def list_bookmarks(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    archived: bool = False,
    is_read: bool | None = None,
    tag: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Bookmark).where(Bookmark.user_id == 1, Bookmark.is_archived == archived)

    if is_read is not None:
        query = query.where(Bookmark.is_read == is_read)

    if tag:
        query = query.join(
            TagAssignment,
            (TagAssignment.source_type == "bookmark")
            & (TagAssignment.source_id == Bookmark.id),
        ).join(Tag).where(Tag.name == tag.lower())

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.order_by(Bookmark.captured_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    bookmarks = result.scalars().all()

    responses = []
    for b in bookmarks:
        tags = await _get_bookmark_tags(db, b.id)
        responses.append(
            BookmarkResponse(
                id=b.id,
                original_url=b.original_url,
                title=b.title,
                scraped_content=b.scraped_content,
                source_domain=b.source_domain,
                captured_at=b.captured_at,
                is_read=b.is_read,
                is_archived=b.is_archived,
                tags=tags,
            )
        )

    return BookmarkListResponse(bookmarks=responses, total=total)


@router.get("/{bookmark_id}", response_model=BookmarkResponse)
async def get_bookmark(bookmark_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Bookmark).where(Bookmark.id == bookmark_id, Bookmark.user_id == 1)
    )
    bookmark = result.scalar_one_or_none()
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    tags = await _get_bookmark_tags(db, bookmark.id)
    return BookmarkResponse(
        id=bookmark.id,
        original_url=bookmark.original_url,
        title=bookmark.title,
        scraped_content=bookmark.scraped_content,
        source_domain=bookmark.source_domain,
        captured_at=bookmark.captured_at,
        is_read=bookmark.is_read,
        is_archived=bookmark.is_archived,
        tags=tags,
    )


@router.put("/{bookmark_id}", response_model=BookmarkResponse)
async def update_bookmark(
    bookmark_id: int, update: BookmarkUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Bookmark).where(Bookmark.id == bookmark_id, Bookmark.user_id == 1)
    )
    bookmark = result.scalar_one_or_none()
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    if update.is_read is not None:
        bookmark.is_read = update.is_read

    await db.flush()

    tags = await _get_bookmark_tags(db, bookmark.id)
    return BookmarkResponse(
        id=bookmark.id,
        original_url=bookmark.original_url,
        title=bookmark.title,
        scraped_content=bookmark.scraped_content,
        source_domain=bookmark.source_domain,
        captured_at=bookmark.captured_at,
        is_read=bookmark.is_read,
        is_archived=bookmark.is_archived,
        tags=tags,
    )


@router.delete("/{bookmark_id}", status_code=204)
async def delete_bookmark(
    bookmark_id: int, hard: bool = False, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Bookmark).where(Bookmark.id == bookmark_id, Bookmark.user_id == 1)
    )
    bookmark = result.scalar_one_or_none()
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    if hard:
        await db.delete(bookmark)
    else:
        bookmark.is_archived = True

    await db.flush()
