from app.utils.tokenizer import count_tokens, truncate_to_tokens


class TestTokenizer:
    def test_count_tokens_simple(self):
        count = count_tokens("Hello, world!")
        assert count > 0
        assert count < 10

    def test_count_tokens_empty(self):
        assert count_tokens("") == 0

    def test_count_tokens_longer_text(self):
        text = "This is a longer piece of text that should have more tokens."
        count = count_tokens(text)
        assert count > 5

    def test_truncate_short_text(self):
        text = "Short text."
        result = truncate_to_tokens(text, max_tokens=100)
        assert result == text

    def test_truncate_long_text(self):
        text = " ".join(["word"] * 1000)
        result = truncate_to_tokens(text, max_tokens=10)
        result_tokens = count_tokens(result)
        assert result_tokens <= 10
