"""Deterministic, page-aware chunking for RAG indexing.

Chunks are produced by sliding a word window of ``chunk_size`` with
``chunk_overlap`` words over the concatenated page text.  The algorithm is
purely deterministic: identical input text and configuration always yield
identical chunks (same order, boundaries and page metadata).
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Chunk:
    chunk_index: int
    text: str
    page_start: Optional[int]
    page_end: Optional[int]
    character_count: int
    word_count: int
    token_count: Optional[int] = None


def _words_with_pages(pages: list[dict]) -> list[tuple[str, Optional[int]]]:
    words: list[tuple[str, Optional[int]]] = []
    for page in pages or []:
        number = page.get("page_number")
        for token in (page.get("text") or "").split():
            words.append((token, number))
    return words


def chunk_pages(
    pages: list[dict],
    chunk_size: int,
    overlap: int,
) -> list[Chunk]:
    """Split page dicts into deterministic overlapping chunks.

    ``pages`` items are ``{"page_number": int, "text": str}``.  Overlap must be
    strictly smaller than the chunk size so that the window always advances.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and smaller than chunk_size")

    words = _words_with_pages(pages)
    if not words:
        return []

    step = chunk_size - overlap
    total = len(words)
    chunks: list[Chunk] = []
    start = 0
    index = 0
    while start < total:
        end = min(start + chunk_size, total)
        window = words[start:end]
        text = " ".join(token for token, _ in window)
        page_start = next((p for _, p in window if p is not None), None)
        page_end = next((p for _, p in reversed(window) if p is not None), None)
        chunks.append(
            Chunk(
                chunk_index=index,
                text=text,
                page_start=page_start,
                page_end=page_end,
                character_count=len(text),
                word_count=len(window),
            )
        )
        index += 1
        if end >= total:
            break
        start += step
    return chunks
