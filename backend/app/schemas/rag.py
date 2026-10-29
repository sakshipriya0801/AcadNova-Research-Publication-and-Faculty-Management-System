"""Pydantic schemas for the RAG foundation (Step 15A).

Responses deliberately omit embeddings, filesystem paths and internal storage
fields.  The chunk listing endpoint is a debugging aid, not the future chat
API.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


def _clean_query(value: str) -> str:
    text = (value or "").strip()
    if not text:
        raise ValueError("query must not be empty")
    return text


class RagProcessingStatusResponse(BaseModel):
    document_id: str
    rag_status: str = "pending"
    rag_error: Optional[str] = None
    chunk_count: Optional[int] = None
    embedding_count: Optional[int] = None
    processing_version: Optional[str] = None
    processed_at: Optional[datetime] = None
    embedding_model: Optional[str] = None


class RagChunkResponse(BaseModel):
    chunk_index: int
    text: str
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    character_count: Optional[int] = None
    word_count: Optional[int] = None
    token_count: Optional[int] = None


class RagChunkListResponse(BaseModel):
    document_id: str
    chunk_count: int
    chunks: list[RagChunkResponse] = Field(default_factory=list)


class RagRetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    publication_id: Optional[str] = None
    document_id: Optional[str] = None
    top_k: Optional[int] = Field(default=None, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def _validate_query(cls, value: str) -> str:
        return _clean_query(value)


class RagRetrievalResult(BaseModel):
    document_id: Optional[str] = None
    publication_id: Optional[str] = None
    chunk_index: Optional[int] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    relevance_score: Optional[float] = None
    text: str = ""


class RagRetrieveResponse(BaseModel):
    query: str
    top_k: int
    retrieved_chunks: int
    search_mode: str
    embedding_model: Optional[str] = None
    results: list[RagRetrievalResult] = Field(default_factory=list)


class RagQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    publication_id: Optional[str] = None
    document_id: Optional[str] = None
    top_k: Optional[int] = Field(default=None, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def _validate_query(cls, value: str) -> str:
        return _clean_query(value)


class RagSource(BaseModel):
    document_id: Optional[str] = None
    publication_id: Optional[str] = None
    chunk_index: Optional[int] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    relevance_score: Optional[float] = None


class RagQueryResponse(BaseModel):
    answer: str
    sources: list[RagSource] = Field(default_factory=list)
    retrieved_chunks: int = 0
    model: Optional[str] = None
    processing_time_ms: int = 0
