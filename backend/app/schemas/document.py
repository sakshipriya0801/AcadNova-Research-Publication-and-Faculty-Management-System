"""Uploaded publication document metadata schema."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.enums import DocumentStatus, DocumentType, ProcessingStatus
from app.schemas.common import MongoDocument, utcnow


class Document(MongoDocument):
    document_id: Optional[str] = None
    publication_id: str
    faculty_id: Optional[str] = None
    document_type: DocumentType = DocumentType.OTHER
    original_filename: str
    stored_filename: str
    storage_path: str
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    checksum: Optional[str] = None
    uploaded_by_user_id: Optional[str] = None
    status: DocumentStatus = DocumentStatus.ACTIVE
    processing_status: ProcessingStatus = ProcessingStatus.NOT_PROCESSED
    processing_error: Optional[str] = None
    page_count: Optional[int] = None
    extracted_text_length: Optional[int] = None
    extracted_at: Optional[datetime] = None
    metadata: Optional[dict[str, Any]] = None
    created_at: Optional[datetime] = Field(default_factory=utcnow)
    updated_at: Optional[datetime] = Field(default_factory=utcnow)


class DocumentResponse(BaseModel):
    """Safe document metadata (no physical storage paths)."""

    id: str
    publication_id: str
    document_type: str
    original_filename: str
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    checksum: Optional[str] = None
    status: str
    processing_status: str = "not_processed"
    uploaded_by_user_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


def document_response(document: dict) -> DocumentResponse:
    return DocumentResponse(
        id=document.get("document_id"),
        publication_id=document.get("publication_id"),
        document_type=document.get("document_type"),
        original_filename=document.get("original_filename"),
        mime_type=document.get("mime_type"),
        file_size=document.get("file_size"),
        checksum=document.get("checksum"),
        status=document.get("status", "active"),
        processing_status=document.get("processing_status", "not_processed"),
        uploaded_by_user_id=document.get("uploaded_by_user_id"),
        created_at=document.get("created_at"),
        updated_at=document.get("updated_at"),
    )
