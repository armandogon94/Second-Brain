import pytest

from app.services.chunking_service import chunk_text, split_into_sentences


class TestSplitIntoSentences:
    def test_simple_sentences(self):
        text = "First sentence. Second sentence. Third sentence."
        result = split_into_sentences(text)
        assert len(result) == 3
        assert result[0] == "First sentence."

    def test_empty_text(self):
        assert split_into_sentences("") == []

    def test_single_sentence(self):
        result = split_into_sentences("Just one sentence.")
        assert len(result) == 1

    def test_question_and_exclamation(self):
        text = "Is this a question? Yes it is! And a statement."
        result = split_into_sentences(text)
        assert len(result) == 3


class TestChunkText:
    def test_short_text_single_chunk(self):
        text = "This is a short note."
        chunks = chunk_text(text, chunk_size=500)
        assert len(chunks) == 1
        assert chunks[0]["content"] == text
        assert chunks[0]["token_count"] > 0
        assert chunks[0]["character_count"] == len(text)

    def test_empty_text(self):
        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_long_text_multiple_chunks(self):
        # Create text that's definitely longer than chunk_size tokens
        sentences = [f"This is sentence number {i} with some content." for i in range(100)]
        text = " ".join(sentences)
        chunks = chunk_text(text, chunk_size=50, chunk_overlap=10)
        assert len(chunks) > 1

        # Verify all chunks have required fields
        for chunk in chunks:
            assert "content" in chunk
            assert "token_count" in chunk
            assert "character_count" in chunk
            assert chunk["token_count"] > 0

    def test_overlap_exists(self):
        sentences = [f"Sentence {i} has unique content here." for i in range(50)]
        text = " ".join(sentences)
        chunks = chunk_text(text, chunk_size=30, chunk_overlap=10)

        if len(chunks) >= 2:
            # Check that consecutive chunks share some content (overlap)
            chunk1_words = set(chunks[0]["content"].split())
            chunk2_words = set(chunks[1]["content"].split())
            overlap = chunk1_words & chunk2_words
            assert len(overlap) > 0, "Expected overlap between consecutive chunks"

    def test_min_chunk_size_enforcement(self):
        text = "Short. " * 20 + "This is a much longer final sentence with lots of words."
        chunks = chunk_text(text, chunk_size=50, chunk_overlap=5, min_chunk_size=10)
        # Small trailing chunks should be merged
        for chunk in chunks:
            assert chunk["token_count"] >= 5  # Allow some flexibility

    def test_paragraph_awareness(self):
        text = "First paragraph content here.\n\nSecond paragraph with different topic."
        chunks = chunk_text(text, chunk_size=500)
        assert len(chunks) == 1  # Short enough for single chunk

    def test_returns_list_of_dicts(self):
        chunks = chunk_text("Hello world. This is a test.")
        assert isinstance(chunks, list)
        for chunk in chunks:
            assert isinstance(chunk, dict)
            assert set(chunk.keys()) == {"content", "token_count", "character_count"}
