"""Wiki graph, lint, query, and export endpoints."""

import io
import zipfile

import yaml
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import WikiLink, WikiPage
from app.schemas import (
    GraphEdge,
    GraphNode,
    GraphResponse,
    LintIssue,
    LintResponse,
    WikiPageResponse,
    WikiQueryRequest,
    WikiQueryResponse,
)
from app.api.wiki import _build_response

router = APIRouter()


@router.get("/graph", response_model=GraphResponse)
async def get_graph(db: AsyncSession = Depends(get_db)):
    """Return all wiki pages as nodes and wiki_links as edges for graph visualization."""
    # Nodes
    pages_q = select(WikiPage).where(WikiPage.user_id == 1, WikiPage.is_published == True)  # noqa: E712
    result = await db.execute(pages_q)
    pages = result.scalars().all()

    # Count outgoing + incoming links per page
    page_ids = {p.id for p in pages}

    # Get all links
    links_q = select(WikiLink).where(
        WikiLink.from_page_id.in_(page_ids) | WikiLink.to_page_id.in_(page_ids)
    )
    result = await db.execute(links_q)
    links = result.scalars().all()

    # Count links per page (both directions)
    link_counts: dict[int, int] = {p.id: 0 for p in pages}
    for link in links:
        if link.from_page_id in link_counts:
            link_counts[link.from_page_id] += 1
        if link.to_page_id in link_counts:
            link_counts[link.to_page_id] += 1

    nodes = [
        GraphNode(
            id=p.id,
            slug=p.slug,
            title=p.title,
            type=p.page_type,
            link_count=link_counts.get(p.id, 0),
        )
        for p in pages
    ]

    edges = [
        GraphEdge(
            source=link.from_page_id,
            target=link.to_page_id,
            label=link.link_text,
        )
        for link in links
    ]

    return GraphResponse(nodes=nodes, edges=edges)


@router.post("/lint", response_model=LintResponse)
async def lint_wiki(db: AsyncSession = Depends(get_db)):
    """Run health check on the wiki: detect orphans, stale pages, broken links."""
    issues: list[LintIssue] = []

    # Get all pages
    result = await db.execute(
        select(WikiPage).where(WikiPage.user_id == 1)
    )
    pages = result.scalars().all()
    page_ids = {p.id for p in pages}

    # Get all links
    result = await db.execute(select(WikiLink))
    links = result.scalars().all()

    # Build adjacency sets
    has_outgoing = {link.from_page_id for link in links}
    has_incoming = {link.to_page_id for link in links}

    # Detect orphans (no incoming AND no outgoing links)
    for page in pages:
        if page.id not in has_outgoing and page.id not in has_incoming:
            issues.append(
                LintIssue(
                    type="orphan",
                    slug=page.slug,
                    message=f"Page '{page.title}' has no incoming or outgoing links",
                )
            )

    # Detect stale pages
    for page in pages:
        if page.is_stale:
            issues.append(
                LintIssue(
                    type="stale",
                    slug=page.slug,
                    message=f"Page '{page.title}' has stale source data",
                )
            )

    # Detect broken links (links pointing to non-existent pages)
    for link in links:
        if link.to_page_id not in page_ids:
            issues.append(
                LintIssue(
                    type="broken_link",
                    slug=None,
                    message=f"Link from page {link.from_page_id} points to missing page {link.to_page_id}",
                )
            )

    stats = {
        "total_pages": len(pages),
        "total_links": len(links),
        "orphan_count": sum(1 for i in issues if i.type == "orphan"),
        "stale_count": sum(1 for i in issues if i.type == "stale"),
        "broken_link_count": sum(1 for i in issues if i.type == "broken_link"),
    }

    return LintResponse(issues=issues, stats=stats)


@router.post("/query", response_model=WikiQueryResponse)
async def wiki_query(req: WikiQueryRequest, db: AsyncSession = Depends(get_db)):
    """Wiki-aware query: check wiki index first, then fall back to RAG."""
    wiki_page_resp = None

    if req.mode in ("wiki_first", "hybrid"):
        # Search wiki pages by title/content match
        pattern = f"%{req.query}%"
        result = await db.execute(
            select(WikiPage)
            .where(
                WikiPage.user_id == 1,
                WikiPage.is_published == True,  # noqa: E712
                WikiPage.title.ilike(pattern) | WikiPage.content_markdown.ilike(pattern),
            )
            .order_by(WikiPage.confidence.desc())
            .limit(1)
        )
        page = result.scalar_one_or_none()
        if page:
            wiki_page_resp = await _build_response(db, page)

    # Build answer from wiki page if found
    if wiki_page_resp:
        answer = (
            f"From your wiki page **{wiki_page_resp.title}**:\n\n"
            f"{wiki_page_resp.content_markdown[:500]}"
        )
    else:
        answer = "No matching wiki page found for this query."

    return WikiQueryResponse(
        answer=answer,
        wiki_page=wiki_page_resp,
        sources=[],
        usage={},
    )


@router.get("/export")
async def export_obsidian(db: AsyncSession = Depends(get_db)):
    """Export all wiki pages as an Obsidian-compatible zip of .md files."""
    result = await db.execute(
        select(WikiPage).where(WikiPage.user_id == 1).order_by(WikiPage.title)
    )
    pages = result.scalars().all()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for page in pages:
            fm = {
                "title": page.title,
                "type": page.page_type,
                "confidence": page.confidence,
            }
            if page.frontmatter:
                fm.update(page.frontmatter)
            front = yaml.dump(fm, default_flow_style=False, allow_unicode=True).strip()
            content = f"---\n{front}\n---\n\n{page.content_markdown}"
            zf.writestr(f"{page.slug}.md", content)

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=wiki-export.zip"},
    )
