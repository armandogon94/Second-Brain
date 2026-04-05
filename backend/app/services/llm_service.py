from anthropic import AsyncAnthropic

from app.config import settings
from app.utils.logger import logger

_client: AsyncAnthropic | None = None

MODEL_MAP = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
}


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


async def generate_answer(
    query: str,
    context_chunks: list[dict],
    model_key: str = "haiku",
) -> dict:
    """Generate a RAG answer using Claude.

    Args:
        query: The user's question.
        context_chunks: List of dicts with 'content', 'source_type', 'source_id', 'title', 'score'.
        model_key: 'haiku' or 'sonnet'.

    Returns:
        Dict with 'answer', 'usage' (input_tokens, output_tokens).
    """
    client = _get_client()
    model = MODEL_MAP.get(model_key, MODEL_MAP["haiku"])

    # Format context
    context_parts: list[str] = []
    for i, chunk in enumerate(context_chunks, 1):
        source_label = chunk.get("title") or f"{chunk['source_type']}:{chunk['source_id']}"
        context_parts.append(
            f"[Source {i} — \"{source_label}\" ({chunk['source_type']})]\n{chunk['content']}"
        )

    context_text = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant notes found."

    system_prompt = (
        "You are Armando's personal knowledge assistant. You answer questions "
        "using his personal notes, bookmarks, and documents.\n\n"
        "RULES:\n"
        "1. ALWAYS check the provided context first.\n"
        "2. If the answer is found in the context, cite it explicitly: "
        '"According to your note \'[title]\' ..."\n'
        "3. If the context partially answers the question, use it and clearly "
        'mark any supplemental information: "From general knowledge: ..."\n'
        "4. If the context contains NO relevant information, say: "
        '"I didn\'t find anything about this in your notes." Then optionally '
        "offer general knowledge, clearly labeled.\n"
        "5. NEVER fabricate content that appears to come from the user's notes.\n"
        "6. When citing, reference by [Source N] identifier."
    )

    user_prompt = (
        f"Question: {query}\n\n"
        f"---\n\n"
        f"From your notes:\n\n"
        f"{context_text}\n\n"
        f"---\n\n"
        f"Based on the information above, answer the question. "
        f"Clearly distinguish what comes from the user's notes vs. general knowledge."
    )

    try:
        response = await client.messages.create(
            model=model,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        answer = response.content[0].text
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "model": model,
        }

        return {"answer": answer, "usage": usage}

    except Exception:
        logger.exception("LLM generation failed")
        return {
            "answer": "I'm sorry, I couldn't generate an answer right now. Please try again.",
            "usage": {},
        }
