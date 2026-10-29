"""RAG question-answering orchestration.

Pipeline: validate → embed/retrieve → relevance filter → build context →
grounded LLM → validate answer → return answer + real sources.

Each request is independent — there is no conversation history or memory.
Orchestration lives here, not in the route handler.
"""

import logging
import time

from app.config.settings import get_settings
from app.services.rag import context_builder, llm_service, prompts, retrieval_service

logger = logging.getLogger(__name__)

_SOURCE_FIELDS = (
    "document_id",
    "publication_id",
    "chunk_index",
    "page_start",
    "page_end",
    "relevance_score",
)


def _elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def _no_answer(start: float) -> dict:
    return {
        "answer": prompts.NO_ANSWER_MESSAGE,
        "sources": [],
        "retrieved_chunks": 0,
        "model": None,
        "processing_time_ms": _elapsed_ms(start),
    }


def _sources(context: list[dict]) -> list[dict]:
    return [{field: item.get(field) for field in _SOURCE_FIELDS} for item in context]


def _validate_answer(answer: str, sources: list[dict], retrieved_ids: set) -> str:
    """Reject unverified answers; every source must map to a retrieved chunk."""
    if not answer or not answer.strip():
        raise llm_service.LLMError("Unable to generate an AI response right now.")
    for source in sources:
        if source.get("document_id") and source["document_id"] not in retrieved_ids:
            raise llm_service.LLMError("Unable to generate an AI response right now.")
    return answer.strip()


def answer_question(
    query: str,
    faculty_id: str | None = None,
    publication_id: str | None = None,
    document_id: str | None = None,
    top_k: int | None = None,
    llm_provider=None,
) -> dict:
    """Answer ``query`` strictly from the caller's retrievable documents.

    ``faculty_id`` is a hard ownership scope derived from the session; it is
    never taken from request input.
    """
    start = time.perf_counter()
    query = (query or "").strip()
    if not query:
        raise ValueError("query must not be empty")

    settings = get_settings()
    retrieval = retrieval_service.retrieve(
        query=query,
        faculty_id=faculty_id,
        publication_id=publication_id,
        document_id=document_id,
        top_k=top_k,
    )

    results = retrieval.get("results") or []
    # ``retrieval_service`` already applied RAG_MIN_RELEVANCE_SCORE.
    if not results:
        return _no_answer(start)

    context = context_builder.build_context(
        results, max_words=int(settings.rag_max_context_words)
    )
    if not context:
        return _no_answer(start)

    generated = llm_service.generate_answer(query, context, provider=llm_provider)
    sources = _sources(context)
    answer = _validate_answer(
        generated.get("answer", ""), sources, {r.get("document_id") for r in results}
    )

    elapsed = _elapsed_ms(start)
    logger.info(
        "rag.query retrieved=%d context=%d model=%s elapsed_ms=%d",
        len(results),
        len(context),
        generated.get("model"),
        elapsed,
    )
    return {
        "answer": answer,
        "sources": sources,
        "retrieved_chunks": len(context),
        "model": generated.get("model"),
        "processing_time_ms": elapsed,
    }
