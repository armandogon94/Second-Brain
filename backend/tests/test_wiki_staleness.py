"""Tests for wiki source tracking and staleness propagation (Slice 3 — RED first)."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Note, User, WikiPage, WikiSource
from app.utils.wiki_helpers import content_hash


@pytest.fixture
async def seed_user(db_session):
    user = User(id=1, username="armando", llm_preference="haiku")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def seed_note_and_wiki(db_session, seed_user):
    """Create a note and a wiki page that cites it via wiki_sources."""
    note = Note(
        user_id=1,
        content="Original note about machine learning",
        source="web_ui",
    )
    db_session.add(note)
    await db_session.flush()

    page = WikiPage(
        user_id=1,
        slug="machine-learning",
        title="Machine Learning",
        page_type="concept",
        content_markdown="# Machine Learning\nCompiled from notes.",
        is_stale=False,
    )
    db_session.add(page)
    await db_session.flush()

    source = WikiSource(
        wiki_page_id=page.id,
        source_type="note",
        source_id=note.id,
        source_hash=content_hash(note.content),
    )
    db_session.add(source)
    await db_session.flush()

    return {"note": note, "page": page, "source": source}


class TestMarkStaleness:
    @pytest.mark.asyncio
    async def test_mark_stale_on_note_update(self, client, seed_note_and_wiki):
        """Updating a note should mark wiki pages that cite it as stale."""
        note = seed_note_and_wiki["note"]
        page = seed_note_and_wiki["page"]

        # Update the note
        response = await client.put(
            f"/api/v1/notes/{note.id}",
            json={"content": "Updated note about deep learning"},
        )
        assert response.status_code == 200

        # Check wiki page is now stale
        wiki_response = await client.get(f"/api/v1/wiki/pages/{page.slug}")
        assert wiki_response.status_code == 200
        assert wiki_response.json()["is_stale"] is True

    @pytest.mark.asyncio
    async def test_no_stale_when_unrelated_note_updated(
        self, client, db_session, seed_note_and_wiki
    ):
        """Updating a note that NO wiki page cites should not mark anything stale."""
        page = seed_note_and_wiki["page"]

        # Create an unrelated note
        other_note = Note(
            user_id=1, content="Unrelated note about cooking", source="web_ui"
        )
        db_session.add(other_note)
        await db_session.flush()

        # Update the unrelated note
        response = await client.put(
            f"/api/v1/notes/{other_note.id}",
            json={"content": "Updated cooking note"},
        )
        assert response.status_code == 200

        # Wiki page should NOT be stale
        wiki_response = await client.get(f"/api/v1/wiki/pages/{page.slug}")
        assert wiki_response.status_code == 200
        assert wiki_response.json()["is_stale"] is False


class TestSourceTracking:
    @pytest.mark.asyncio
    async def test_wiki_page_has_sources(self, client, seed_note_and_wiki):
        """GET wiki page should include its sources."""
        page = seed_note_and_wiki["page"]

        response = await client.get(f"/api/v1/wiki/pages/{page.slug}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["sources"]) == 1
        assert data["sources"][0]["source_type"] == "note"
        assert data["sources"][0]["source_id"] == seed_note_and_wiki["note"].id

    @pytest.mark.asyncio
    async def test_source_hash_stored(self, db_session, seed_note_and_wiki):
        """WikiSource should store content hash for change detection."""
        source = seed_note_and_wiki["source"]
        expected_hash = content_hash("Original note about machine learning")
        assert source.source_hash == expected_hash

    @pytest.mark.asyncio
    async def test_multiple_sources_per_page(self, db_session, seed_note_and_wiki):
        """A wiki page can have multiple sources."""
        page = seed_note_and_wiki["page"]

        note2 = Note(
            user_id=1, content="Another note about neural networks", source="web_ui"
        )
        db_session.add(note2)
        await db_session.flush()

        source2 = WikiSource(
            wiki_page_id=page.id,
            source_type="note",
            source_id=note2.id,
            source_hash=content_hash(note2.content),
        )
        db_session.add(source2)
        await db_session.flush()

        result = await db_session.execute(
            select(WikiSource).where(WikiSource.wiki_page_id == page.id)
        )
        sources = result.scalars().all()
        assert len(sources) == 2
