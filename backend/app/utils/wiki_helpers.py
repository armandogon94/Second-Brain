"""Wiki helper functions: slug generation, wikilink parsing, content hashing."""

import hashlib
import re
from unicodedata import normalize

WIKILINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")


def slugify(title: str) -> str:
    """Convert a title to a URL-safe slug.

    'Machine Learning Basics' -> 'machine-learning-basics'
    """
    slug = normalize("NFKD", title).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^\w\s-]", "", slug).strip().lower()
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug or "untitled"


def extract_wikilinks(markdown: str) -> list[str]:
    """Extract all [[wikilink]] targets from markdown content."""
    return WIKILINK_PATTERN.findall(markdown)


def content_hash(text: str) -> str:
    """SHA-256 hash of text content for change detection."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
