from unittest.mock import AsyncMock, patch

import pytest

from app.models import User


@pytest.fixture
async def seed_user(db_session):
    user = User(id=1, username="armando", llm_preference="haiku")
    db_session.add(user)
    await db_session.flush()
    return user


class TestSearchAPI:
    @pytest.mark.asyncio
    async def test_search_empty_query(self, client, seed_user):
        response = await client.post("/api/v1/search", json={"query": ""})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_valid_query(self, client, seed_user, mock_embed_single, mock_llm):
        with patch(
            "app.api.search.hybrid_search",
            new_callable=AsyncMock,
            return_value=[
                {
                    "chunk_id": 1,
                    "content": "Machine learning is a subset of AI.",
                    "source_type": "note",
                    "source_id": 1,
                    "score": 0.85,
                    "title": "ML Notes",
                }
            ],
        ), patch(
            "app.api.search.search_and_answer",
            new_callable=AsyncMock,
            return_value={
                "answer": "Test answer",
                "sources": [
                    {
                        "source_type": "note",
                        "source_id": 1,
                        "title": "ML Notes",
                        "content_preview": "Machine learning...",
                        "score": 0.85,
                        "chunk_id": 1,
                    }
                ],
                "usage": {"input_tokens": 100, "output_tokens": 50},
            },
        ):
            response = await client.post(
                "/api/v1/search", json={"query": "What is machine learning?"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "answer" in data
            assert "sources" in data

    @pytest.mark.asyncio
    async def test_search_with_model_selection(self, client, seed_user):
        with patch(
            "app.api.search.search_and_answer",
            new_callable=AsyncMock,
            return_value={"answer": "Test", "sources": [], "usage": {}},
        ):
            response = await client.post(
                "/api/v1/search",
                json={"query": "test query", "llm_model": "sonnet"},
            )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_raw_search(self, client, seed_user):
        with patch(
            "app.api.search.hybrid_search",
            new_callable=AsyncMock,
            return_value=[
                {
                    "chunk_id": 1,
                    "content": "Some content here.",
                    "source_type": "note",
                    "source_id": 1,
                    "score": 0.75,
                    "title": "Test Note",
                }
            ],
        ):
            response = await client.post(
                "/api/v1/search/raw",
                json={"query": "test", "include_scores": True},
            )
            assert response.status_code == 200
            data = response.json()
            assert "chunks" in data
            assert data["total"] == 1

    @pytest.mark.asyncio
    async def test_search_query_too_long(self, client, seed_user):
        response = await client.post("/api/v1/search", json={"query": "x" * 501})
        assert response.status_code == 422
