import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import Pdf, Tag, TagAssignment
from app.schemas import PdfListResponse, PdfResponse, TagResponse
from app.services.embedding_service import create_chunks_and_embeddings
from app.services.pdf_service import extract_pdf_text

router = APIRouter()


async def _get_pdf_tags(db: AsyncSession, pdf_id: int) -> list[TagResponse]:
    result = await db.execute(
        select(Tag)
        .join(TagAssignment, Tag.id == TagAssignment.tag_id)
        .where(TagAssignment.source_type == "pdf", TagAssignment.source_id == pdf_id)
    )
    return [TagResponse.model_validate(t) for t in result.scalars().all()]


@router.post("/upload", response_model=PdfResponse, status_code=201)
async def upload_pdf(file: UploadFile, db: AsyncSession = Depends(get_db)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    if file.content_type and file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid content type")

    # Read file
    content = await file.read()
    if len(content) > settings.max_file_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.max_file_size // (1024*1024)}MB",
        )

    # Save to disk with unique name
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = upload_dir / safe_name

    with open(file_path, "wb") as f:
        f.write(content)

    # Extract text
    try:
        extracted = await extract_pdf_text(str(file_path))
    except Exception as e:
        os.unlink(file_path)
        raise HTTPException(status_code=422, detail=f"Could not extract PDF text: {e}")

    pdf = Pdf(
        filename=file.filename,
        file_path=str(file_path),
        extracted_text=extracted["text"],
        page_count=extracted["page_count"],
        file_size=len(content),
    )
    db.add(pdf)
    await db.flush()

    # Chunk and embed
    if extracted["text"]:
        await create_chunks_and_embeddings(db, "pdf", pdf.id, extracted["text"])

    tags = await _get_pdf_tags(db, pdf.id)
    return PdfResponse(
        id=pdf.id,
        filename=pdf.filename,
        file_path=pdf.file_path,
        extracted_text=pdf.extracted_text,
        page_count=pdf.page_count,
        file_size=pdf.file_size,
        uploaded_at=pdf.uploaded_at,
        is_archived=pdf.is_archived,
        tags=tags,
    )


@router.get("", response_model=PdfListResponse)
async def list_pdfs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    archived: bool = False,
    db: AsyncSession = Depends(get_db),
):
    query = select(Pdf).where(Pdf.user_id == 1, Pdf.is_archived == archived)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.order_by(Pdf.uploaded_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    pdfs = result.scalars().all()

    responses = []
    for p in pdfs:
        tags = await _get_pdf_tags(db, p.id)
        responses.append(
            PdfResponse(
                id=p.id,
                filename=p.filename,
                file_path=p.file_path,
                extracted_text=p.extracted_text,
                page_count=p.page_count,
                file_size=p.file_size,
                uploaded_at=p.uploaded_at,
                is_archived=p.is_archived,
                tags=tags,
            )
        )

    return PdfListResponse(pdfs=responses, total=total)


@router.get("/{pdf_id}", response_model=PdfResponse)
async def get_pdf(pdf_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Pdf).where(Pdf.id == pdf_id, Pdf.user_id == 1))
    pdf = result.scalar_one_or_none()
    if not pdf:
        raise HTTPException(status_code=404, detail="PDF not found")

    tags = await _get_pdf_tags(db, pdf.id)
    return PdfResponse(
        id=pdf.id,
        filename=pdf.filename,
        file_path=pdf.file_path,
        extracted_text=pdf.extracted_text,
        page_count=pdf.page_count,
        file_size=pdf.file_size,
        uploaded_at=pdf.uploaded_at,
        is_archived=pdf.is_archived,
        tags=tags,
    )


@router.delete("/{pdf_id}", status_code=204)
async def delete_pdf(
    pdf_id: int, hard: bool = False, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Pdf).where(Pdf.id == pdf_id, Pdf.user_id == 1))
    pdf = result.scalar_one_or_none()
    if not pdf:
        raise HTTPException(status_code=404, detail="PDF not found")

    if hard:
        # Delete file from disk
        try:
            os.unlink(pdf.file_path)
        except OSError:
            pass
        await db.delete(pdf)
    else:
        pdf.is_archived = True

    await db.flush()
