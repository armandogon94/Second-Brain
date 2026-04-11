"""Tests for wiki Obsidian export endpoint (Slice 10 — RED first)."""

import io
import zipfile

import pytest

from app.models import User, WikiPage, WikiSource


@pytest.fixture
async def seed_user(db_session):
    user = User(id=1, username="armando", llm_preference="haiku")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def seed_wiki_for_export(db_session, seed_user):
    pages = [
        WikiPage(
            user_id=1,
            slug="machine-learning",
            title="Machine Learning",
            page_type="concept",
            content_markdown="# Machine Learning\nContent with [[Deep Learning]].",
            confidence=0.85,
            frontmatter={"summary": "ML overview"},
        ),
        WikiPage(
            user_id=1,
            slug="deep-learning",
            title="Deep Learning",
            page_type="concept",
            content_markdown="# Deep Learning\nA subset of [[Machine Learning]].",
            confidence=0.9,
        ),
    ]
    db_session.add_all(pages)
    await db_session.flush()

    source = WikiSource(
        wiki_page_id=pages[0].id,
        source_type="note",
        source_id=1,
        source_hash="abc123",
    )
    db_session.add(source)
    await db_session.flush()
    return pages


class TestObsidianExport:
    @pytest.mark.asyncio
    async def test_export_returns_zip(self, client, seed_wiki_for_export):
        response = await client.get("/api/v1/wiki/export")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"

    @pytest.mark.asyncio
    async def test_export_contains_md_files(self, client, seed_wiki_for_export):
        response = await client.get("/api/v1/wiki/export")
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        names = zf.namelist()
        assert "machine-learning.md" in names
        assert "deep-learning.md" in names

    @pytest.mark.asyncio
    async def test_export_contains_frontmatter(self, client, seed_wiki_for_export):
        response = await client.get("/api/v1/wiki/export")
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        content = zf.read("machine-learning.md").decode()
        assert "---" in content
        assert "title: Machine Learning" in content
        assert "type: concept" in content
        assert "confidence:" in content

    @pytest.mark.asyncio
    async def test_export_preserves_wikilinks(self, client, seed_wiki_for_export):
        response = await client.get("/api/v1/wiki/export")
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        content = zf.read("machine-learning.md").decode()
        assert "[[Deep Learning]]" in content

    @pytest.mark.asyncio
    async def test_export_empty_wiki(self, client, seed_user):
        response = await client.get("/api/v1/wiki/export")
        assert response.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        assert len(zf.namelist()) == 0
