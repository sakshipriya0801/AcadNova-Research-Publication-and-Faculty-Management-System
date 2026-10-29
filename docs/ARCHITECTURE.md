# Architecture

## Overview

The system is a three-tier application — a React single-page app, a FastAPI
backend, and MongoDB — augmented by external scholarly APIs and an
AI/RAG pipeline. The backend is the single source of truth: all authorization,
points, verification state and citations are computed server-side.

## A. System Architecture

```mermaid
flowchart TB
    subgraph Client["React Frontend (Vite, port 5173)"]
        UI[Pages & Components]
        SVC[Service layer - central api.js]
        UI --> SVC
    end

    subgraph Server["FastAPI Backend (Uvicorn, port 8000)"]
        ROUTES[Routers: auth, faculty, publications, documents, points, admin, orcid, scopus, wos, rag]
        DEPS[Auth dependencies - JWT, role checks]
        SERVICES[Services: publication, verification, points, document, pdf_processing, external, rag]
        RULES[Rule engine]
        ROUTES --> DEPS
        ROUTES --> SERVICES
        SERVICES --> RULES
    end

    subgraph DB["MongoDB (research_faculty_db)"]
        COLS[(13 collections)]
    end

    subgraph Ext["External Scholarly APIs"]
        CROSSREF[Crossref]
        PUBMED[PubMed]
        ORCID[ORCID]
        SCOPUS[Scopus - needs key]
        WOS[Web of Science - needs key]
    end

    subgraph AI["AI / RAG Providers"]
        EMB[Embedding provider]
        LLM[LLM provider]
    end

    SVC -->|HTTP JSON + Bearer JWT / Vite proxy| ROUTES
    SERVICES --> COLS
    SERVICES --> CROSSREF
    SERVICES --> PUBMED
    SERVICES --> ORCID
    SERVICES --> SCOPUS
    SERVICES --> WOS
    SERVICES --> EMB
    SERVICES --> LLM
```

## B. Authentication Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as React
    participant A as FastAPI
    participant DB as MongoDB

    U->>F: Register / Login
    F->>A: POST /api/auth/register | /api/auth/login
    A->>DB: lookup / create user (bcrypt hash)
    A-->>F: access_token (JWT) + user
    F->>F: store token (localStorage) via api.js
    F->>A: GET /api/auth/me (Bearer token)
    A->>A: decode JWT, load active user
    A-->>F: current user (role, faculty_id)
    Note over F,A: 401 → interceptor clears token, redirects to /login
```

## C. Publication Workflow

```mermaid
flowchart LR
    A[Create / Import] --> B[Normalise DOI]
    B --> C{Duplicate DOI?}
    C -->|yes| D[409 Conflict]
    C -->|no| E[Derive academic year]
    E --> F[Store publication - pending]
    F --> G[List / Search / Filter / Sort]
    G --> H[View details]
    H --> I[Edit owned publication]
    H --> J[Delete owned publication]
```

## D. Verification Workflow

```mermaid
stateDiagram-v2
    [*] --> pending: publication created
    pending --> verified: admin verify
    pending --> rejected: admin reject (reason required)
    pending --> needs_review: rule ambiguity
    verified --> [*]
    rejected --> [*]
    note right of verified
      verification_records entry
      points recalculated
    end note
```

## E. Points Calculation Workflow

```mermaid
flowchart TD
    A[Verified publications for faculty + academic year] --> B[Rule engine: match by type, indexing, author position]
    B --> C{Multiple matches?}
    C -->|equal specificity| R[needs_review]
    C -->|single best| D[Most specific rule wins]
    D --> E{max_claims_per_year exceeded?}
    E -->|yes| Z[0 points - yearly cap reached]
    E -->|no| F[Rule points]
    F --> G[Sum accepted points]
    G --> H[Compare to eligibility threshold by designation]
    H --> I[Eligible / remaining points]
```

## F. PDF / RAG Pipeline

```mermaid
flowchart LR
    PDF[Uploaded PDF] --> EX[PyMuPDF extraction]
    EX --> DC[(document_contents - page text)]
    DC --> CL[Text cleaning]
    CL --> CH[Deterministic page-aware chunking]
    CH --> EM[Embeddings]
    EM --> DCH[(document_chunks - text + vector + metadata)]
    DCH --> VS[Vector similarity search]
    VS --> RT[Ranked chunks + sources]
```

## G. AI Question-Answer Flow

```mermaid
sequenceDiagram
    participant U as Faculty
    participant F as AI Research Assistant
    participant A as FastAPI /api/rag/query
    participant DB as MongoDB
    participant L as LLM provider

    U->>F: Question (+ optional scope)
    F->>A: POST /api/rag/query (Bearer JWT, no faculty_id)
    A->>A: authorise scope from session
    A->>DB: embed query + similarity search (scoped)
    DB-->>A: ranked chunks
    A->>A: relevance filter + context assembly
    alt no relevant chunks
        A-->>F: safe no-answer message, no LLM call
    else relevant context
        A->>L: grounded prompt (system + untrusted context + question)
        L-->>A: answer text
        A->>A: validate answer; attach authoritative sources
        A-->>F: answer + real sources + model + time
    end
```

## H. Database / Entity Relationship (logical)

```mermaid
erDiagram
    USERS ||--o| FACULTY : "1:1 optional profile"
    FACULTY ||--o{ PUBLICATIONS : owns
    FACULTY }o--|| DEPARTMENTS : "belongs to"
    ACADEMIC_YEARS ||--o{ PUBLICATIONS : classifies
    PUBLICATIONS ||--o{ DOCUMENTS : has evidence
    DOCUMENTS ||--o| DOCUMENT_CONTENTS : "extracted text"
    DOCUMENTS ||--o{ DOCUMENT_CHUNKS : "RAG chunks"
    PUBLICATIONS ||--o{ VERIFICATION_RECORDS : "verification history"
    FACULTY ||--o{ FACULTY_POINTS : "annual points"
    ACADEMIC_YEARS ||--o{ FACULTY_POINTS : "per year"
    PUBLICATION_RULES ||--o{ FACULTY_POINTS : "awarded by"
    ELIGIBILITY_RULES }o--|| DEPARTMENTS : "designation thresholds"
    USERS ||--o{ AUDIT_LOGS : "acts on"
```

## Layer Connectivity

| Layer | Connects to | Evidence |
|---|---|---|
| React | FastAPI via central `api.js` (Bearer JWT) | 23 routes, 16 services, all use one axios client |
| FastAPI | MongoDB | health `{status:ok, database:connected}`; CRUD verified in `document_chunks` etc. |
| FastAPI | External APIs | live Crossref/PubMed/ORCID; Scopus/WoS return safe 503 without keys |
| FastAPI | Rule engine | `app/rules/rule_engine.py`, used by `points_service` |
| Documents | PDF processing | `pdf_processing_service` → `document_contents` |
| RAG | Embeddings + vector store + LLM | `app/services/rag/*` → `document_chunks` |

## Key Directories

```
backend/app/
  config/       settings (env-driven)
  database/     MongoDB client + index creation
  models/       collection names, indexes, enums
  schemas/      Pydantic request/response models
  routes/       API routers (+ admin/)
  services/     business logic (+ services/rag/)
  rules/        publication rule engine
  integrations/ external API clients
  utils/        security, author matching
frontend/src/
  pages/        route screens (+ admin/)
  components/   reusable UI
  services/     axios API layer (central api.js)
  hooks/        useAuth
  layouts/      AppLayout, AuthLayout
  utils/        formatting, error mapping
docs/           this documentation
```
