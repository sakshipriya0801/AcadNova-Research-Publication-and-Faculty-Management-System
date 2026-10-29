"""PDF processing schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProcessingStatusResponse(BaseModel):
    document_id: str
    processing_status: str
    processing_error: Optional[str] = None
    page_count: Optional[int] = None
    extracted_text_length: Optional[int] = None
    extracted_at: Optional[datetime] = None


class ExtractedPage(BaseModel):
    page_number: int
    text: str


class ExtractedContentResponse(BaseModel):
    document_id: str
    publication_id: str
    page_count: int
    text_length: int
    extraction_method: str
    pages: list[ExtractedPage] = Field(default_factory=list)


class DocumentMetadataResponse(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    keywords: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None
    page_count: Optional[int] = None
