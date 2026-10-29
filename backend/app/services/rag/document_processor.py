"""Knowledge-base (RAG) processing pipeline for a document.

Reuses the Step 13 PDF extraction and then cleans, chunks, embeds and stores
the text as knowledge chunks.  Processing is idempotent: re-running replaces a
document's chunks rather than duplicating them.  Failures leave the document
in a terminal ``failed`` state with a safe message (never stuck in
``processing``).
"""

import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status
from pymongo import ReturnDocument

from app.config.settings import get_settings
from app.database import mongodb
from app.models.collections import DOCUMENTS
from app.models.enums import RagProcessingStatus
from app.services import document_service, pdf_processing_service
from app.services.rag import chunker, embedding_service, text_cleaner, vector_store

logger = logging.getLogger(__name__)

PROCESSING_VERSION = "1"
EMPTY_TEXT_MESSAGE = "PDF contains no extractable text; OCR is not enabled."


def _documents():
    return mongodb.get_collection(DOCUMENTS)


def _update(document_id: str, fields: dict) -> dict:
    fields["updated_at"] = datetime.now(timezone.utc)
    return _documents().find_one_and_update(
        {"document_id": document_id},
        {"$set": fields},
        return_document=ReturnDocument.AFTER,
    )


def _valid_vectors(vectors) -> bool:
    """Return True only for a non-empty batch of equal-length numeric vectors."""
    if not isinstance(vectors, (list, tuple)) or not vectors:
        return False
    length = None
    for vector in vectors:
        if not isinstance(vector, (list, tuple)) or not vector:
            return False
        if not all(
            isinstance(value, (int, float)) and not isinstance(value, bool)
            for value in vector
        ):
            return False
        if length is None:
            length = len(vector)
        elif len(vector) != length:
            return False
    return True


def _fail(document_id: str, message: str) -> dict:
    """Mark processing failed and drop any stale chunks for consistency."""
    vector_store.delete_document(document_id)
    updated = _update(
        document_id,
        {
            "rag_status": RagProcessingStatus.FAILED.value,
            "rag_error": message,
            "rag_processed_at": datetime.now(timezone.utc),
            "rag_chunk_count": 0,
            "rag_embedding_count": 0,
        },
    )
    return get_rag_status(updated)


def get_rag_status(document: dict) -> dict:
    return {
        "document_id": document.get("document_id"),
        "rag_status": document.get("rag_status", RagProcessingStatus.PENDING.value),
        "rag_error": document.get("rag_error"),
        "chunk_count": document.get("rag_chunk_count"),
        "embedding_count": document.get("rag_embedding_count"),
        "processing_version": document.get("rag_processing_version"),
        "processed_at": document.get("rag_processed_at"),
        "embedding_model": document.get("rag_embedding_model"),
    }


def _extracted_pages(document_id: str) -> list[dict]:
    """Return extracted pages, running Step 13 extraction if not done yet."""
    content = pdf_processing_service.get_extracted_content(document_id)
    if content is None:
        pdf_processing_service.process_document(document_id)
        content = pdf_processing_service.get_extracted_content(document_id)
    return (content or {}).get("pages") or []


def process_document_knowledge(document_id: str) -> dict:
    """Run the full clean → chunk → embed → store pipeline for a document."""
    document = document_service.get_document(document_id)
    if document is None or document.get("status") == "deleted":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")

    _update(
        document_id,
        {
            "rag_status": RagProcessingStatus.PROCESSING.value,
            "rag_error": None,
        },
    )

    try:
        settings = get_settings()
        pages = _extracted_pages(document_id)
        cleaned_pages = text_cleaner.clean_pages(pages)
        cleaned_text = "\n\n".join(page["text"] for page in cleaned_pages).strip()
        if not cleaned_text:
            return _fail(document_id, EMPTY_TEXT_MESSAGE)

        chunks = chunker.chunk_pages(
            cleaned_pages,
            chunk_size=int(settings.rag_chunk_size),
            overlap=int(settings.rag_chunk_overlap),
        )
        if not chunks:
            return _fail(document_id, EMPTY_TEXT_MESSAGE)

        provider = embedding_service.get_embedding_provider()
        vectors = embedding_service.embed_texts([chunk.text for chunk in chunks])
        if len(vectors) != len(chunks) or not _valid_vectors(vectors):
            return _fail(document_id, "Embedding generation failed.")

        records = [
            {
                "chunk_id": f"{document_id}:{chunk.chunk_index}",
                "document_id": document_id,
                "publication_id": document.get("publication_id"),
                "faculty_id": document.get("faculty_id"),
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "character_count": chunk.character_count,
                "word_count": chunk.word_count,
                "token_count": chunk.token_count,
                "embedding": vector,
                "embedding_model": provider.model_name,
                "processing_version": PROCESSING_VERSION,
            }
            for chunk, vector in zip(chunks, vectors)
        ]
        stored = vector_store.upsert_document_chunks(document_id, records)
        now = datetime.now(timezone.utc)
        updated = _update(
            document_id,
            {
                "rag_status": RagProcessingStatus.COMPLETED.value,
                "rag_error": None,
                "rag_processed_at": now,
                "rag_chunk_count": len(chunks),
                "rag_embedding_count": stored,
                "rag_processing_version": PROCESSING_VERSION,
                "rag_embedding_model": provider.model_name,
            },
        )
        return get_rag_status(updated)

    except embedding_service.EmbeddingConfigurationError as exc:
        return _fail(document_id, str(exc))
    except embedding_service.EmbeddingError:
        return _fail(document_id, "Embedding generation failed.")
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, str) else "PDF processing failed"
        return _fail(document_id, detail)
    except Exception as exc:  # unexpected — never leak internals
        logger.warning(
            "RAG processing failed for document %s (%s)",
            document_id,
            type(exc).__name__,
        )
        return _fail(document_id, "Document processing failed.")


def list_chunks(document_id: str) -> list[dict]:
    """Return safe chunk metadata for a document (no embeddings)."""
    return vector_store.list_document_chunks(document_id)
