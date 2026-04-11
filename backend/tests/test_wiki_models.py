"""Tests for wiki models, schemas, and helper functions (Slice 1 — RED first)."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CompilationLog, WikiLink, WikiPage, WikiSource
from app.utils.wiki_helpers import content_hash, extract_wikilinks, slugify


# ─── Helper function tests ───────────────────────────────────────────────────


class TestSlugify:
    def test_basic_title(self):
        assert slugify("Machine Learning Basics") == "machine-learning-basics"

    def test_already_slug(self):
        assert slugify("hello-world") == "hello-world"

    def test_special_characters(self):
        assert slugify("What's New in Python 3.12?") == "whats-new-in-python-312"

    def test_unicode(self):
        assert slugify("Cafe Resume") == "cafe-resume"

    def test_multiple_spaces(self):
        assert slugify("too   many   spaces") == "too-many-spaces"

    def test_leading_trailing(self):
        assert slugify("  hello  ") == "hello"

    def test_empty_string(self):
        assert slugify("") == "untitled"

    def test_only_special_chars(self):
        assert slugify("!!!@@@###") == "untitled"


class TestExtractWikilinks:
    def test_single_link(self):
        assert extract_wikilinks("See [[Machine Learning]] for details") == [
            "Machine Learning"
        ]

    def test_multiple_links(self):
        result = extract_wikilinks(
            "Both [[Python]] and [[Rust]] are great [[Languages]]"
        )
        assert result == ["Python", "Rust", "Languages"]

    def test_no_links(self):
        assert extract_wikilinks("No links here") == []

    def test_empty_string(self):
        assert extract_wikilinks("") == []

    def test_nested_brackets(self):
        # [[link]] should match, [single] should not
        assert extract_wikilinks("[single] and [[double]]") == ["double"]

    def test_link_with_special_chars(self):
        assert extract_wikilinks("[[C++ Programming]]") == ["C++ Programming"]

    def test_adjacent_links(self):
        assert extract_wikilinks("[[A]][[B]]") == ["A", "B"]


class TestContentHash:
    def test_deterministic(self):
        h1 = content_hash("hello world")
        h2 = content_hash("hello world")
        assert h1 == h2

    def test_different_content(self):
        h1 = content_hash("hello")
        h2 = content_hash("world")
        assert h1 != h2

    def test_sha256_length(self):
        h = content_hash("test")
        assert len(h) == 64  # SHA-256 hex digest is 64 chars

    def test_empty_string(self):
        h = content_hash("")
        assert len(h) == 64


# ─── Pydantic schema tests ───────────────────────────────────────────────────


class TestWikiPageSchemas:
    def test_create_valid(self):
        from app.schemas import WikiPageCreate

        page = WikiPageCreate(
            title="Test Page",
            content_markdown="# Hello\nSome content with [[Link]]",
        )
        assert page.title == "Test Page"
        assert page.page_type == "concept"  # default
        assert page.frontmatter == {}

    def test_create_with_type(self):
        from app.schemas import WikiPageCreate

        page = WikiPageCreate(
            title="John Doe",
            content_markdown="Person profile",
            page_type="person",
        )
        assert page.page_type == "person"

    def test_create_invalid_type(self):
        from app.schemas import WikiPageCreate

        with pytest.raises(ValidationError):
            WikiPageCreate(
                title="Test",
                content_markdown="Content",
                page_type="invalid_type",
            )

    def test_create_empty_title_rejected(self):
        from app.schemas import WikiPageCreate

        with pytest.raises(ValidationError):
            WikiPageCreate(title="", content_markdown="Content")

    def test_create_empty_content_rejected(self):
        from app.schemas import WikiPageCreate

        with pytest.raises(ValidationError):
            WikiPageCreate(title="Title", content_markdown="")

    def test_update_all_optional(self):
        from app.schemas import WikiPageUpdate

        update = WikiPageUpdate()
        assert update.title is None
        assert update.content_markdown is None

    def test_response_model(self):
        from app.schemas import WikiPageResponse

        data = {
            "id": 1,
            "slug": "test-page",
            "title": "Test Page",
            "page_type": "concept",
            "content_markdown": "# Hello",
            "frontmatter": {"summary": "A test"},
            "confidence": 0.85,
            "is_stale": False,
            "version": 1,
            "compiled_at": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        response = WikiPageResponse(**data)
        assert response.slug == "test-page"
        assert response.backlinks == []
        assert response.sources == []


class TestCompileRequestSchema:
    def test_defaults(self):
        from app.schemas import CompileRequest

        req = CompileRequest()
        assert req.source_ids is None
        assert req.force is False
        assert req.model == "haiku"

    def test_valid_model(self):
        from app.schemas import CompileRequest

        req = CompileRequest(model="sonnet")
        assert req.model == "sonnet"

    def test_invalid_model(self):
        from app.schemas import CompileRequest

        with pytest.raises(ValidationError):
            CompileRequest(model="gpt4")


class TestGraphSchemas:
    def test_graph_node(self):
        from app.schemas import GraphNode

        node = GraphNode(
            id=1, slug="test", title="Test", type="concept", link_count=5
        )
        assert node.link_count == 5

    def test_graph_response(self):
        from app.schemas import GraphResponse

        resp = GraphResponse(nodes=[], edges=[])
        assert resp.nodes == []


# ─── SQLAlchemy model tests (need DB fixtures) ───────────────────────────────


@pytest.mark.asyncio
async def test_create_wiki_page(db_session: AsyncSession):
    """WikiPage model can be created with all fields."""
    page = WikiPage(
        user_id=1,
        slug="machine-learning",
        title="Machine Learning",
        page_type="concept",
        content_markdown="# Machine Learning\nContent here",
        frontmatter={"summary": "ML overview", "confidence": 0.9},
        confidence=0.9,
    )
    db_session.add(page)
    await db_session.flush()

    assert page.id is not None
    assert page.slug == "machine-learning"
    assert page.is_stale is False
    assert page.is_published is True
    assert page.version == 1


@pytest.mark.asyncio
async def test_create_wiki_link(db_session: AsyncSession):
    """WikiLink model connects two wiki pages."""
    page_a = WikiPage(
        user_id=1,
        slug="page-a",
        title="Page A",
        page_type="concept",
        content_markdown="Links to [[Page B]]",
    )
    page_b = WikiPage(
        user_id=1,
        slug="page-b",
        title="Page B",
        page_type="concept",
        content_markdown="Content",
    )
    db_session.add_all([page_a, page_b])
    await db_session.flush()

    link = WikiLink(
        from_page_id=page_a.id,
        to_page_id=page_b.id,
        link_text="Page B",
        context_snippet="Links to [[Page B]]",
    )
    db_session.add(link)
    await db_session.flush()

    assert link.id is not None
    assert link.from_page_id == page_a.id
    assert link.to_page_id == page_b.id


@pytest.mark.asyncio
async def test_create_wiki_source(db_session: AsyncSession):
    """WikiSource tracks which raw sources compiled into a page."""
    page = WikiPage(
        user_id=1,
        slug="test-src",
        title="Test Source",
        page_type="concept",
        content_markdown="Compiled from a note",
    )
    db_session.add(page)
    await db_session.flush()

    source = WikiSource(
        wiki_page_id=page.id,
        source_type="note",
        source_id=42,
        source_hash=content_hash("original note content"),
    )
    db_session.add(source)
    await db_session.flush()

    assert source.id is not None
    assert source.source_hash == content_hash("original note content")


@pytest.mark.asyncio
async def test_create_compilation_log(db_session: AsyncSession):
    """CompilationLog records compilation runs."""
    log = CompilationLog(
        user_id=1,
        action="compile",
        status="success",
        sources_processed=5,
        pages_created=3,
        pages_updated=2,
        token_usage={"input_tokens": 1000, "output_tokens": 500, "model": "haiku"},
    )
    db_session.add(log)
    await db_session.flush()

    assert log.id is not None
    assert log.action == "compile"
    assert log.token_usage["model"] == "haiku"


@pytest.mark.asyncio
async def test_wiki_page_defaults(db_session: AsyncSession):
    """WikiPage has correct defaults for optional fields."""
    page = WikiPage(
        user_id=1,
        slug="defaults-test",
        title="Defaults",
        page_type="concept",
        content_markdown="Minimal page",
    )
    db_session.add(page)
    await db_session.flush()

    assert page.is_published is True
    assert page.is_stale is False
    assert page.version == 1
    assert page.confidence == 0.8
    assert page.frontmatter == {}
