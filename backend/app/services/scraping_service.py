import asyncio
from urllib.parse import urlparse

import trafilatura

from app.utils.logger import logger


def _scrape_url_sync(url: str) -> dict:
    """Synchronous URL scraping using trafilatura."""
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        raise ValueError(f"Could not download content from: {url}")

    result = trafilatura.extract(
        downloaded,
        include_links=False,
        include_images=False,
        include_tables=True,
        output_format="markdown",
        with_metadata=True,
    )

    if not result:
        # Fallback: try with less strict extraction
        result = trafilatura.extract(
            downloaded,
            include_links=False,
            include_images=False,
            output_format="markdown",
            no_fallback=False,
        )

    metadata = trafilatura.extract_metadata(downloaded)
    title = metadata.title if metadata else None
    domain = urlparse(url).netloc

    return {
        "content": result or "",
        "title": title or domain,
        "domain": domain,
    }


async def scrape_url(url: str) -> dict:
    """Scrape article content from a URL asynchronously.

    Returns dict with 'content' (markdown), 'title', and 'domain'.
    """
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid URL: {url}")

    result = await asyncio.to_thread(_scrape_url_sync, url)
    logger.info(
        "Scraped %d chars from %s: %s",
        len(result["content"]),
        result["domain"],
        result["title"],
    )
    return result
