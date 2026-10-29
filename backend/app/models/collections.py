"""MongoDB collection names and index definitions.

Indexes are defined here as data representation so the database layer can
create them uniformly.  Optional-unique fields use ``partialFilterExpression``
so that missing/null values are not indexed, preventing MongoDB from wrongly
rejecting multiple records that happen to share a null value.
"""

from pymongo import ASCENDING, DESCENDING, IndexModel

# --- Collection names -------------------------------------------------------
USERS = "users"
FACULTY = "faculty"
DEPARTMENTS = "departments"
ACADEMIC_YEARS = "academic_years"
PUBLICATIONS = "publications"
PUBLICATION_RULES = "publication_rules"
ELIGIBILITY_RULES = "eligibility_rules"
FACULTY_POINTS = "faculty_points"
VERIFICATION_RECORDS = "verification_records"
DOCUMENTS = "documents"
DOCUMENT_CONTENTS = "document_contents"
DOCUMENT_CHUNKS = "document_chunks"
ADMIN_INVITATIONS = "admin_invitations"
AUDIT_LOGS = "audit_logs"

COLLECTIONS: list[str] = [
    USERS,
    FACULTY,
    DEPARTMENTS,
    ACADEMIC_YEARS,
    PUBLICATIONS,
    PUBLICATION_RULES,
    ELIGIBILITY_RULES,
    FACULTY_POINTS,
    VERIFICATION_RECORDS,
    DOCUMENTS,
    DOCUMENT_CONTENTS,
    DOCUMENT_CHUNKS,
    ADMIN_INVITATIONS,
    AUDIT_LOGS,
]

# --- Index definitions ------------------------------------------------------
INDEXES: dict[str, list[IndexModel]] = {
    USERS: [
        IndexModel(
            [("email", ASCENDING)],
            name="email_unique",
            unique=True,
            partialFilterExpression={"email": {"$type": "string"}},
        ),
        IndexModel(
            [("user_id", ASCENDING)],
            name="user_id_unique",
            unique=True,
            partialFilterExpression={"user_id": {"$type": "string"}},
        ),
    ],
    DEPARTMENTS: [
        IndexModel(
            [("code", ASCENDING)],
            name="code_unique",
            unique=True,
            partialFilterExpression={"code": {"$type": "string"}},
        ),
    ],
    FACULTY: [
        IndexModel(
            [("employee_id", ASCENDING)],
            name="employee_id_unique",
            unique=True,
            partialFilterExpression={"employee_id": {"$type": "string"}},
        ),
        IndexModel([("email", ASCENDING)], name="email_unique", unique=True),
        IndexModel(
            [("orcid_id", ASCENDING)],
            name="orcid_id_unique",
            unique=True,
            partialFilterExpression={"orcid_id": {"$type": "string"}},
        ),
        IndexModel(
            [("scopus_author_id", ASCENDING)],
            name="scopus_author_id_unique",
            unique=True,
            partialFilterExpression={"scopus_author_id": {"$type": "string"}},
        ),
    ],
    PUBLICATIONS: [
        IndexModel(
            [("doi", ASCENDING)],
            name="doi_unique",
            unique=True,
            partialFilterExpression={"doi": {"$type": "string"}},
        ),
        IndexModel([("faculty_id", ASCENDING)], name="faculty_id_idx"),
        IndexModel([("academic_year_id", ASCENDING)], name="academic_year_id_idx"),
        IndexModel([("publication_year", ASCENDING)], name="publication_year_idx"),
        IndexModel([("source", ASCENDING)], name="source_idx"),
        IndexModel([("source_record_id", ASCENDING)], name="source_record_id_idx"),
        IndexModel(
            [("verification_status", ASCENDING)], name="verification_status_idx"
        ),
        IndexModel(
            [("source", ASCENDING), ("source_record_id", ASCENDING)],
            name="source_source_record_id_unique",
            unique=True,
            partialFilterExpression={"source_record_id": {"$type": "string"}},
        ),
    ],
    ACADEMIC_YEARS: [
        IndexModel([("name", ASCENDING)], name="name_unique", unique=True),
        IndexModel([("is_current", ASCENDING)], name="is_current_idx"),
    ],
    FACULTY_POINTS: [
        IndexModel(
            [("faculty_id", ASCENDING), ("academic_year_id", ASCENDING)],
            name="faculty_academic_year_unique",
            unique=True,
        ),
    ],
    PUBLICATION_RULES: [
        IndexModel([("publication_type", ASCENDING)], name="publication_type_idx"),
        IndexModel([("indexing", ASCENDING)], name="indexing_idx"),
        IndexModel([("is_active", ASCENDING)], name="is_active_idx"),
        IndexModel([("rule_code", ASCENDING)], name="rule_code_unique", unique=True),
    ],
    ELIGIBILITY_RULES: [
        IndexModel(
            [("designation", ASCENDING)], name="designation_unique", unique=True
        ),
    ],
    VERIFICATION_RECORDS: [
        IndexModel([("publication_id", ASCENDING)], name="publication_id_idx"),
        IndexModel([("faculty_id", ASCENDING)], name="faculty_id_idx"),
        IndexModel([("created_at", DESCENDING)], name="created_at_idx"),
    ],
    DOCUMENT_CONTENTS: [
        IndexModel([("document_id", ASCENDING)], name="document_id_unique", unique=True),
    ],
    DOCUMENTS: [
        IndexModel(
            [("document_id", ASCENDING)],
            name="document_id_unique",
            unique=True,
            partialFilterExpression={"document_id": {"$type": "string"}},
        ),
        IndexModel([("publication_id", ASCENDING)], name="publication_id_idx"),
        IndexModel([("faculty_id", ASCENDING)], name="faculty_id_idx"),
    ],
    DOCUMENT_CHUNKS: [
        IndexModel([("document_id", ASCENDING)], name="document_id_idx"),
        IndexModel([("publication_id", ASCENDING)], name="publication_id_idx"),
        IndexModel([("faculty_id", ASCENDING)], name="faculty_id_idx"),
        IndexModel(
            [("document_id", ASCENDING), ("chunk_index", ASCENDING)],
            name="document_chunk_unique",
            unique=True,
        ),
    ],
    ADMIN_INVITATIONS: [
        IndexModel(
            [("token_hash", ASCENDING)],
            name="token_hash_unique",
            unique=True,
            partialFilterExpression={"token_hash": {"$type": "string"}},
        ),
        IndexModel(
            [("invitation_id", ASCENDING)],
            name="invitation_id_unique",
            unique=True,
        ),
        IndexModel([("expires_at", ASCENDING)], name="expires_at_idx"),
    ],
}
