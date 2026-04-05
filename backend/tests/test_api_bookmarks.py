import pytest

from app.models import User


@pytest.fixture
async def seed_user(db_session):
    user = User(id=1, username="armando", llm_preference="haiku")
    db_session.add(user)
    await db_session.flush()
    return user


class TestBookmarksAPI:
    @pytest.mark.asyncio
    async def test_create_bookmark(self, client, seed_user, mock_scrape):
        response = await client.post(
            "/api/v1/bookmarks",
            json={"url": "https://example.com/article", "tags": ["tech"]},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["original_url"] == "https://example.com/article"
        assert data["title"] == "Test Article"
        assert data["source_domain"] == "example.com"
        assert data["is_read"] is False

    @pytest.mark.asyncio
    async def test_create_bookmark_duplicate(self, client, seed_user, mock_scrape):
        await client.post(
            "/api/v1/bookmarks", json={"url": "https://example.com/same"}
        )
        response = await client.post(
            "/api/v1/bookmarks", json={"url": "https://example.com/same"}
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_create_bookmark_invalid_url(self, client, seed_user):
        response = await client.post("/api/v1/bookmarks", json={"url": "not-a-url"})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_bookmarks(self, client, seed_user, mock_scrape):
        await client.post("/api/v1/bookmarks", json={"url": "https://example.com/1"})
        await client.post("/api/v1/bookmarks", json={"url": "https://example.com/2"})

        response = await client.get("/api/v1/bookmarks")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    @pytest.mark.asyncio
    async def test_mark_as_read(self, client, seed_user, mock_scrape):
        create = await client.post(
            "/api/v1/bookmarks", json={"url": "https://example.com/read-test"}
        )
        bookmark_id = create.json()["id"]

        response = await client.put(
            f"/api/v1/bookmarks/{bookmark_id}", json={"is_read": True}
        )
        assert response.status_code == 200
        assert response.json()["is_read"] is True

    @pytest.mark.asyncio
    async def test_delete_bookmark(self, client, seed_user, mock_scrape):
        create = await client.post(
            "/api/v1/bookmarks", json={"url": "https://example.com/delete-test"}
        )
        bookmark_id = create.json()["id"]

        response = await client.delete(f"/api/v1/bookmarks/{bookmark_id}")
        assert response.status_code == 204
