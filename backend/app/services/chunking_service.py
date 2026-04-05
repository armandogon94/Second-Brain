import re

from app.config import settings
from app.utils.tokenizer import count_tokens


def split_into_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def chunk_text(
    text: str,
    chunk_size: int = settings.chunk_size,
    chunk_overlap: int = settings.chunk_overlap,
    min_chunk_size: int = settings.min_chunk_size,
) -> list[dict]:
    """Split text into chunks using sentence-boundary splitting with token accumulation.

    Returns list of dicts with 'content', 'token_count', 'character_count'.
    """
    if not text or not text.strip():
        return []

    total_tokens = count_tokens(text)
    if total_tokens <= chunk_size:
        return [
            {
                "content": text.strip(),
                "token_count": total_tokens,
                "character_count": len(text.strip()),
            }
        ]

    # Split by paragraphs first, then sentences
    paragraphs = re.split(r"\n\s*\n", text)
    sentences: list[str] = []
    for para in paragraphs:
        para_sentences = split_into_sentences(para)
        sentences.extend(para_sentences)

    if not sentences:
        sentences = [text]

    chunks: list[dict] = []
    current_sentences: list[str] = []
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = count_tokens(sentence)

        # If single sentence exceeds chunk_size, split by character
        if sentence_tokens > chunk_size:
            # Flush current buffer
            if current_sentences:
                chunk_text_content = " ".join(current_sentences)
                chunks.append(
                    {
                        "content": chunk_text_content,
                        "token_count": count_tokens(chunk_text_content),
                        "character_count": len(chunk_text_content),
                    }
                )
                current_sentences = []
                current_tokens = 0

            # Split long sentence by words
            words = sentence.split()
            word_buffer: list[str] = []
            word_tokens = 0
            for word in words:
                wt = count_tokens(word)
                if word_tokens + wt > chunk_size and word_buffer:
                    chunk_content = " ".join(word_buffer)
                    chunks.append(
                        {
                            "content": chunk_content,
                            "token_count": count_tokens(chunk_content),
                            "character_count": len(chunk_content),
                        }
                    )
                    word_buffer = []
                    word_tokens = 0
                word_buffer.append(word)
                word_tokens += wt
            if word_buffer:
                chunk_content = " ".join(word_buffer)
                current_sentences = [chunk_content]
                current_tokens = count_tokens(chunk_content)
            continue

        if current_tokens + sentence_tokens > chunk_size and current_sentences:
            chunk_text_content = " ".join(current_sentences)
            chunks.append(
                {
                    "content": chunk_text_content,
                    "token_count": count_tokens(chunk_text_content),
                    "character_count": len(chunk_text_content),
                }
            )

            # Overlap: keep last few sentences that fit within overlap budget
            overlap_sentences: list[str] = []
            overlap_tokens = 0
            for s in reversed(current_sentences):
                st = count_tokens(s)
                if overlap_tokens + st > chunk_overlap:
                    break
                overlap_sentences.insert(0, s)
                overlap_tokens += st

            current_sentences = overlap_sentences
            current_tokens = overlap_tokens

        current_sentences.append(sentence)
        current_tokens += sentence_tokens

    # Flush remaining
    if current_sentences:
        chunk_text_content = " ".join(current_sentences)
        chunk_token_count = count_tokens(chunk_text_content)
        if chunk_token_count >= min_chunk_size or not chunks:
            chunks.append(
                {
                    "content": chunk_text_content,
                    "token_count": chunk_token_count,
                    "character_count": len(chunk_text_content),
                }
            )
        elif chunks:
            # Merge small trailing chunk with previous
            prev = chunks[-1]
            merged = prev["content"] + " " + chunk_text_content
            chunks[-1] = {
                "content": merged,
                "token_count": count_tokens(merged),
                "character_count": len(merged),
            }

    return chunks
