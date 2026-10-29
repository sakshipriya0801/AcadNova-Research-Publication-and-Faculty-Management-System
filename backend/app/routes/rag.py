"""RAG knowledge retrieval endpoint (foundation — no answer generation).

Retrieval is scoped by the authenticated session: faculty members may only
search their own documents, while admins may search across all documents.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.routes import dependencies
from app.schemas.rag import (
    RagQueryRequest,
    RagQueryResponse,
    RagRetrieveRequest,
    RagRetrieveResponse,
    RagRetrievalResult,
    RagSource,
)
from app.services import document_service, publication_service
from app.services.rag import (
    embedding_service,
    llm_service,
    qa_service,
    retrieval_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag", tags=["rag"])

_FORBIDDEN = "You do not have permission to access these documents."
_NOT_FOUND = "Requested document or publication was not found."


def _authorize_scope(user: dict, publication_id: str | None, document_id: str | None) -> None:
    """Validate that the caller may target the requested publication/document."""
    role = user.get("role")
    faculty_id = user.get("faculty_id")

    if document_id:
        document = document_service.get_document(document_id)
        if document is None or document.get("status") == "deleted":
            raise HTTPException(status.HTTP_404_NOT_FOUND, _NOT_FOUND)
        if role != "admin" and document.get("faculty_id") != faculty_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, _FORBIDDEN)
        if publication_id and document.get("publication_id") != publication_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, _NOT_FOUND)

    if publication_id:
        publication = publication_service.find_publication_by_id(publication_id)
        if publication is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, _NOT_FOUND)
        if role != "admin" and publication.get("faculty_id") != faculty_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, _FORBIDDEN)


@router.post("/retrieve", response_model=RagRetrieveResponse)
async def retrieve_knowledge(
    request: RagRetrieveRequest,
    user: dict = Depends(dependencies.require_authenticated_user),
) -> RagRetrieveResponse:
    _authorize_scope(user, request.publication_id, request.document_id)

    faculty_scope = None
    if user.get("role") != "admin":
        faculty_scope = user.get("faculty_id")
        if not faculty_scope:
            raise HTTPException(status.HTTP_403_FORBIDDEN, _FORBIDDEN)

    try:
        result = retrieval_service.retrieve(
            query=request.query,
            faculty_id=faculty_scope,
            publication_id=request.publication_id,
            document_id=request.document_id,
            top_k=request.top_k,
        )
    except embedding_service.EmbeddingConfigurationError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "AI provider is not configured."
        )
    except embedding_service.EmbeddingError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "AI service is currently unavailable."
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error during RAG retrieval")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "AI service is currently unavailable."
        )

    return RagRetrieveResponse(
        query=result["query"],
        top_k=result["top_k"],
        retrieved_chunks=result["count"],
        search_mode=result["search_mode"],
        embedding_model=result.get("embedding_model"),
        results=[RagRetrievalResult(**item) for item in result["results"]],
    )


@router.post("/query", response_model=RagQueryResponse)
async def query_documents(
    request: RagQueryRequest,
    user: dict = Depends(dependencies.require_authenticated_user),
) -> RagQueryResponse:
    _authorize_scope(user, request.publication_id, request.document_id)

    faculty_scope = None
    if user.get("role") != "admin":
        faculty_scope = user.get("faculty_id")
        if not faculty_scope:
            raise HTTPException(status.HTTP_403_FORBIDDEN, _FORBIDDEN)

    try:
        result = qa_service.answer_question(
            query=request.query,
            faculty_id=faculty_scope,
            publication_id=request.publication_id,
            document_id=request.document_id,
            top_k=request.top_k,
        )
    except embedding_service.EmbeddingConfigurationError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "AI provider is not configured."
        )
    except llm_service.LLMConfigurationError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "AI provider is not configured."
        )
    except (embedding_service.EmbeddingError, llm_service.LLMUnavailableError):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "AI service is currently unavailable."
        )
    except llm_service.LLMError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Unable to generate an AI response right now.",
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error during RAG query")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Unable to generate an AI response right now.",
        )

    return RagQueryResponse(
        answer=result["answer"],
        sources=[RagSource(**source) for source in result["sources"]],
        retrieved_chunks=result["retrieved_chunks"],
        model=result.get("model"),
        processing_time_ms=result["processing_time_ms"],
    )
