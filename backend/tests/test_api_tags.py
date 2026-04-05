import pytest

from app.models import User


@pytest.fixture
async def seed_user(db_session):
    user = User(id=1, username="armando", llm_preference="haiku")
    db_session.add(user)
    await db_session.flush()
    return user


class TestTagsAPI:
    @pytest.mark.asyncio
    async def test_create_tag(self, client, seed_user):
        response = await client.post(
            "/api/v1/tags", json={"name": "python", "color": "#3572A5"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "python"
        assert data["color"] == "#3572A5"
        assert data["count"] == 0

    @pytest.mark.asyncio
    async def test_create_tag_duplicate(self, client, seed_user):
        await client.post("/api/v1/tags", json={"name": "duplicate"})
        response = await client.post("/api/v1/tags", json={"name": "duplicate"})
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_create_tag_normalized(self, client, seed_user):
        response = await client.post(
            "/api/v1/tags", json={"name": "  Machine Learning  "}
        )
        assert response.status_code == 201
        assert response.json()["name"] == "machine learning"

    @pytest.mark.asyncio
    async def test_list_tags(self, client, seed_user):
        await client.post("/api/v1/tags", json={"name": "alpha"})
        await client.post("/api/v1/tags", json={"name": "beta"})

        response = await client.get("/api/v1/tags")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "alpha"

    @pytest.mark.asyncio
    async def test_delete_tag(self, client, seed_user):
        create = await client.post("/api/v1/tags", json={"name": "to-delete"})
        tag_id = create.json()["id"]

        response = await client.delete(f"/api/v1/tags/{tag_id}")
        assert response.status_code == 204

        list_response = await client.get("/api/v1/tags")
        assert len(list_response.json()) == 0

    @pytest.mark.asyncio
    async def test_delete_tag_not_found(self, client, seed_user):
        response = await client.delete("/api/v1/tags/9999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_color(self, client, seed_user):
        response = await client.post(
            "/api/v1/tags", json={"name": "bad-color", "color": "red"}
        )
        assert response.status_code == 422
