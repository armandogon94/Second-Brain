"""Tests for wiki CRUD API endpoints (Slice 2 — RED first)."""

import pytest

from app.models import User, WikiPage


@pytest.fixture
async def seed_user(db_session):
    user = User(id=1, username="armando", llm_preference="haiku")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def seed_wiki_page(db_session, seed_user):
    """Create a wiki page for tests that need one."""
    page = WikiPage(
        user_id=1,
        slug="machine-learning",
        title="Machine Learning",
        page_type="concept",
        content_markdown="# Machine Learning\nOverview of [[Deep Learning]] techniques.",
        frontmatter={"summary": "ML overview"},
        confidence=0.9,
    )
    db_session.add(page)
    await db_session.flush()
    return page


class TestCreateWikiPage:
    @pytest.mark.asyncio
    async def test_create_page(self, client, seed_user):
        response = await client.post(
            "/api/v1/wiki/pages",
            json={
                "title": "Machine Learning",
                "content_markdown": "# Machine Learning\nContent here.",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Machine Learning"
        assert data["slug"] == "machine-learning"
        assert data["page_type"] == "concept"
        assert data["confidence"] == 0.8
        assert data["is_stale"] is False
        assert data["version"] == 1
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_page_with_type(self, client, seed_user):
        response = await client.post(
            "/api/v1/wiki/pages",
            json={
                "title": "John Doe",
                "content_markdown": "Person profile.",
                "page_type": "person",
            },
        )
        assert response.status_code == 201
        assert response.json()["page_type"] == "person"

    @pytest.mark.asyncio
    async def test_create_page_empty_title_rejected(self, client, seed_user):
        response = await client.post(
            "/api/v1/wiki/pages",
            json={"title": "", "content_markdown": "Content"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_page_empty_content_rejected(self, client, seed_user):
        response = await client.post(
            "/api/v1/wiki/pages",
            json={"title": "Title", "content_markdown": ""},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_page_duplicate_slug(self, client, seed_user):
        await client.post(
            "/api/v1/wiki/pages",
            json={
                "title": "Machine Learning",
                "content_markdown": "First page.",
            },
        )
        response = await client.post(
            "/api/v1/wiki/pages",
            json={
                "title": "Machine Learning",
                "content_markdown": "Second page, same title.",
            },
        )
        # Should get a conflict or auto-suffix
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_create_page_auto_generates_slug(self, client, seed_user):
        response = await client.post(
            "/api/v1/wiki/pages",
            json={
                "title": "What's New in Python 3.12?",
                "content_markdown": "New features.",
            },
        )
        assert response.status_code == 201
        assert response.json()["slug"] == "whats-new-in-python-312"


class TestListWikiPages:
    @pytest.mark.asyncio
    async def test_list_empty(self, client, seed_user):
        response = await client.get("/api/v1/wiki/pages")
        assert response.status_code == 200
        data = response.json()
        assert data["pages"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_pages(self, client, seed_user):
        for title in ["Page A", "Page B", "Page C"]:
            await client.post(
                "/api/v1/wiki/pages",
                json={"title": title, "content_markdown": f"Content for {title}"},
            )

        response = await client.get("/api/v1/wiki/pages")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["pages"]) == 3

    @pytest.mark.asyncio
    async def test_list_pages_filter_by_type(self, client, seed_user):
        await client.post(
            "/api/v1/wiki/pages",
            json={
                "title": "Concept A",
                "content_markdown": "Concept content",
                "page_type": "concept",
            },
        )
        await client.post(
            "/api/v1/wiki/pages",
            json={
                "title": "Person B",
                "content_markdown": "Person content",
                "page_type": "person",
            },
        )

        response = await client.get("/api/v1/wiki/pages?page_type=concept")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["pages"][0]["page_type"] == "concept"

    @pytest.mark.asyncio
    async def test_list_pages_pagination(self, client, seed_user):
        for i in range(5):
            await client.post(
                "/api/v1/wiki/pages",
                json={"title": f"Page {i}", "content_markdown": f"Content {i}"},
            )

        response = await client.get("/api/v1/wiki/pages?skip=0&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["pages"]) == 2

    @pytest.mark.asyncio
    async def test_list_pages_search(self, client, seed_user):
        await client.post(
            "/api/v1/wiki/pages",
            json={
                "title": "Python Guide",
                "content_markdown": "How to learn Python.",
            },
        )
        await client.post(
            "/api/v1/wiki/pages",
            json={
                "title": "Rust Guide",
                "content_markdown": "How to learn Rust.",
            },
        )

        response = await client.get("/api/v1/wiki/pages?search=python")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        slugs = [p["slug"] for p in data["pages"]]
        assert "python-guide" in slugs


class TestGetWikiPage:
    @pytest.mark.asyncio
    async def test_get_page_by_slug(self, client, seed_user):
        await client.post(
            "/api/v1/wiki/pages",
            json={
                "title": "Machine Learning",
                "content_markdown": "# ML\nContent about ML.",
            },
        )

        response = await client.get("/api/v1/wiki/pages/machine-learning")
        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == "machine-learning"
        assert data["title"] == "Machine Learning"
        assert "backlinks" in data
        assert "sources" in data

    @pytest.mark.asyncio
    async def test_get_page_not_found(self, client, seed_user):
        response = await client.get("/api/v1/wiki/pages/nonexistent-page")
        assert response.status_code == 404


class TestUpdateWikiPage:
    @pytest.mark.asyncio
    async def test_update_title(self, client, seed_user):
        await client.post(
            "/api/v1/wiki/pages",
            json={
                "title": "Old Title",
                "content_markdown": "Content.",
            },
        )

        response = await client.put(
            "/api/v1/wiki/pages/old-title",
            json={"title": "New Title"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Title"
        # Slug should update when title changes
        assert data["slug"] == "new-title"

    @pytest.mark.asyncio
    async def test_update_content(self, client, seed_user):
        await client.post(
            "/api/v1/wiki/pages",
            json={
                "title": "Test Page",
                "content_markdown": "Original content.",
            },
        )

        response = await client.put(
            "/api/v1/wiki/pages/test-page",
            json={"content_markdown": "Updated content with [[New Link]]."},
        )
        assert response.status_code == 200
        assert response.json()["content_markdown"] == "Updated content with [[New Link]]."

    @pytest.mark.asyncio
    async def test_update_not_found(self, client, seed_user):
        response = await client.put(
            "/api/v1/wiki/pages/nonexistent",
            json={"title": "New"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_increments_version(self, client, seed_user):
        await client.post(
            "/api/v1/wiki/pages",
            json={
                "title": "Versioned Page",
                "content_markdown": "V1 content.",
            },
        )

        response = await client.put(
            "/api/v1/wiki/pages/versioned-page",
            json={"content_markdown": "V2 content."},
        )
        assert response.status_code == 200
        assert response.json()["version"] == 2


class TestDeleteWikiPage:
    @pytest.mark.asyncio
    async def test_delete_page(self, client, seed_user):
        await client.post(
            "/api/v1/wiki/pages",
            json={
                "title": "To Delete",
                "content_markdown": "Will be deleted.",
            },
        )

        response = await client.delete("/api/v1/wiki/pages/to-delete")
        assert response.status_code == 204

        get_response = await client.get("/api/v1/wiki/pages/to-delete")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_not_found(self, client, seed_user):
        response = await client.delete("/api/v1/wiki/pages/nonexistent")
        assert response.status_code == 404
