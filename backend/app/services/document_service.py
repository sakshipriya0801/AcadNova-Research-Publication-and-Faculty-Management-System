"""Publication document storage and metadata management.

Files are stored on the local filesystem (not in MongoDB) under a configurable
root directory.  Physical filenames are server-generated UUIDs; the original
filename is kept only as metadata.  Soft-deletion is used.
"""

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, status, UploadFile
from pymongo import ReturnDocument

from app.config.settings import get_settings
from app.database import mongodb
from app.models.collections import DOCUMENTS
from app.models.enums import DocumentStatus, DocumentType, ProcessingStatus

_ALLOWED_EXTENSIONS = {".pdf"}
_PDF_SIGNATURE = b"%PDF-"
_CHUNK_SIZE = 1024 * 1024  # 1 MiB


def _collection():
    return mongodb.get_collection(DOCUMENTS)


def _storage_root() -> Path:
    settings = get_settings()
    root = Path(settings.document_storage_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _max_bytes() -> int:
    return int(get_settings().max_document_size_mb) * 1024 * 1024


def _validate_document_type(document_type) -> DocumentType:
    if isinstance(document_type, DocumentType):
        return document_type
    try:
        return DocumentType(str(document_type))
    except ValueError:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Invalid document type"
        )


def _validate_filename(filename: Optional[str]) -> str:
    if not filename:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Filename is required")
    # Strip any directory components to prevent path traversal from the name.
    basename = Path(filename).name
    if not basename:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid filename")
    ext = Path(basename).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unsupported file type '{ext}'. Only PDF files are allowed.",
        )
    return basename


async def save_document(
    publication_id: str,
    faculty_id: Optional[str],
    user_id: Optional[str],
    document_type,
    upload_file: UploadFile,
) -> dict:
    """Validate, store and record an uploaded publication document."""
    doc_type = _validate_document_type(document_type)
    original_filename = _validate_filename(upload_file.filename)

    # MIME type is a soft signal — magic bytes remain the authority.
    content_type = (upload_file.content_type or "").lower()
    if content_type and content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Unsupported MIME type; only PDF files are allowed",
        )

    # Read the PDF signature (never trust the client MIME type alone).
    signature = await upload_file.read(5)
    if signature != _PDF_SIGNATURE:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "File is not a valid PDF (invalid signature)",
        )

    stored_filename = f"{uuid4().hex}.pdf"
    root = _storage_root()
    dest = root / stored_filename
    max_bytes = _max_bytes()

    hasher = hashlib.sha256()
    hasher.update(signature)
    total_size = len(signature)

    try:
        with open(dest, "wb") as out:
            out.write(signature)
            while True:
                chunk = await upload_file.read(_CHUNK_SIZE)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > max_bytes:
                    raise HTTPException(
                        status.HTTP_413_CONTENT_TOO_LARGE,
                        "File exceeds the maximum allowed size",
                    )
                hasher.update(chunk)
                out.write(chunk)
    except HTTPException:
        dest.unlink(missing_ok=True)
        raise
    except Exception:
        dest.unlink(missing_ok=True)
        raise

    checksum = hasher.hexdigest()

    # Duplicate detection: same file already attached (active) to this publication.
    existing = _collection().find_one(
        {
            "publication_id": publication_id,
            "checksum": checksum,
            "status": DocumentStatus.ACTIVE.value,
        }
    )
    if existing is not None:
        dest.unlink(missing_ok=True)
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This document is already attached to the publication",
        )

    now = datetime.now(timezone.utc)
    document = {
        "document_id": str(uuid4()),
        "publication_id": publication_id,
        "faculty_id": faculty_id,
        "document_type": doc_type.value,
        "original_filename": original_filename,
        "stored_filename": stored_filename,
        "storage_path": stored_filename,
        "mime_type": upload_file.content_type or "application/pdf",
        "file_size": total_size,
        "checksum": checksum,
        "uploaded_by_user_id": user_id,
        "status": DocumentStatus.ACTIVE.value,
        "processing_status": ProcessingStatus.NOT_PROCESSED.value,
        "created_at": now,
        "updated_at": now,
    }
    _collection().insert_one(document)
    return document


def list_documents(publication_id: str) -> list[dict]:
    return list(
        _collection()
        .find(
            {
                "publication_id": publication_id,
                "status": DocumentStatus.ACTIVE.value,
            }
        )
        .sort("created_at", -1)
    )


def get_document(document_id: str) -> Optional[dict]:
    return _collection().find_one({"document_id": document_id})


def soft_delete_document(document_id: str) -> Optional[dict]:
    document = _collection().find_one_and_update(
        {"document_id": document_id},
        {
            "$set": {
                "status": DocumentStatus.DELETED.value,
                "updated_at": datetime.now(timezone.utc),
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    # Remove any knowledge-base chunks so deleted documents are never retrieved.
    # Imported lazily to avoid a circular import at module load time.
    try:
        from app.services.rag import vector_store

        vector_store.delete_document(document_id)
    except Exception:  # pragma: no cover - cleanup must never block deletion
        pass
    return document


def resolve_document_path(document: dict) -> Path:
    """Resolve a stored document's physical path (safe within storage root)."""
    root = _storage_root()
    storage_path = document.get("storage_path")
    if not storage_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document file not found")

    # Reject any path that attempts to escape the storage root.
    if Path(storage_path).is_absolute() or ".." in Path(storage_path).parts:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document file not found")

    full = (root / storage_path).resolve()
    if not str(full).startswith(str(root)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document file not found")
    return full


def sanitize_filename(filename: Optional[str]) -> str:
    """Return a safe filename for Content-Disposition."""
    if not filename:
        return "document.pdf"
    basename = Path(filename).name
    basename = re.sub(r"[\r\n\x00-\x1f\x7f]", "", basename)
    return basename or "document.pdf"
