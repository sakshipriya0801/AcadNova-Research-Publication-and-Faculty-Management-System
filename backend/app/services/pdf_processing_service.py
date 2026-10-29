"""PDF text extraction and document processing.

Uses PyMuPDF locally to extract page-aware text and PDF metadata from uploaded
documents.  Extracted text is stored in a separate ``document_contents``
collection to avoid bloating the main document record.
"""

import re
from datetime import datetime, timezone
from typing import Optional

import pymupdf
from fastapi import HTTPException, status
from pymongo import ReturnDocument

from app.database import mongodb
from app.models.collections import DOCUMENT_CONTENTS, DOCUMENTS
from app.models.enums import ProcessingStatus
from app.services import document_service

EXTRACTION_METHOD = "pymupdf"


class ProcessingError(Exception):
    def __init__(self, message: str, status_code: int = 422):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _documents():
    return mongodb.get_collection(DOCUMENTS)


def _contents():
    return mongodb.get_collection(DOCUMENT_CONTENTS)


def _clean(value) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_text(text: str) -> str:
    """Normalize whitespace/line breaks while preserving page text faithfully."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]

    result: list[str] = []
    blank_run = 0
    for line in lines:
        if line == "":
            blank_run += 1
            if blank_run <= 1:
                result.append("")
        else:
            blank_run = 0
            result.append(line)
    return "\n".join(result).strip()


def _extract(path) -> dict:
    try:
        pdf = pymupdf.open(path)
    except Exception:
        raise ProcessingError("Invalid or corrupted PDF")

    try:
        if pdf.needs_pass:
            raise ProcessingError("Encrypted or password-protected PDF is not supported")
        if pdf.page_count == 0:
            raise ProcessingError("PDF contains no pages")

        raw = pdf.metadata or {}
        metadata = {
            "title": _clean(raw.get("title")),
            "author": _clean(raw.get("author")),
            "subject": _clean(raw.get("subject")),
            "keywords": _clean(raw.get("keywords")),
            "creator": _clean(raw.get("creator")),
            "producer": _clean(raw.get("producer")),
            "creation_date": _clean(raw.get("creationDate")),
            "modification_date": _clean(raw.get("modDate")),
        }

        pages: list[dict] = []
        pages_with_text = 0
        pages_without_text = 0
        for page_num in range(pdf.page_count):
            page = pdf.load_page(page_num)
            page_text = normalize_text(page.get_text("text"))
            pages.append({"page_number": page_num + 1, "text": page_text})
            if page_text:
                pages_with_text += 1
            else:
                pages_without_text += 1

        full_text = "\n\n".join(p["text"] for p in pages).strip()
        quality = "low" if pages_without_text > pages_with_text else "normal"

        return {
            "metadata": metadata,
            "pages": pages,
            "full_text": full_text,
            "text_length": len(full_text),
            "page_count": pdf.page_count,
            "quality": quality,
        }
    finally:
        pdf.close()


def _update_document(document_id: str, fields: dict) -> dict:
    fields["updated_at"] = datetime.now(timezone.utc)
    return _documents().find_one_and_update(
        {"document_id": document_id},
        {"$set": fields},
        return_document=ReturnDocument.AFTER,
    )


def process_document(document_id: str) -> dict:
    document = document_service.get_document(document_id)
    if document is None or document.get("status") == "deleted":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")

    _update_document(
        document_id,
        {"processing_status": ProcessingStatus.PROCESSING.value, "processing_error": None},
    )

    path = document_service.resolve_document_path(document)
    if not path.exists():
        _update_document(
            document_id,
            {
                "processing_status": ProcessingStatus.FAILED.value,
                "processing_error": "Stored file is missing",
            },
        )
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document file not found")

    try:
        result = _extract(path)
    except ProcessingError as exc:
        _update_document(
            document_id,
            {
                "processing_status": ProcessingStatus.FAILED.value,
                "processing_error": exc.message,
            },
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except Exception:
        _update_document(
            document_id,
            {
                "processing_status": ProcessingStatus.FAILED.value,
                "processing_error": "PDF processing failed",
            },
        )
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "PDF processing failed")

    now = datetime.now(timezone.utc)
    _contents().update_one(
        {"document_id": document_id},
        {
            "$set": {
                "document_id": document_id,
                "publication_id": document.get("publication_id"),
                "faculty_id": document.get("faculty_id"),
                "text": result["full_text"],
                "text_length": result["text_length"],
                "page_count": result["page_count"],
                "pages": result["pages"],
                "extraction_method": EXTRACTION_METHOD,
                "text_extraction_quality": result["quality"],
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )

    return _update_document(
        document_id,
        {
            "processing_status": ProcessingStatus.PROCESSED.value,
            "processing_error": None,
            "page_count": result["page_count"],
            "extracted_text_length": result["text_length"],
            "extracted_at": now,
            "metadata": result["metadata"],
        },
    )


def get_processing_status(document: dict) -> dict:
    return {
        "document_id": document.get("document_id"),
        "processing_status": document.get("processing_status", "not_processed"),
        "processing_error": document.get("processing_error"),
        "page_count": document.get("page_count"),
        "extracted_text_length": document.get("extracted_text_length"),
        "extracted_at": document.get("extracted_at"),
    }


def get_extracted_content(document_id: str) -> Optional[dict]:
    return _contents().find_one({"document_id": document_id})


def get_document_metadata(document: dict) -> dict:
    meta = document.get("metadata") or {}
    return {
        "title": meta.get("title"),
        "author": meta.get("author"),
        "subject": meta.get("subject"),
        "keywords": meta.get("keywords"),
        "creator": meta.get("creator"),
        "producer": meta.get("producer"),
        "creation_date": meta.get("creation_date"),
        "modification_date": meta.get("modification_date"),
        "page_count": document.get("page_count"),
    }
