"""Non-destructive text cleaning for RAG indexing.

Academic PDFs contain headings, equations, citations and references.  Cleaning
must therefore normalise whitespace only and never discard meaningful content.
"""

import re
import unicodedata

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_INLINE_SPACE = re.compile(r"[ \t\u00a0\u2000-\u200a\u202f\u205f\u3000]+")
_EXCESS_BLANK_LINES = re.compile(r"\n{3,}")


def clean_text(text: str) -> str:
    """Normalise whitespace and line endings without changing meaning.

    - unifies line endings and Unicode forms
    - collapses runs of spaces/tabs to a single space
    - strips control characters except newlines
    - limits blank lines to at most one between blocks
    - preserves punctuation, math symbols, headings and citations
    """
    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL_CHARS.sub("", text)

    lines = [_INLINE_SPACE.sub(" ", line).strip() for line in text.split("\n")]
    cleaned = "\n".join(lines)
    cleaned = _EXCESS_BLANK_LINES.sub("\n\n", cleaned)
    return cleaned.strip()


def clean_pages(pages: list[dict]) -> list[dict]:
    """Return page dicts with cleaned text, preserving page numbers.

    Pages that become empty after cleaning are dropped so that they do not
    produce empty chunks, but their page numbers are still represented by the
    remaining pages around them.
    """
    cleaned: list[dict] = []
    for page in pages or []:
        number = page.get("page_number")
        text = clean_text(page.get("text") or "")
        if text:
            cleaned.append({"page_number": number, "text": text})
    return cleaned
