from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Note, Tag, TagAssignment
from app.schemas import NoteCreate, NoteListResponse, NoteResponse, NoteUpdate, TagResponse
from app.services.embedding_service import create_chunks_and_embeddings
from app.utils.wiki_helpers import mark_wiki_pages_stale

router = APIRouter()


async def _get_note_tags(db: AsyncSession, note_id: int) -> list[TagResponse]:
    result = await db.execute(
        select(Tag)
        .join(TagAssignment, Tag.id == TagAssignment.tag_id)
        .where(TagAssignment.source_type == "note", TagAssignment.source_id == note_id)
    )
    return [TagResponse.model_validate(t) for t in result.scalars().all()]


@router.post("", response_model=NoteResponse, status_code=201)
async def create_note(note_in: NoteCreate, db: AsyncSession = Depends(get_db)):
    note = Note(
        content=note_in.content,
        markdown_content=note_in.markdown_content or note_in.content,
        source=note_in.source,
    )
    db.add(note)
    await db.flush()

    # Handle tags
    for tag_name in note_in.tags:
        tag_name = tag_name.strip().lower()
        result = await db.execute(select(Tag).where(Tag.name == tag_name, Tag.user_id == 1))
        tag = result.scalar_one_or_none()
        if not tag:
            tag = Tag(name=tag_name)
            db.add(tag)
            await db.flush()
        db.add(TagAssignment(tag_id=tag.id, source_type="note", source_id=note.id))

    await db.flush()

    # Chunk and embed
    await create_chunks_and_embeddings(db, "note", note.id, note.content)

    tags = await _get_note_tags(db, note.id)
    return NoteResponse(
        id=note.id,
        content=note.content,
        markdown_content=note.markdown_content,
        created_at=note.created_at,
        updated_at=note.updated_at,
        source=note.source,
        is_archived=note.is_archived,
        tags=tags,
    )


@router.get("", response_model=NoteListResponse)
async def list_notes(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    archived: bool = False,
    tag: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Note).where(Note.user_id == 1, Note.is_archived == archived)

    if tag:
        query = query.join(
            TagAssignment,
            (TagAssignment.source_type == "note") & (TagAssignment.source_id == Note.id),
        ).join(Tag).where(Tag.name == tag.lower())

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Fetch
    query = query.order_by(Note.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    notes = result.scalars().all()

    note_responses = []
    for n in notes:
        tags = await _get_note_tags(db, n.id)
        note_responses.append(
            NoteResponse(
                id=n.id,
                content=n.content,
                markdown_content=n.markdown_content,
                created_at=n.created_at,
                updated_at=n.updated_at,
                source=n.source,
                is_archived=n.is_archived,
                tags=tags,
            )
        )

    return NoteListResponse(notes=note_responses, total=total)


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(note_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Note).where(Note.id == note_id, Note.user_id == 1))
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    tags = await _get_note_tags(db, note.id)
    return NoteResponse(
        id=note.id,
        content=note.content,
        markdown_content=note.markdown_content,
        created_at=note.created_at,
        updated_at=note.updated_at,
        source=note.source,
        is_archived=note.is_archived,
        tags=tags,
    )


@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(note_id: int, note_in: NoteUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Note).where(Note.id == note_id, Note.user_id == 1))
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if note_in.content is not None:
        note.content = note_in.content
    if note_in.markdown_content is not None:
        note.markdown_content = note_in.markdown_content

    note.updated_at = datetime.now(timezone.utc)
    await db.flush()

    # Re-chunk and re-embed if content changed
    if note_in.content is not None:
        await create_chunks_and_embeddings(db, "note", note.id, note.content)
        await mark_wiki_pages_stale(db, "note", note.id)

    tags = await _get_note_tags(db, note.id)
    return NoteResponse(
        id=note.id,
        content=note.content,
        markdown_content=note.markdown_content,
        created_at=note.created_at,
        updated_at=note.updated_at,
        source=note.source,
        is_archived=note.is_archived,
        tags=tags,
    )


@router.delete("/{note_id}", status_code=204)
async def delete_note(
    note_id: int, hard: bool = False, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Note).where(Note.id == note_id, Note.user_id == 1))
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if hard:
        await db.delete(note)
    else:
        note.is_archived = True

    await db.flush()
