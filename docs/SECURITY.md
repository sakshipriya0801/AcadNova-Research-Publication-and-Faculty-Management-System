# Security

The backend is the single authority for authentication, authorization and all
derived values (points, verification state, RAG citations). The frontend never
makes trust decisions.

## Authentication

- **JWT** bearer tokens (`PyJWT`, HS256). The signing secret is
  `JWT_SECRET_KEY`, required from the environment with **no hardcoded default**.
- Tokens expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (default 60).
- Passwords are hashed with bcrypt (via `pwdlib`); plaintext is never stored.
- The frontend stores only `access_token` (localStorage). A `401` response makes
  the axios interceptor clear the token and redirect to `/login`.
- Inactive users are rejected during token validation.

## Authorization Matrix

| Capability | Faculty | Admin |
|---|---|---|
| Own profile / points / publications / documents | ✅ | – (admin has no faculty profile) |
| Verify / reject publications | ❌ (403) | ✅ |
| Academic years, departments, faculty, rules, eligibility | ❌ (403) | ✅ |
| Review queue / admin summary | ❌ (403) | ✅ |
| RAG query/retrieve over own documents | ✅ | ✅ (cross-document scope) |

Enforced by `require_authenticated_user` / `require_faculty` / `require_admin`
and per-resource ownership checks.

## Ownership & IDOR Prevention

- `faculty_id` is always derived from the JWT session; request bodies never
  supply it (schemas omit it, and RAG request schemas ignore unknown fields).
- Publication/document/RAG operations verify the resource's `faculty_id`
  against the caller: cross-faculty access returns **403**, unknown resources
  **404**.
- Automated tests cover cross-faculty isolation for publications, documents,
  verification history, points and RAG retrieval/query.

## Document Security

- **Upload validation**: PDF extension, MIME type, and `%PDF-` magic bytes;
  configurable size limit (`MAX_DOCUMENT_SIZE_MB`).
- **Deduplication**: SHA-256 checksum; duplicate active upload → `409`.
- **Storage**: PDFs live on the filesystem under `DOCUMENT_STORAGE_DIR` with
  server-generated UUID filenames; the original name is metadata only. The
  binary is **never** stored in MongoDB.
- **Path traversal**: `resolve_document_path` rejects absolute paths and `..`
  segments and confirms the resolved path stays within the storage root.
- **Download**: authenticated + ownership-checked; filename is sanitised before
  `Content-Disposition`.
- **Soft deletion**: documents are soft-deleted; RAG chunks are removed and
  retrieval excludes deleted/orphaned documents.

## Client-Controlled Field Protection

The following are backend-owned and not accepted from clients on create/update:
`faculty_id`, `verification_status`, `points_awarded`, `academic_year_id`,
`source`, `source_record_id`. Points and verification state are computed
server-side only.

## Secret Management

- All secrets via environment variables; `backend/.env` is git-ignored
  (`.env`, `*.env`). `.env.example` contains only placeholder names.
- The repository was scanned for hardcoded API keys, JWT secrets, MongoDB
  credentials and private keys — **none found**. The MongoDB URI has no
  credentials.

## Error Handling & Information Disclosure

- Validation errors return clean `400` messages (no stack traces).
- RAG/LLM/embedding failures are mapped to safe messages; unexpected errors are
  logged server-side and returned as generic `503`s.
- No API keys, MongoDB URIs, filesystem paths, embeddings, password hashes, or
  provider payloads are included in responses.
- The chunks endpoint never returns embeddings; the query endpoint never returns
  paths or internals.

## Prompt-Injection Defense

Retrieved document text is treated strictly as untrusted data, delimited from
the system instructions and the user question. The model is instructed never to
follow instructions inside documents. Even if the model were manipulated, the
`sources` array is built by the backend from retrieved chunks, so fabricated
citations are impossible.

## Audit Logging

Significant actions (registration, publication/document changes, verification,
admin management) are written to `audit_logs` with actor, action, entity and old
/ new values.

## Known Considerations

- For production, set `APP_DEBUG=false` and use a strong `JWT_SECRET_KEY`, a
  credentialed MongoDB URI, explicit `CORS_ORIGINS`, and TLS at the edge.
- No application-level rate limiting is implemented; query size, `top_k`,
  context size and retrieval candidates are bounded instead.
- Admin diagnostic endpoints (`/api/auth/test`, `/api/auth/admin-test`) return
  static messages and still require authentication/admin.
