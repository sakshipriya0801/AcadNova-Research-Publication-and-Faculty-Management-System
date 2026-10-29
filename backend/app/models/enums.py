"""Enumerations used across the data models and schemas."""

from enum import Enum


class UserRole(str, Enum):
    FACULTY = "faculty"
    ADMIN = "admin"


class PublicationSource(str, Enum):
    MANUAL = "manual"
    PUBMED = "pubmed"
    CROSSREF = "crossref"
    ORCID = "orcid"
    SCOPUS = "scopus"
    WEB_OF_SCIENCE = "web_of_science"


class PublicationType(str, Enum):
    RESEARCH_PUBLICATION = "research_publication"
    COLLABORATIVE_PUBLICATION = "collaborative_publication"
    BOOK_EDITOR = "book_editor"
    BOOK_CHAPTER = "book_chapter"
    CONFERENCE_PROCEEDING = "conference_proceeding"
    PATENT = "patent"
    COPYRIGHT = "copyright"
    STARTUP = "startup"
    PROJECT = "project"
    CONSULTANCY = "consultancy"
    OTHER = "other"


class VerificationStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"


class DocumentType(str, Enum):
    RESEARCH_PAPER = "research_paper"
    CONFERENCE_PAPER = "conference_paper"
    BOOK_CHAPTER = "book_chapter"
    PATENT_DOCUMENT = "patent_document"
    COPYRIGHT_DOCUMENT = "copyright_document"
    SUPPORTING_EVIDENCE = "supporting_evidence"
    OTHER = "other"


class DocumentStatus(str, Enum):
    ACTIVE = "active"
    DELETED = "deleted"


class ProcessingStatus(str, Enum):
    NOT_PROCESSED = "not_processed"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class ApprovalStatus(str, Enum):
    """Faculty account approval state."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# Single-institute academic programs and designations (shared by admin
# faculty-creation validation and the frontend dropdowns).
DEPARTMENT_PROGRAMS = ("MCA", "BCA", "MBA", "BBA")
DESIGNATIONS = (
    "Professor",
    "Associate Professor",
    "Assistant Professor",
    "Lecturer",
    "Visiting Faculty",
)


class RagProcessingStatus(str, Enum):
    """Knowledge-base (RAG) processing state for a document."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
