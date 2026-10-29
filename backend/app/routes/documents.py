"""Publication document routes."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.models.enums import DocumentType
from app.routes import dependencies
from app.routes.admin import _audit
from app.schemas.document import DocumentResponse, document_response
from app.schemas.pdf_processing import (
    DocumentMetadataResponse,
    ExtractedContentResponse,
    ExtractedPage,
    ProcessingStatusResponse,
)
from app.schemas.rag import (
    RagChunkListResponse,
    RagChunkResponse,
    RagProcessingStatusResponse,
)
from app.services import document_service, pdf_processing_service, publication_service
from app.services.rag import document_processor

router = APIRouter(prefix="/api/publications/{publication_id}/documents", tags=["documents"])


def _load_publication(publication_id: str) -> dict:
    publication = publication_service.find_publication_by_id(publication_id)
    if publication is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Publication not found")
    return publication


def _can_access(user: dict, publication: dict) -> bool:
    if user.get("role") == "admin":
        return True
    return publication.get("faculty_id") == user.get("faculty_id")


def _require_access(user: dict, publication: dict) -> None:
    if not _can_access(user, publication):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "You do not have access to this publication",
        )


def _load_active_document(publication_id: str, document_id: str, user: dict) -> dict:
    publication = _load_publication(publication_id)
    _require_access(user, publication)
    document = document_service.get_document(document_id)
    if document is None or document.get("publication_id") != publication_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    if document.get("status") == "deleted":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return document


def _status_response(document: dict) -> ProcessingStatusResponse:
    status_info = pdf_processing_service.get_processing_status(document)
    return ProcessingStatusResponse(**status_info)


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    publication_id: str,
    document_type: DocumentType = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(dependencies.require_authenticated_user),
) -> DocumentResponse:
    publication = _load_publication(publication_id)
    _require_access(user, publication)

    document = await document_service.save_document(
        publication_id=publication_id,
        faculty_id=publication.get("faculty_id"),
        user_id=user.get("user_id"),
        document_type=document_type,
        upload_file=file,
    )
    _audit.log(
        user,
        "document.upload",
        "document",
        document["document_id"],
        new_value={"publication_id": publication_id, "document_type": document_type.value},
    )
    return document_response(document)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    publication_id: str,
    user: dict = Depends(dependencies.require_authenticated_user),
) -> list[DocumentResponse]:
    publication = _load_publication(publication_id)
    _require_access(user, publication)
    documents = document_service.list_documents(publication_id)
    return [document_response(d) for d in documents]


@router.get("/{document_id}/download")
async def download_document(
    publication_id: str,
    document_id: str,
    user: dict = Depends(dependencies.require_authenticated_user),
):
    publication = _load_publication(publication_id)
    _require_access(user, publication)

    document = document_service.get_document(document_id)
    if document is None or document.get("publication_id") != publication_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    if document.get("status") != "active":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")

    path = document_service.resolve_document_path(document)
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document file not found")

    filename = document_service.sanitize_filename(document.get("original_filename"))
    return FileResponse(
        path,
        media_type=document.get("mime_type") or "application/pdf",
        filename=filename,
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    publication_id: str,
    document_id: str,
    user: dict = Depends(dependencies.require_authenticated_user),
) -> None:
    publication = _load_publication(publication_id)
    _require_access(user, publication)

    document = document_service.get_document(document_id)
    if document is None or document.get("publication_id") != publication_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    if document.get("status") == "deleted":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")

    document_service.soft_delete_document(document_id)
    _audit.log(
        user,
        "document.delete",
        "document",
        document_id,
        old_value={"status": "active"},
        new_value={"status": "deleted"},
    )
    return None


@router.post("/{document_id}/process", response_model=ProcessingStatusResponse)
async def process_document(
    publication_id: str,
    document_id: str,
    user: dict = Depends(dependencies.require_authenticated_user),
) -> ProcessingStatusResponse:
    _load_active_document(publication_id, document_id, user)
    updated = pdf_processing_service.process_document(document_id)
    return _status_response(updated)


@router.get("/{document_id}/processing-status", response_model=ProcessingStatusResponse)
async def document_processing_status(
    publication_id: str,
    document_id: str,
    user: dict = Depends(dependencies.require_authenticated_user),
) -> ProcessingStatusResponse:
    document = _load_active_document(publication_id, document_id, user)
    return _status_response(document)


@router.get("/{document_id}/content", response_model=ExtractedContentResponse)
async def document_content(
    publication_id: str,
    document_id: str,
    user: dict = Depends(dependencies.require_authenticated_user),
) -> ExtractedContentResponse:
    _load_active_document(publication_id, document_id, user)
    content = pdf_processing_service.get_extracted_content(document_id)
    if content is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Extracted content not found")
    return ExtractedContentResponse(
        document_id=content.get("document_id"),
        publication_id=content.get("publication_id"),
        page_count=content.get("page_count", 0),
        text_length=content.get("text_length", 0),
        extraction_method=content.get("extraction_method", "pymupdf"),
        pages=[
            ExtractedPage(page_number=p.get("page_number"), text=p.get("text", ""))
            for p in content.get("pages", [])
        ],
    )


@router.get("/{document_id}/metadata", response_model=DocumentMetadataResponse)
async def document_metadata(
    publication_id: str,
    document_id: str,
    user: dict = Depends(dependencies.require_authenticated_user),
) -> DocumentMetadataResponse:
    document = _load_active_document(publication_id, document_id, user)
    return DocumentMetadataResponse(**pdf_processing_service.get_document_metadata(document))


@router.post(
    "/{document_id}/knowledge/process",
    response_model=RagProcessingStatusResponse,
)
async def process_document_knowledge(
    publication_id: str,
    document_id: str,
    user: dict = Depends(dependencies.require_authenticated_user),
) -> RagProcessingStatusResponse:
    _load_active_document(publication_id, document_id, user)
    status_info = document_processor.process_document_knowledge(document_id)
    return RagProcessingStatusResponse(**status_info)


@router.get(
    "/{document_id}/knowledge/status",
    response_model=RagProcessingStatusResponse,
)
async def document_knowledge_status(
    publication_id: str,
    document_id: str,
    user: dict = Depends(dependencies.require_authenticated_user),
) -> RagProcessingStatusResponse:
    document = _load_active_document(publication_id, document_id, user)
    return RagProcessingStatusResponse(**document_processor.get_rag_status(document))


@router.get(
    "/{document_id}/knowledge/chunks",
    response_model=RagChunkListResponse,
)
async def document_knowledge_chunks(
    publication_id: str,
    document_id: str,
    user: dict = Depends(dependencies.require_authenticated_user),
) -> RagChunkListResponse:
    _load_active_document(publication_id, document_id, user)
    chunks = document_processor.list_chunks(document_id)
    return RagChunkListResponse(
        document_id=document_id,
        chunk_count=len(chunks),
        chunks=[
            RagChunkResponse(
                chunk_index=chunk.get("chunk_index", 0),
                text=chunk.get("text", ""),
                page_start=chunk.get("page_start"),
                page_end=chunk.get("page_end"),
                character_count=chunk.get("character_count"),
                word_count=chunk.get("word_count"),
                token_count=chunk.get("token_count"),
            )
            for chunk in chunks
        ],
    )
