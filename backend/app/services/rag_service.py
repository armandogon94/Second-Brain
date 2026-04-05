from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.embedding_service import embed_single
from app.services.llm_service import generate_answer
from app.utils.logger import logger


async def hybrid_search(
    db: AsyncSession,
    query: str,
    limit: int = 10,
    user_id: int = 1,
) -> list[dict]:
    """Perform hybrid search combining semantic + full-text with RRF."""
    # Embed the query
    try:
        query_vector = await embed_single(query)
    except Exception:
        logger.exception("Failed to embed query")
        query_vector = None

    k = settings.rrf_k
    over_fetch = limit * 2

    results: list[dict] = []

    if query_vector:
        # Hybrid search with RRF in a single query
        vector_str = "[" + ",".join(str(v) for v in query_vector) + "]"

        rrf_query = text("""
            SELECT chunk_id, content, source_type, source_id, score, title FROM (
                SELECT
                    searches.chunk_id,
                    searches.content,
                    searches.source_type,
                    searches.source_id,
                    SUM(1.0 / (:k + searches.rank)) AS score,
                    searches.title
                FROM (
                    -- Semantic search
                    (SELECT
                        c.id AS chunk_id,
                        c.content,
                        c.source_type,
                        c.source_id,
                        RANK() OVER (ORDER BY e.embedding <=> :query_vec::vector) AS rank,
                        COALESCE(
                            CASE c.source_type
                                WHEN 'note' THEN (SELECT LEFT(n.content, 100) FROM notes n WHERE n.id = c.source_id)
                                WHEN 'bookmark' THEN (SELECT b.title FROM bookmarks b WHERE b.id = c.source_id)
                                WHEN 'pdf' THEN (SELECT p.filename FROM pdfs p WHERE p.id = c.source_id)
                            END,
                            c.source_type || ':' || c.source_id::text
                        ) AS title
                    FROM chunks c
                    JOIN embeddings e ON c.id = e.chunk_id
                    WHERE c.user_id = :user_id
                    ORDER BY e.embedding <=> :query_vec::vector
                    LIMIT :over_fetch)

                    UNION ALL

                    -- Full-text search
                    (SELECT
                        c.id AS chunk_id,
                        c.content,
                        c.source_type,
                        c.source_id,
                        RANK() OVER (ORDER BY ts_rank_cd(c.search_vector,
                            plainto_tsquery('english', :query_text)) DESC) AS rank,
                        COALESCE(
                            CASE c.source_type
                                WHEN 'note' THEN (SELECT LEFT(n.content, 100) FROM notes n WHERE n.id = c.source_id)
                                WHEN 'bookmark' THEN (SELECT b.title FROM bookmarks b WHERE b.id = c.source_id)
                                WHEN 'pdf' THEN (SELECT p.filename FROM pdfs p WHERE p.id = c.source_id)
                            END,
                            c.source_type || ':' || c.source_id::text
                        ) AS title
                    FROM chunks c
                    WHERE c.user_id = :user_id
                        AND c.search_vector @@ plainto_tsquery('english', :query_text)
                    ORDER BY ts_rank_cd(c.search_vector,
                        plainto_tsquery('english', :query_text)) DESC
                    LIMIT :over_fetch)
                ) searches
                GROUP BY searches.chunk_id, searches.content,
                         searches.source_type, searches.source_id, searches.title
                ORDER BY score DESC
                LIMIT :limit
            ) ranked
        """)

        result = await db.execute(
            rrf_query,
            {
                "k": k,
                "query_vec": vector_str,
                "query_text": query,
                "user_id": user_id,
                "over_fetch": over_fetch,
                "limit": limit,
            },
        )

        for row in result:
            results.append(
                {
                    "chunk_id": row.chunk_id,
                    "content": row.content,
                    "source_type": row.source_type,
                    "source_id": row.source_id,
                    "score": float(row.score),
                    "title": row.title,
                }
            )
    else:
        # Fallback to full-text only
        fts_query = text("""
            SELECT
                c.id AS chunk_id,
                c.content,
                c.source_type,
                c.source_id,
                ts_rank_cd(c.search_vector, plainto_tsquery('english', :query_text)) AS score,
                COALESCE(
                    CASE c.source_type
                        WHEN 'note' THEN (SELECT LEFT(n.content, 100) FROM notes n WHERE n.id = c.source_id)
                        WHEN 'bookmark' THEN (SELECT b.title FROM bookmarks b WHERE b.id = c.source_id)
                        WHEN 'pdf' THEN (SELECT p.filename FROM pdfs p WHERE p.id = c.source_id)
                    END,
                    c.source_type || ':' || c.source_id::text
                ) AS title
            FROM chunks c
            WHERE c.user_id = :user_id
                AND c.search_vector @@ plainto_tsquery('english', :query_text)
            ORDER BY score DESC
            LIMIT :limit
        """)

        result = await db.execute(
            fts_query, {"query_text": query, "user_id": user_id, "limit": limit}
        )
        for row in result:
            results.append(
                {
                    "chunk_id": row.chunk_id,
                    "content": row.content,
                    "source_type": row.source_type,
                    "source_id": row.source_id,
                    "score": float(row.score),
                    "title": row.title,
                }
            )

    return results


async def search_and_answer(
    db: AsyncSession,
    query: str,
    limit: int = 10,
    llm_model: str = "haiku",
    user_id: int = 1,
) -> dict:
    """Full RAG pipeline: search → retrieve → generate answer."""
    chunks = await hybrid_search(db, query, limit=limit, user_id=user_id)

    if not chunks:
        return {
            "answer": "I didn't find anything relevant in your notes for this query.",
            "sources": [],
            "usage": {},
        }

    # Check if best result meets similarity threshold
    best_score = chunks[0]["score"] if chunks else 0
    if best_score < settings.similarity_threshold:
        logger.info("Best score %.4f below threshold %.4f", best_score, settings.similarity_threshold)

    # Generate answer
    result = await generate_answer(query, chunks, model_key=llm_model)

    sources = [
        {
            "source_type": c["source_type"],
            "source_id": c["source_id"],
            "title": c["title"],
            "content_preview": c["content"][:200],
            "score": c["score"],
            "chunk_id": c["chunk_id"],
        }
        for c in chunks
    ]

    return {
        "answer": result["answer"],
        "sources": sources,
        "usage": result["usage"],
    }
