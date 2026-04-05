import pytest

from app.models import User


@pytest.fixture
async def seed_user(db_session):
    """Ensure user exists for tests."""
    user = User(id=1, username="armando", llm_preference="haiku")
    db_session.add(user)
    await db_session.flush()
    return user


class TestNotesAPI:
    @pytest.mark.asyncio
    async def test_create_note(self, client, seed_user):
        response = await client.post(
            "/api/v1/notes",
            json={"content": "Test note about machine learning", "tags": ["ai", "ml"]},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == "Test note about machine learning"
        assert data["source"] == "web_ui"
        assert data["is_archived"] is False
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_note_empty_content(self, client, seed_user):
        response = await client.post("/api/v1/notes", json={"content": ""})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_notes(self, client, seed_user):
        for i in range(3):
            await client.post("/api/v1/notes", json={"content": f"Note number {i}"})

        response = await client.get("/api/v1/notes")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["notes"]) == 3

    @pytest.mark.asyncio
    async def test_list_notes_pagination(self, client, seed_user):
        for i in range(5):
            await client.post("/api/v1/notes", json={"content": f"Note {i}"})

        response = await client.get("/api/v1/notes?skip=0&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["notes"]) == 2

    @pytest.mark.asyncio
    async def test_get_note(self, client, seed_user):
        create = await client.post("/api/v1/notes", json={"content": "Get this note"})
        note_id = create.json()["id"]

        response = await client.get(f"/api/v1/notes/{note_id}")
        assert response.status_code == 200
        assert response.json()["content"] == "Get this note"

    @pytest.mark.asyncio
    async def test_get_note_not_found(self, client, seed_user):
        response = await client.get("/api/v1/notes/9999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_note(self, client, seed_user):
        create = await client.post("/api/v1/notes", json={"content": "Original content"})
        note_id = create.json()["id"]

        response = await client.put(
            f"/api/v1/notes/{note_id}", json={"content": "Updated content"}
        )
        assert response.status_code == 200
        assert response.json()["content"] == "Updated content"

    @pytest.mark.asyncio
    async def test_delete_note_soft(self, client, seed_user):
        create = await client.post("/api/v1/notes", json={"content": "To be archived"})
        note_id = create.json()["id"]

        response = await client.delete(f"/api/v1/notes/{note_id}")
        assert response.status_code == 204

        list_response = await client.get("/api/v1/notes")
        assert list_response.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_delete_note_hard(self, client, seed_user):
        create = await client.post("/api/v1/notes", json={"content": "To be deleted"})
        note_id = create.json()["id"]

        response = await client.delete(f"/api/v1/notes/{note_id}?hard=true")
        assert response.status_code == 204

        get_response = await client.get(f"/api/v1/notes/{note_id}")
        assert get_response.status_code == 404


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
