from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Chunk, Embedding
from app.services.chunking_service import chunk_text
from app.utils.logger import logger

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts using OpenAI's embedding model."""
    if not texts:
        return []
    client = _get_client()
    response = await client.embeddings.create(
        input=texts,
        model=settings.embedding_model,
    )
    return [item.embedding for item in response.data]


async def embed_single(text: str) -> list[float]:
    """Embed a single text."""
    result = await embed_texts([text])
    return result[0]


async def create_chunks_and_embeddings(
    db: AsyncSession,
    source_type: str,
    source_id: int,
    text: str,
    user_id: int = 1,
) -> list[Chunk]:
    """Chunk text, create chunk records, and embed them."""
    # Delete existing chunks for this source
    existing = await db.execute(
        select(Chunk).where(
            Chunk.source_type == source_type,
            Chunk.source_id == source_id,
        )
    )
    for chunk in existing.scalars().all():
        await db.delete(chunk)
    await db.flush()

    # Chunk the text
    chunk_dicts = chunk_text(text)
    if not chunk_dicts:
        return []

    # Create chunk records
    chunks: list[Chunk] = []
    for i, cd in enumerate(chunk_dicts):
        chunk = Chunk(
            user_id=user_id,
            source_type=source_type,
            source_id=source_id,
            chunk_index=i,
            content=cd["content"],
            character_count=cd["character_count"],
            token_count=cd["token_count"],
        )
        db.add(chunk)
        chunks.append(chunk)

    await db.flush()

    # Embed all chunks in batch
    texts_to_embed = [c.content for c in chunks]
    try:
        vectors = await embed_texts(texts_to_embed)
    except Exception:
        logger.exception("Failed to embed chunks for %s:%d", source_type, source_id)
        return chunks

    # Create embedding records
    for chunk, vector in zip(chunks, vectors):
        emb = Embedding(
            chunk_id=chunk.id,
            embedding=vector,
            embedding_model=settings.embedding_model,
        )
        db.add(emb)

    await db.flush()
    logger.info(
        "Created %d chunks and embeddings for %s:%d", len(chunks), source_type, source_id
    )
    return chunks
