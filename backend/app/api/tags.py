from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Tag, TagAssignment
from app.schemas import TagCreate, TagWithCount

router = APIRouter()


@router.get("", response_model=list[TagWithCount])
async def list_tags(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            Tag,
            func.count(TagAssignment.id).label("count"),
        )
        .outerjoin(TagAssignment, Tag.id == TagAssignment.tag_id)
        .where(Tag.user_id == 1)
        .group_by(Tag.id)
        .order_by(Tag.name)
    )

    tags = []
    for row in result:
        tag = row[0]
        count = row[1]
        tags.append(
            TagWithCount(
                id=tag.id,
                name=tag.name,
                color=tag.color,
                created_at=tag.created_at,
                count=count,
            )
        )

    return tags


@router.post("", response_model=TagWithCount, status_code=201)
async def create_tag(tag_in: TagCreate, db: AsyncSession = Depends(get_db)):
    name = tag_in.name.strip().lower()

    existing = await db.execute(select(Tag).where(Tag.name == name, Tag.user_id == 1))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Tag already exists")

    tag = Tag(name=name, color=tag_in.color)
    db.add(tag)
    await db.flush()

    return TagWithCount(
        id=tag.id,
        name=tag.name,
        color=tag.color,
        created_at=tag.created_at,
        count=0,
    )


@router.delete("/{tag_id}", status_code=204)
async def delete_tag(tag_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tag).where(Tag.id == tag_id, Tag.user_id == 1))
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    await db.delete(tag)
    await db.flush()
