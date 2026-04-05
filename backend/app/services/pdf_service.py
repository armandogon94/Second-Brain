import asyncio
from pathlib import Path

import pdfplumber

from app.utils.logger import logger


def _extract_text_sync(file_path: str) -> dict:
    """Synchronous PDF text extraction using pdfplumber."""
    text_parts: list[str] = []
    page_count = 0

    with pdfplumber.open(file_path) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    full_text = "\n\n".join(text_parts)

    # OCR fallback detection: if extracted text is very short, it might be scanned
    if len(full_text.strip()) < 50 and page_count > 0:
        logger.warning(
            "PDF %s has very little text (%d chars) — may be scanned. "
            "OCR fallback not enabled (install 'ocr' extras).",
            file_path,
            len(full_text),
        )

    return {
        "text": full_text,
        "page_count": page_count,
    }


async def extract_pdf_text(file_path: str) -> dict:
    """Extract text from a PDF file asynchronously.

    Returns dict with 'text' and 'page_count'.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    if not path.suffix.lower() == ".pdf":
        raise ValueError(f"Not a PDF file: {file_path}")

    result = await asyncio.to_thread(_extract_text_sync, file_path)
    logger.info(
        "Extracted %d chars from %d pages: %s",
        len(result["text"]),
        result["page_count"],
        path.name,
    )
    return result
