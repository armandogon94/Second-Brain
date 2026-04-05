from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import RawSearchRequest, RawSearchResponse, SearchRequest, SearchResponse
from app.services.rag_service import hybrid_search, search_and_answer

router = APIRouter()


@router.post("", response_model=SearchResponse)
async def search(request: SearchRequest, db: AsyncSession = Depends(get_db)):
    result = await search_and_answer(
        db,
        query=request.query,
        limit=request.limit,
        llm_model=request.llm_model,
    )
    return SearchResponse(**result)


@router.post("/raw", response_model=RawSearchResponse)
async def raw_search(request: RawSearchRequest, db: AsyncSession = Depends(get_db)):
    chunks = await hybrid_search(
        db,
        query=request.query,
        limit=request.limit,
    )

    sources = [
        {
            "source_type": c["source_type"],
            "source_id": c["source_id"],
            "title": c["title"],
            "content_preview": c["content"][:200],
            "score": c["score"] if request.include_scores else 0.0,
            "chunk_id": c["chunk_id"],
        }
        for c in chunks
    ]

    return RawSearchResponse(chunks=sources, total=len(sources))
