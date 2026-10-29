# AI / RAG Architecture

The AI subsystem is a modular retrieval-augmented generation (RAG) pipeline.
It reuses the existing document extraction pipeline and **never** fabricates
answers, sources, page numbers or citations. All code lives under
`backend/app/services/rag/`.

## Pipeline

```mermaid
flowchart LR
    PDF[PDF] --> EX[Extraction - reused Step 13]
    EX --> CL[text_cleaner]
    CL --> CH[chunker - deterministic, page-aware]
    CH --> EM[embedding_service]
    EM --> VS[vector_store - MongoDB document_chunks]
    VS --> RT[retrieval_service]
    RT --> CB[context_builder]
    CB --> QA[qa_service]
    QA --> LLM[llm_service]
    LLM --> ANS[Answer + authoritative sources]
```

## Modules

| Module | Responsibility |
|---|---|
| `text_cleaner.py` | Non-destructive Unicode/whitespace normalisation; preserves headings, punctuation, math |
| `chunker.py` | Deterministic word-window chunking with page-aware metadata (`chunk_size`, `overlap`) |
| `embedding_service.py` | Provider-independent embeddings (`embed_text`, `embed_texts`); providers: `test` (deterministic, dev/tests) and `openai` |
| `vector_store.py` | MongoDB-backed chunk/vector storage; upsert, delete, count, similarity search |
| `retrieval_service.py` | Scoped semantic retrieval; excludes deleted/orphaned documents |
| `context_builder.py` | Orders by relevance, de-duplicates, enforces word budget, keeps safe metadata |
| `prompts.py` | Grounding system instructions + delimited context/question template |
| `llm_service.py` | Provider-independent answer generation; `openai` adapter; safe error mapping |
| `qa_service.py` | Orchestrates validate → retrieve → filter → context → LLM → validate → answer + sources |
| `document_processor.py` | Clean → chunk → embed → store; idempotent; safe failure states |

## Vector Storage

- Chunks (text + embedding + metadata) are stored in **MongoDB**
  (`document_chunks`).
- If an Atlas `$vectorSearch` index is available it is used; otherwise the store
  performs a real **brute-force cosine** scan over stored vectors, capped at a
  maximum candidate count. The active mode is reported honestly as
  `vector_index` vs `vector_brute_force`. Keyword/text search is never presented
  as semantic search.
- Embeddings are **never** returned by the API.

## Embedding & LLM Provider Abstraction

| Provider | Embeddings (`RAG_EMBEDDING_PROVIDER`) | LLM (`RAG_LLM_PROVIDER`) |
|---|---|---|
| *(blank, default)* | Not configured → safe error | Not configured → safe error |
| `test` | Deterministic lexical hashing (dev/tests only) | n/a (LLM is mocked in tests) |
| `openai` | OpenAI-compatible `/embeddings` | OpenAI-compatible `/chat/completions` |

The embedding model (`RAG_EMBEDDING_MODEL`) and LLM model (`RAG_LLM_MODEL`) are
configured independently. API keys are read from the environment
(`RAG_OPENAI_API_KEY`); no key is hardcoded.

## Grounding & Safety

- The system prompt instructs the model to answer **only** from the supplied
  context, never to use outside knowledge, and never to invent facts/citations/
  pages.
- Retrieved document text is wrapped as **untrusted data** between
  `<<<BEGIN DOCUMENT CONTEXT>>>` and `<<<END DOCUMENT CONTEXT>>>`, separate from
  the system instructions and the user question. The model is told never to
  follow instructions found in documents (prompt-injection defense).
- The **backend** attaches sources from retrieved chunks; the model cannot
  fabricate source IDs or page numbers.
- Relevance cutoff (`RAG_MIN_RELEVANCE_SCORE`) is server-side; if nothing passes,
  the LLM is not called and a safe no-answer message is returned.

## Processing States

| State | Meaning |
|---|---|
| `pending` | Uploaded, not yet indexed |
| `processing` | Indexing in progress |
| `completed` | Chunks + embeddings stored |
| `failed` | Error stored in `rag_error`; no chunks retained |

Failures delete any existing chunks so a failed reprocess never leaves stale
evidence, and reprocessing remains possible once the provider recovers.

## Database

`document_chunks` fields: `chunk_id`, `document_id`, `publication_id`,
`faculty_id`, `chunk_index`, `text`, `page_start`, `page_end`,
`character_count`, `word_count`, `token_count`, `embedding`, `embedding_model`,
`processing_version`, timestamps.

## Configuration

```
RAG_ENABLED=true
RAG_EMBEDDING_PROVIDER=      # "" | test | openai
RAG_EMBEDDING_MODEL=
RAG_CHUNK_SIZE=1000          # words
RAG_CHUNK_OVERLAP=150
RAG_TOP_K=5
RAG_MAX_TOP_K=20
RAG_MAX_QUERY_LENGTH=2000
RAG_MIN_RELEVANCE_SCORE=0.0
RAG_MAX_CONTEXT_WORDS=3000
RAG_LLM_PROVIDER=            # "" | openai
RAG_LLM_MODEL=
RAG_LLM_TEMPERATURE=0.0
RAG_OPENAI_API_URL=https://api.openai.com/v1
RAG_OPENAI_API_KEY=
RAG_OPENAI_TIMEOUT_SECONDS=30
```

## Limitations

- Live semantic embeddings and LLM answers require provider credentials which
  are **not configured** in this repository/environment. Without them the
  endpoints return safe configuration errors (verified); no fake answers are
  produced.
- Local MongoDB has no Atlas `$vectorSearch`, so retrieval uses brute-force
  cosine (correct, but not ANN-indexed at scale).
- No persistent chat history or multi-turn memory (each request is independent).
```
