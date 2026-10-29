# API Documentation

Interactive documentation (FastAPI OpenAPI 3.1):
- Swagger UI: `GET /docs`
- Raw schema: `GET /openapi.json`

Base URL (development): `http://localhost:8000` (frontend also reachable via the
Vite proxy at `http://localhost:5173/api/...`).

## Conventions

- **Auth**: protected endpoints require `Authorization: Bearer <JWT>`.
- **Errors**: `{ "detail": <string | list> }`. Validation errors return `400`
  (the app maps `RequestValidationError` to a clean list of messages).
  Status codes used: `400` validation, `401` unauthenticated, `403` forbidden,
  `404` not found, `409` conflict, `413` too large, `503` service/provider
  unavailable.
- **Pagination**: list endpoints accept `page`, `page_size` and return
  `{ items, page, page_size, total, total_pages }`.
- **Ownership**: faculty routes are scoped by the JWT session; `faculty_id` is
  never accepted from the client.

## Health & Auth (`auth`)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/api/health` | – | API + MongoDB status |
| POST | `/api/auth/register` | – | Register faculty account |
| POST | `/api/auth/login` | – | Login (returns JWT) |
| GET | `/api/auth/me` | user | Current user |
| GET | `/api/auth/test` | user | Diagnostic: authenticated OK |
| GET | `/api/auth/admin-test` | admin | Diagnostic: admin OK |

## Faculty (`faculty`, `departments`, `academic-years`)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/api/faculty/profile` | user | Own profile |
| PUT | `/api/faculty/profile` | user | Update own profile |
| GET | `/api/departments` | user | Read-only department lookup |
| GET | `/api/academic-years` | user | Read-only academic-year lookup |

## Publications (`publications`)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/api/publications` | user | List own (search/filter/sort/paginate) |
| POST | `/api/publications` | user | Create (pending) |
| GET | `/api/publications/{id}` | user | Details (owner/admin) |
| PUT | `/api/publications/{id}` | user | Update own |
| DELETE | `/api/publications/{id}` | user | Delete own |
| GET | `/api/publications/{id}/verification-history` | user | Own history |
| GET | `/api/publications/search-external` | user | Search Crossref/PubMed/ORCID/Scopus/WoS |
| GET | `/api/publications/external/{source}/{record_id}` | user | Fetch one external record |
| POST | `/api/publications/import-external` | user | Import external record |

## Documents (`documents`)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/api/publications/{pid}/documents` | user | Upload PDF evidence |
| GET | `/api/publications/{pid}/documents` | user | List documents |
| GET | `/api/publications/{pid}/documents/{id}/download` | user | Download PDF |
| DELETE | `/api/publications/{pid}/documents/{id}` | user | Soft delete |
| POST | `/api/publications/{pid}/documents/{id}/process` | user | Extract text |
| GET | `/api/publications/{pid}/documents/{id}/processing-status` | user | Extraction status |
| GET | `/api/publications/{pid}/documents/{id}/content` | user | Extracted pages |
| GET | `/api/publications/{pid}/documents/{id}/metadata` | user | PDF metadata |
| POST | `/api/publications/{pid}/documents/{id}/knowledge/process` | user | Build RAG chunks |
| GET | `/api/publications/{pid}/documents/{id}/knowledge/status` | user | RAG status |
| GET | `/api/publications/{pid}/documents/{id}/knowledge/chunks` | user | Chunk metadata (debug) |

## Verification — Admin (`admin: publications`)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/api/admin/publications` | admin | Review queue |
| POST | `/api/admin/publications/{id}/verification` | admin | `verify` / `reject` (reason required to reject) |
| GET | `/api/admin/publications/{id}/verification-history` | admin | History |

## Points (`points`)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/api/points/summary` | user | Total, category totals, eligibility |
| GET | `/api/points/breakdown` | user | Per-publication award with rule |
| POST | `/api/points/recalculate` | user | Recompute for an academic year |

## Admin Management (`admin: ...`)

| Group | Methods | Paths |
|---|---|---|
| Academic years | GET/POST/PUT/DELETE/PATCH | `/api/admin/academic-years[/{id}[/current]]` |
| Departments | GET/POST/PUT/DELETE/PATCH | `/api/admin/departments[/{id}[/deactivate]]` |
| Faculty | GET/PUT/PATCH | `/api/admin/faculty[/{id}[/status]]` |
| Rules | GET/POST/PUT/PATCH | `/api/admin/rules[/{id}[/status]]` |
| Eligibility | GET/POST/PUT/PATCH | `/api/admin/eligibility-rules[/{id}[/status]]` |
| Summary | GET | `/api/admin/summary` |

## External Source Integrations

| Group | Paths |
|---|---|
| ORCID | `/api/orcid/profile`, `/api/orcid/works`, `/api/orcid/works/{id}`, `/api/orcid/search`, `/api/orcid/researcher/{orcid}` |
| Scopus | `/api/scopus/search`, `/api/scopus/publication/{id}`, `/api/scopus/author/{id}` |
| Web of Science | `/api/web-of-science/search`, `/api/web-of-science/publication/{id}`, `/api/web-of-science/researcher/{id}` |

Scopus and Web of Science require provider API keys; without them they return a
safe `503` ("… API key is not configured").

## AI / RAG (`rag`)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/api/rag/retrieve` | user | Semantic retrieval (ranked chunks, no answer) |
| POST | `/api/rag/query` | user | Grounded answer + authoritative sources |

### `POST /api/rag/query`

Request (only these fields are honoured):

```json
{ "query": "What methodology was used?", "publication_id": null, "document_id": null, "top_k": 5 }
```

Response:

```json
{
  "answer": "…",
  "sources": [
    { "document_id": "…", "publication_id": "…", "chunk_index": 3,
      "page_start": 4, "page_end": 5, "relevance_score": 0.87 }
  ],
  "retrieved_chunks": 3,
  "model": "gpt-4o-mini",
  "processing_time_ms": 1234
}
```

Behaviours:
- No relevant context → `answer` is the safe no-answer message, `sources: []`,
  and the LLM is not called.
- No LLM configured → `503 { "detail": "AI provider is not configured." }`.
- Provider failure → `503` with a safe message.
- Sources are attached by the backend from retrieved chunks (never from model
  text); embeddings, filesystem paths and internals are never returned.

## Request Validation Highlights

- `query`: 1–2000 characters, trimmed; whitespace-only rejected (`400`).
- `top_k`: `1`–`20` server-side.
- Retrieval context bounded by `RAG_MAX_CONTEXT_WORDS`.
- Unknown `document_id`/`publication_id` → `404`; cross-faculty → `403`.
