# Database Design

Database: **MongoDB** — database name `research_faculty_db` (configurable via
`MONGODB_DATABASE`). Connection is managed by `app/database/mongodb.py`; index
creation runs at application startup (`create_indexes()`), and the health
endpoint pings the server.

## Collections (13)

| # | Collection | Purpose |
|---|---|---|
| 1 | `users` | Login identities and roles |
| 2 | `faculty` | Faculty profiles |
| 3 | `departments` | Departments |
| 4 | `academic_years` | Academic year windows (1 Jul → 30 Jun) |
| 5 | `publications` | Faculty publications |
| 6 | `publication_rules` | Institutional points rules |
| 7 | `eligibility_rules` | Increment eligibility thresholds by designation |
| 8 | `faculty_points` | Annual aggregated points per faculty |
| 9 | `verification_records` | Verification/rejection history |
| 10 | `documents` | Uploaded evidence metadata (+ RAG status) |
| 11 | `document_contents` | Extracted page-aware PDF text |
| 12 | `document_chunks` | RAG chunks + embeddings |
| 13 | `audit_logs` | Audit trail |

## Collection Schemas (principal fields)

### users
`user_id`, `email`, `password_hash` (bcrypt, never plaintext), `role`
(`faculty` | `admin`), `faculty_id` (nullable), `is_active`, `created_at`,
`updated_at`.
Indexes: `email_unique`, `user_id_unique`.

### faculty
`faculty_id`, `employee_id`, `name`, `email`, `department_id`, `designation`,
`orcid_id`, `scopus_author_id`, `web_of_science_researcher_id`, `pubmed_id`,
`research_interests`, `profile_photo_url`, `is_active`, `created_at`,
`updated_at`.
Indexes: `email_unique`, `employee_id_unique`, `orcid_id_unique`,
`scopus_author_id_unique` (unique, partial on string).

### departments
`department_id`, `code`, `name`, `description`, `is_active`, `created_at`,
`updated_at`. Index: `code_unique`.

### academic_years
`academic_year_id`, `name` (e.g. `2025-2026`), `start_date` (1 Jul),
`end_date` (30 Jun), `is_current`, timestamps.
Indexes: `name_unique`, `is_current_idx`.

### publications
`publication_id`, `title`, `authors[]`, `author_count`, `faculty_id`,
`faculty_author_position`, `is_corresponding_author`, `publication_type`,
`journal_name`, `conference_name`, `publisher`, `doi`, `issn`, `isbn`,
`volume`, `issue`, `pages`, `publication_date`, `publication_year`,
`abstract`, `keywords`, `source`, `source_record_id`, `source_url`, `pdf_url`,
`indexing[]`, `collaboration_type`, `external_institution`, `sub_type`,
`verification_status`, `points_awarded`, `academic_year_id`, timestamps.
Indexes: `doi_unique` (partial), `faculty_id_idx`, `academic_year_id_idx`,
`publication_year_idx`, `source_idx`, `source_record_id_idx`,
`verification_status_idx`, `source_source_record_id_unique` (partial unique).

> `verification_status`, `points_awarded`, `academic_year_id` and `source` are
> backend-owned; the client cannot set them (enforced by request schemas).

### publication_rules
`rule_id`, `rule_code`, `name`, `publication_type`, `indexing[]`,
`author_positions[]`, `corresponding_author_required`, `collaboration_type`,
`sub_type`, `points`, `max_claims_per_year`, `eligibility_designation`,
`description`, `is_active`, `effective_from`, `effective_to`, timestamps.
Indexes: `rule_code_unique`, `publication_type_idx`, `indexing_idx`,
`is_active_idx`.

Seeded catalogue (18 rules): `RULE-001`…`RULE-018` covering research and
collaborative publications, books, conference proceedings, patents, copyrights,
start-ups and projects, with points defined in data only.

### eligibility_rules
`eligibility_rule_id`, `code`, `designation`, `minimum_points`, `is_active`,
`effective_from`, `effective_to`, timestamps. Index: `designation_unique`.

Seeded thresholds: `assistant professor` = **100**, `associate professor` =
**200**, `professor` = **200**.

### faculty_points
`faculty_points_id`, `faculty_id`, `academic_year_id`, `total_points`,
`research_publication_points`, `book_points`, `conference_points`,
`patent_points`, `copyright_points`, `project_points`, `other_points`,
`last_calculated_at`. Index: `faculty_academic_year_unique`.

### verification_records
`verification_id`, `publication_id`, `faculty_id`, `verified_by_user_id`,
`previous_status`, `new_status`, `action` (`verify` | `reject`), `reason`,
`notes`, `created_at`. Indexes: `publication_id_idx`, `faculty_id_idx`,
`created_at_idx`.

### documents
`document_id`, `publication_id`, `faculty_id`, `document_type`,
`original_filename`, `stored_filename`, `storage_path`, `mime_type`,
`file_size`, `checksum` (SHA-256), `uploaded_by_user_id`, `status`
(`active` | `deleted`), `processing_status`, `processing_error`, `page_count`,
`extracted_text_length`, `extracted_at`, `metadata{}`, RAG fields
(`rag_status`, `rag_error`, `rag_processed_at`, `rag_chunk_count`,
`rag_embedding_count`, `rag_processing_version`, `rag_embedding_model`),
timestamps. Indexes: `document_id_unique`, `publication_id_idx`,
`faculty_id_idx`. The PDF binary is **not** stored in MongoDB.

### document_contents
`document_id`, `publication_id`, `faculty_id`, `text`, `text_length`,
`page_count`, `pages[{page_number, text}]`, `extraction_method`,
`text_extraction_quality`, timestamps. Index: `document_id_unique`.

### document_chunks
`chunk_id`, `document_id`, `publication_id`, `faculty_id`, `chunk_index`,
`text`, `page_start`, `page_end`, `character_count`, `word_count`,
`token_count`, `embedding[]`, `embedding_model`, `processing_version`,
timestamps. Indexes: `document_chunk_unique` (document_id + chunk_index),
`document_id_idx`, `publication_id_idx`, `faculty_id_idx`. Embeddings are never
returned by the API.

### audit_logs
`audit_id`, `user_id`, `action`, `entity_type`, `entity_id`, `old_value`,
`new_value`, `timestamp`, `ip_address`. (No secondary index configured.)

## Index Summary

All indexes are declared centrally in `app/models/collections.py` and created
idempotently on startup. Unique constraints use `partialFilterExpression` on
string fields so missing/null values do not collide. Verified live: every
configured index exists.

## Data Ownership invariants

- `publications.faculty_id`, `documents.faculty_id`, `document_chunks.faculty_id`
  and `faculty_points.faculty_id` are derived from the authenticated session,
  never from client input.
- Deleting a document soft-deletes it and removes its chunks; deleting a
  publication removes its chunks. Retrieval additionally excludes chunks whose
  document or publication no longer exists.

## Backup / reset

- The database is a standard MongoDB database; use `mongodump`/`mongorestore`.
- Tests use a separate database `research_faculty_db_test` (see `tests/conftest.py`)
  that is dropped after the suite, so production data is never touched.
