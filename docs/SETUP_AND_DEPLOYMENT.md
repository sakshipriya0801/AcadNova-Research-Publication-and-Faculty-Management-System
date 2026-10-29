# Setup & Deployment

## Prerequisites

- Python 3.12+
- Node.js 18+ and npm
- MongoDB 6.0+ (local `mongod` or a connection string)

## 1. MongoDB

Start a local MongoDB (adjust data path as needed):

```bash
mongod --dbpath /path/to/data --bind_ip 127.0.0.1 --port 27017
```

Database name: `research_faculty_db` (configurable). The application creates
collections and indexes automatically on first write/startup.

## 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # then edit values (never commit .env)
# Required: JWT_SECRET_KEY (no default)
export JWT_SECRET_KEY="a-long-random-secret"   # or set it in .env

uvicorn app.main:app --reload
```

Health check:

```bash
curl http://localhost:8000/api/health
# {"status":"ok","database":"connected"}
```

Swagger UI: `http://localhost:8000/docs` · OpenAPI: `http://localhost:8000/openapi.json`.

## 3. Frontend

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173
```

The frontend calls the API at `VITE_API_BASE_URL` (default
`http://localhost:8000`) through the central `src/services/api.js` client. The
backend allows the dev origin via `CORS_ORIGINS`. Vite also proxies `/api` to
`http://localhost:8000` for convenience.

## 4. Environment Variables (`backend/.env.example`)

| Variable | Required | Purpose |
|---|---|---|
| `MONGODB_URI` | yes (default provided) | MongoDB connection string (no credentials by default) |
| `MONGODB_DATABASE` | yes (default provided) | Database name |
| `JWT_SECRET_KEY` | **yes** | JWT signing secret (no default) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | optional | Token lifetime |
| `CORS_ORIGINS` | optional | Comma-separated browser origins |
| `DOCUMENT_STORAGE_DIR` | optional | Filesystem directory for PDFs |
| `MAX_DOCUMENT_SIZE_MB` | optional | Upload size limit |
| `CROSSREF_API_URL` / `CROSSREF_TIMEOUT_SECONDS` | optional | Crossref |
| `PUBMED_API_URL` / `PUBMED_API_KEY` / `PUBMED_EMAIL` | optional | PubMed |
| `ORCID_API_URL` / `ORCID_CLIENT_ID` / `ORCID_CLIENT_SECRET` | optional | ORCID |
| `SCOPUS_API_URL` / `SCOPUS_API_KEY` | for Scopus | Scopus (key required) |
| `WEB_OF_SCIENCE_API_URL` / `WEB_OF_SCIENCE_API_KEY` | for WoS | Web of Science (key required) |
| `RAG_ENABLED`, `RAG_EMBEDDING_PROVIDER`, `RAG_EMBEDDING_MODEL`, `RAG_CHUNK_SIZE`, `RAG_CHUNK_OVERLAP`, `RAG_TOP_K`, `RAG_MAX_TOP_K`, `RAG_MAX_QUERY_LENGTH`, `RAG_MIN_RELEVANCE_SCORE`, `RAG_MAX_CONTEXT_WORDS` | optional | RAG retrieval |
| `RAG_LLM_PROVIDER`, `RAG_LLM_MODEL`, `RAG_LLM_TEMPERATURE`, `RAG_OPENAI_API_URL`, `RAG_OPENAI_API_KEY`, `RAG_OPENAI_TIMEOUT_SECONDS` | for live AI | LLM/embedding provider |

Frontend `.env.example`: `VITE_API_BASE_URL`.

**Never put real credentials in `.env.example`.** The `.env` files are
git-ignored.

## 5. Seeding & Reset

The repository ships configuration seeds only:

- `backend/scripts/seed_rules.py` — publication rules + eligibility thresholds.
- `backend/scripts/create_admin.py` — creates the first admin account
  (`ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD=...`).

```bash
cd backend
JWT_SECRET_KEY=... .venv/bin/python -c "from app.database import mongodb; from scripts.seed_rules import seed_publication_rules, seed_eligibility_rules; mongodb.init_mongodb(); seed_publication_rules(); seed_eligibility_rules()"
ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD='change-me' .venv/bin/python scripts/create_admin.py
```

A fresh deployment starts with just the admin and the seeded rules; faculty
accounts are created through registration. There is no demo/faculty seed.

## 6. Running Tests

```bash
# Backend
cd backend && .venv/bin/python -m pytest -q

# Frontend build
cd frontend && npm run build
```

See `docs/TESTING.md` for the harness and contract-flow suites.

## 7. Production Notes

- Set `APP_DEBUG=false`, a strong `JWT_SECRET_KEY`, an authenticated
  `MONGODB_URI`, explicit `CORS_ORIGINS`, and serve the frontend behind TLS.
- Build the frontend (`npm run build` → `frontend/dist`) and serve the static
  assets; route API calls to the FastAPI service.
- Consider a MongoDB Atlas deployment if `$vectorSearch` (ANN vector index) is
  desired for RAG at scale; otherwise brute-force cosine is used.

## 8. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `/api/health` → `disconnected` | MongoDB not running or wrong `MONGODB_URI` |
| Validation error at startup: `jwt_secret_key` | `JWT_SECRET_KEY` not set |
| Browser API calls fail (CORS) | add the frontend origin to `CORS_ORIGINS` |
| `503 AI provider is not configured.` | set `RAG_EMBEDDING_PROVIDER` / `RAG_LLM_PROVIDER` + `RAG_OPENAI_API_KEY` |
| `503 … API key is not configured` (Scopus/WoS) | set the provider key, or ignore — those integrations are optional |
