"""Tests for wiki compilation service and endpoints (Slice 4 — RED first)."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Bookmark, CompilationLog, Note, User, WikiPage, WikiSource


@pytest.fixture
async def seed_user(db_session):
    user = User(id=1, username="armando", llm_preference="haiku")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def seed_sources(db_session, seed_user):
    """Create some notes and bookmarks as raw sources."""
    notes = []
    for i, content in enumerate(
        [
            "Machine learning is a subset of AI that learns from data.",
            "Neural networks use layers of interconnected nodes.",
            "Python is great for data science and ML.",
        ]
    ):
        note = Note(user_id=1, content=content, source="web_ui")
        db_session.add(note)
        notes.append(note)

    bookmark = Bookmark(
        user_id=1,
        original_url="https://example.com/ml-guide",
        title="ML Guide",
        scraped_content="A comprehensive guide to machine learning algorithms.",
        source_domain="example.com",
    )
    db_session.add(bookmark)
    await db_session.flush()

    return {"notes": notes, "bookmark": bookmark}


MOCK_COMPILE_RESPONSE = {
    "answer": (
        "---\n"
        "title: Machine Learning\n"
        "type: concept\n"
        "confidence: 0.85\n"
        "---\n\n"
        "# Machine Learning\n\n"
        "Machine learning is a subset of AI. It uses [[Neural Networks]] "
        "and is commonly implemented in [[Python]].\n\n"
        "## Key Concepts\n"
        "- Supervised learning\n"
        "- Unsupervised learning\n"
    ),
    "usage": {"input_tokens": 500, "output_tokens": 200, "model": "claude-haiku-4-5-20251001"},
}


class TestCompileEndpoint:
    @pytest.mark.asyncio
    async def test_trigger_compile(self, client, seed_sources):
        """POST /wiki/compile should start compilation and return log_id."""
        with patch(
            "app.api.wiki_compile.run_compilation",
            new_callable=AsyncMock,
        ) as mock_compile:
            response = await client.post(
                "/api/v1/wiki/compile",
                json={"model": "haiku"},
            )
            assert response.status_code == 202
            data = response.json()
            assert "log_id" in data
            assert data["status"] == "running"

    @pytest.mark.asyncio
    async def test_compile_status(self, client, db_session, seed_user):
        """GET /wiki/compile/{log_id} should return compilation status."""
        log = CompilationLog(
            user_id=1,
            action="compile",
            status="success",
            sources_processed=3,
            pages_created=1,
            pages_updated=0,
            completed_at=datetime.now(timezone.utc),
        )
        db_session.add(log)
        await db_session.flush()

        response = await client.get(f"/api/v1/wiki/compile/{log.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["sources_processed"] == 3
        assert data["pages_created"] == 1

    @pytest.mark.asyncio
    async def test_compile_status_not_found(self, client, seed_user):
        response = await client.get("/api/v1/wiki/compile/9999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_compile_history(self, client, db_session, seed_user):
        """GET /wiki/compile/history should return past compilations."""
        for status in ["success", "success", "failed"]:
            log = CompilationLog(
                user_id=1, action="compile", status=status,
            )
            db_session.add(log)
        await db_session.flush()

        response = await client.get("/api/v1/wiki/compile/history")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3


class TestCompilationService:
    @pytest.mark.asyncio
    async def test_gather_uncompiled_sources(self, db_session, seed_sources):
        """Should find sources that have no wiki_sources entry."""
        from app.services.wiki_compilation_service import gather_uncompiled_sources

        sources = await gather_uncompiled_sources(db_session, user_id=1)
        # 3 notes + 1 bookmark = 4 uncompiled sources
        assert len(sources) == 4

    @pytest.mark.asyncio
    async def test_gather_skips_compiled_sources(self, db_session, seed_sources):
        """Sources already in wiki_sources should be skipped."""
        from app.services.wiki_compilation_service import gather_uncompiled_sources

        # Create a wiki page and mark note[0] as compiled
        page = WikiPage(
            user_id=1,
            slug="existing",
            title="Existing",
            page_type="concept",
            content_markdown="Already compiled.",
        )
        db_session.add(page)
        await db_session.flush()

        ws = WikiSource(
            wiki_page_id=page.id,
            source_type="note",
            source_id=seed_sources["notes"][0].id,
            source_hash="abc123",
        )
        db_session.add(ws)
        await db_session.flush()

        sources = await gather_uncompiled_sources(db_session, user_id=1)
        # Should exclude the already-compiled note
        assert len(sources) == 3

    @pytest.mark.asyncio
    async def test_compile_creates_log(self, db_session, seed_sources):
        """Compilation should create a CompilationLog entry."""
        from app.services.wiki_compilation_service import compile_wiki

        with patch(
            "app.services.wiki_compilation_service.generate_wiki_page",
            new_callable=AsyncMock,
            return_value=MOCK_COMPILE_RESPONSE,
        ):
            log_id = await compile_wiki(db_session, user_id=1, model="haiku")

        result = await db_session.execute(
            select(CompilationLog).where(CompilationLog.id == log_id)
        )
        log = result.scalar_one()
        assert log.action == "compile"
        assert log.status == "success"
        assert log.sources_processed > 0

    @pytest.mark.asyncio
    async def test_compile_creates_wiki_page(self, db_session, seed_sources):
        """Compilation should create wiki pages from sources."""
        from app.services.wiki_compilation_service import compile_wiki

        with patch(
            "app.services.wiki_compilation_service.generate_wiki_page",
            new_callable=AsyncMock,
            return_value=MOCK_COMPILE_RESPONSE,
        ):
            await compile_wiki(db_session, user_id=1, model="haiku")

        result = await db_session.execute(select(WikiPage))
        pages = result.scalars().all()
        assert len(pages) >= 1

    @pytest.mark.asyncio
    async def test_compile_records_sources(self, db_session, seed_sources):
        """Compilation should create wiki_sources entries linking pages to sources."""
        from app.services.wiki_compilation_service import compile_wiki

        with patch(
            "app.services.wiki_compilation_service.generate_wiki_page",
            new_callable=AsyncMock,
            return_value=MOCK_COMPILE_RESPONSE,
        ):
            await compile_wiki(db_session, user_id=1, model="haiku")

        result = await db_session.execute(select(WikiSource))
        sources = result.scalars().all()
        assert len(sources) >= 1
