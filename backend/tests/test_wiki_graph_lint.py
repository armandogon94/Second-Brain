"""Tests for graph API and lint/health check endpoints (Slice 5 — RED first)."""

import pytest

from app.models import User, WikiLink, WikiPage


@pytest.fixture
async def seed_user(db_session):
    user = User(id=1, username="armando", llm_preference="haiku")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def seed_wiki_graph(db_session, seed_user):
    """Create a small wiki graph: A -> B -> C, A -> C."""
    page_a = WikiPage(
        user_id=1,
        slug="page-a",
        title="Page A",
        page_type="concept",
        content_markdown="Links to [[Page B]] and [[Page C]].",
    )
    page_b = WikiPage(
        user_id=1,
        slug="page-b",
        title="Page B",
        page_type="concept",
        content_markdown="Links to [[Page C]].",
    )
    page_c = WikiPage(
        user_id=1,
        slug="page-c",
        title="Page C",
        page_type="reference",
        content_markdown="A leaf node.",
    )
    orphan = WikiPage(
        user_id=1,
        slug="orphan-page",
        title="Orphan Page",
        page_type="concept",
        content_markdown="No links in or out.",
    )
    db_session.add_all([page_a, page_b, page_c, orphan])
    await db_session.flush()

    # Create links
    links = [
        WikiLink(from_page_id=page_a.id, to_page_id=page_b.id, link_text="Page B"),
        WikiLink(from_page_id=page_a.id, to_page_id=page_c.id, link_text="Page C"),
        WikiLink(from_page_id=page_b.id, to_page_id=page_c.id, link_text="Page C"),
    ]
    db_session.add_all(links)
    await db_session.flush()

    return {
        "page_a": page_a,
        "page_b": page_b,
        "page_c": page_c,
        "orphan": orphan,
    }


class TestGraphAPI:
    @pytest.mark.asyncio
    async def test_graph_returns_nodes_and_edges(self, client, seed_wiki_graph):
        response = await client.get("/api/v1/wiki/graph")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 4
        assert len(data["edges"]) == 3

    @pytest.mark.asyncio
    async def test_graph_node_shape(self, client, seed_wiki_graph):
        response = await client.get("/api/v1/wiki/graph")
        data = response.json()
        node = data["nodes"][0]
        assert "id" in node
        assert "slug" in node
        assert "title" in node
        assert "type" in node
        assert "link_count" in node

    @pytest.mark.asyncio
    async def test_graph_edge_shape(self, client, seed_wiki_graph):
        response = await client.get("/api/v1/wiki/graph")
        data = response.json()
        edge = data["edges"][0]
        assert "source" in edge
        assert "target" in edge

    @pytest.mark.asyncio
    async def test_graph_empty(self, client, seed_user):
        response = await client.get("/api/v1/wiki/graph")
        assert response.status_code == 200
        data = response.json()
        assert data["nodes"] == []
        assert data["edges"] == []


class TestLintAPI:
    @pytest.mark.asyncio
    async def test_lint_detects_orphans(self, client, seed_wiki_graph):
        """Orphan pages (no incoming or outgoing links) should be flagged."""
        response = await client.post("/api/v1/wiki/lint")
        assert response.status_code == 200
        data = response.json()
        orphan_issues = [i for i in data["issues"] if i["type"] == "orphan"]
        assert len(orphan_issues) >= 1
        orphan_slugs = [i["slug"] for i in orphan_issues]
        assert "orphan-page" in orphan_slugs

    @pytest.mark.asyncio
    async def test_lint_includes_stats(self, client, seed_wiki_graph):
        response = await client.post("/api/v1/wiki/lint")
        assert response.status_code == 200
        data = response.json()
        assert "stats" in data
        assert "total_pages" in data["stats"]
        assert data["stats"]["total_pages"] == 4

    @pytest.mark.asyncio
    async def test_lint_detects_stale(self, client, db_session, seed_wiki_graph):
        """Stale pages should be flagged."""
        page_a = seed_wiki_graph["page_a"]
        page_a.is_stale = True
        await db_session.flush()

        response = await client.post("/api/v1/wiki/lint")
        data = response.json()
        stale_issues = [i for i in data["issues"] if i["type"] == "stale"]
        assert len(stale_issues) >= 1

    @pytest.mark.asyncio
    async def test_lint_empty_wiki(self, client, seed_user):
        response = await client.post("/api/v1/wiki/lint")
        assert response.status_code == 200
        data = response.json()
        assert data["stats"]["total_pages"] == 0
