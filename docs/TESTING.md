# Testing

The project uses three complementary test layers. No test requires paid
external AI or scholarly credentials.

## 1. Backend unit/integration tests (pytest)

Location: `backend/tests/`. Run:

```bash
cd backend
.venv/bin/python -m pytest -q
```

- Uses an isolated database (`research_faculty_db_test`) created and dropped by
  `tests/conftest.py`; production data is never touched.
- `TestClient` exercises the real FastAPI app and MongoDB.
- External scholarly APIs are mocked where needed; the mapping tests hit no
  network.

Coverage highlights: auth, faculty, publications, documents, PDF processing,
verification, points, rules, admin, external integrations, database/health,
integration persistence, RAG foundation and RAG quality/security.

## 2. Frontend / utility harnesses (Node)

Location: `/home/sakshi/.opencode-state/scripts/*.mjs` (verification tooling).
Run:

```bash
node <harness>.mjs
```

They copy the pure utility modules into a temp dir and unit-test formatting,
error mapping, request building and source/citation rendering logic:

| Harness | Focus |
|---|---|
| `external_utils_test.mjs` | external search/import helpers |
| `document_utils_test.mjs` | document helpers |
| `verification_utils_test.mjs` | verification helpers |
| `points_utils_test.mjs` | points helpers |
| `reports_utils_test.mjs` | reports helpers |
| `admin_utils_test.mjs` | admin helpers |
| `research_assistant_utils_test.mjs` | AI assistant request/source/answer helpers |

## 3. End-to-end contract flows (Python)

Location: `/home/sakshi/.opencode-state/scripts/*.py`. They drive the running
stack through the Vite proxy (`http://localhost:5173`) and assert API contracts
and real persistence, cleaning up after themselves:

| Flow | Area |
|---|---|
| `pub_ui_flow.py` | publications |
| `external_contract_flow.py` | Crossref/PubMed/ORCID search & import |
| `document_ui_flow.py` | documents/PDF (uses backend venv python) |
| `verification_ui_flow.py` | verification |
| `points_ui_flow.py` | points & eligibility |
| `reports_ui_flow.py` | reports |
| `admin_ui_flow.py` | admin management |
| `lifecycle_ui_flow.py` | create→upload→verify→points→reports |
| `integration_db_verify.py` | real CRUD persistence + security |
| `rag_security_verify.py` | RAG persistence, retrieval, isolation |

## 4. Frontend build

```bash
cd frontend
npm run build
```

## RAG-specific suites

- `tests/test_rag_foundation.py` — extraction reuse, cleaning, deterministic
  chunking, page metadata, empty/scanned PDFs, deterministic embeddings, chunk
  storage, idempotent reprocessing, retrieval ranking, ownership, deleted-doc
  exclusion.
- `tests/test_rag_qa.py` — grounded answers with sources, no-answer behaviour,
  provider-not-configured/unavailable/failure, prompt injection as data, no
  embeddings/paths exposed, context limits, auth.
- `tests/test_rag_quality.py` (Step 15E) — grounding, multi-source retrieval,
  citation integrity, relevance threshold (incl. client cannot lower it), prompt
  injection, cross-faculty isolation, document lifecycle, LLM/embedding failure
  handling, input validation and resource bounds.

## Latest Results (Step 16 final run)

| Suite | Result |
|---|---|
| Backend pytest | **408 passed** |
| Frontend harnesses (7) | **461 passed** |
| Contract flows (8) | **399 passed** |
| Live DB integration verifier | **44/44** |
| Live RAG/security verifier | **21/21** |
| Production build | success (0 warnings) |

Warnings: 1 pre-existing `StarletteDeprecationWarning` (httpx vs. httpx2) —
unrelated to application behaviour.

## Test Data Hygiene

All temporary users, faculty, publications, documents, contents and chunks are
removed after each flow. The final database contains no test/demo records and no
`document_chunks` rows.
