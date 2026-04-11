"""Tests for wiki-aware search (Slice 6 — RED first)."""

from unittest.mock import AsyncMock, patch

import pytest

from app.models import User, WikiPage


@pytest.fixture
async def seed_user(db_session):
    user = User(id=1, username="armando", llm_preference="haiku")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def seed_wiki_for_search(db_session, seed_user):
    """Create wiki pages for search tests."""
    ml_page = WikiPage(
        user_id=1,
        slug="machine-learning",
        title="Machine Learning",
        page_type="concept",
        content_markdown="# Machine Learning\nML is a subset of AI.",
    )
    python_page = WikiPage(
        user_id=1,
        slug="python",
        title="Python",
        page_type="concept",
        content_markdown="# Python\nPython is great for data science.",
    )
    db_session.add_all([ml_page, python_page])
    await db_session.flush()
    return {"ml": ml_page, "python": python_page}


class TestWikiQuery:
    @pytest.mark.asyncio
    async def test_wiki_first_finds_page(self, client, seed_wiki_for_search):
        """wiki_first mode should return matching wiki page directly."""
        response = await client.post(
            "/api/v1/wiki/query",
            json={"query": "machine learning", "mode": "wiki_first"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["wiki_page"] is not None
        assert data["wiki_page"]["slug"] == "machine-learning"

    @pytest.mark.asyncio
    async def test_wiki_first_no_match_returns_empty_page(
        self, client, seed_wiki_for_search
    ):
        """wiki_first mode with no wiki match should return wiki_page=None."""
        response = await client.post(
            "/api/v1/wiki/query",
            json={"query": "quantum computing", "mode": "wiki_first"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["wiki_page"] is None

    @pytest.mark.asyncio
    async def test_wiki_query_returns_answer(self, client, seed_wiki_for_search):
        """Should always return an answer string."""
        response = await client.post(
            "/api/v1/wiki/query",
            json={"query": "python"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert isinstance(data["answer"], str)

    @pytest.mark.asyncio
    async def test_wiki_query_empty_rejected(self, client, seed_user):
        response = await client.post(
            "/api/v1/wiki/query",
            json={"query": ""},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_wiki_query_default_mode(self, client, seed_wiki_for_search):
        """Default mode should be wiki_first."""
        response = await client.post(
            "/api/v1/wiki/query",
            json={"query": "machine learning"},
        )
        assert response.status_code == 200
        data = response.json()
        # wiki_first mode should attempt wiki lookup
        assert "wiki_page" in data
