"""Context assembly for RAG answer generation.

Orders retrieved chunks by relevance, removes obvious duplicates, enforces a
maximum context size (in words) and keeps only the metadata the LLM needs.
Embeddings, filesystem paths and internal database fields are never included.
"""

from app.config.settings import get_settings

_SAFE_FIELDS = (
    "document_id",
    "publication_id",
    "chunk_index",
    "page_start",
    "page_end",
    "relevance_score",
)


def _normalize(text: str) -> str:
    return " ".join((text or "").lower().split())


def build_context(
    retrieval_results: list[dict],
    max_words: int | None = None,
) -> list[dict]:
    """Return an ordered, de-duplicated, size-limited list of context items."""
    settings = get_settings()
    budget = int(max_words if max_words is not None else settings.rag_max_context_words)
    if budget <= 0:
        return []

    ordered = sorted(
        retrieval_results or [],
        key=lambda item: float(item.get("relevance_score") or 0.0),
        reverse=True,
    )

    context: list[dict] = []
    seen: set[str] = set()
    used_words = 0

    for item in ordered:
        text = (item.get("text") or "").strip()
        if not text:
            continue

        normalized = _normalize(text)
        if normalized in seen:
            continue

        remaining = budget - used_words
        if remaining <= 0:
            break

        words = text.split()
        if len(words) > remaining:
            text = " ".join(words[:remaining]) + " …"
            words = words[:remaining]

        seen.add(normalized)
        block = {field: item.get(field) for field in _SAFE_FIELDS}
        block["text"] = text
        context.append(block)
        used_words += len(words)

    return context
