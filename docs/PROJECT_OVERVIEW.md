# Project Overview

## Project Title

**AcadNova** — *A New Era of Research.*

AcadNova is an academic research and faculty performance platform with
publication verification, performance analytics, and an AI Research Assistant.

A full-stack web application for managing research publications,
verifying them against institutional policy, computing performance points and
increment eligibility, storing publication evidence, and answering grounded
questions about uploaded research using a retrieval-augmented generation (RAG)
pipeline.

## Overview

The system gives faculty a single place to record and manage their scholarly
output (manual entry or import from external scholarly APIs), upload supporting
PDF evidence, and track their annual performance points and eligibility for
increment. Administrators review and verify submissions, manage academic years,
departments, faculty, publication rules and eligibility thresholds, and
generate reports. An AI Research Assistant answers questions strictly from the
faculty member's own processed documents and returns the real sources used.

The application is deliberately layered so that each concern is testable in
isolation:

```
React (Vite) → FastAPI → MongoDB → External scholarly APIs → Rule engine
             → Verification → Points/Eligibility → Documents/PDF
             → RAG (extract → clean → chunk → embed → retrieve) → LLM
```

## Problem Statement

Universities must assess faculty research performance annually against a
complex, configurable points policy. Manual tracking is error-prone, evidence
is scattered, verification is ad-hoc, and results are hard to audit. There is no
consistent, transparent, rule-driven way to compute points, determine increment
eligibility, or let faculty ask questions about their own documents.

## Objectives

1. Centralise faculty publications with external API import and duplicate
   protection.
2. Encode the institutional points policy as a configurable, auditable rule
   engine (no hardcoded points in application logic).
3. Provide a secure verification workflow with an immutable history and audit
   trail.
4. Compute points and increment eligibility from backend-owned data only.
5. Manage publication evidence PDFs securely (filesystem storage + metadata).
6. Provide a grounded AI assistant that answers only from retrieved documents
   and cites real sources.
7. Enforce strict ownership/authorization with the backend as the authority.
8. Deliver professional documentation and a fully tested system.

## Main Features

- Authentication and role-based access (faculty / admin) using JWT.
- Faculty profiles (department, designation, ORCID, Scopus, WoS, PubMed,
  research interests).
- Publication CRUD with DOI normalisation, duplicate protection, academic-year
  derivation, filtering, sorting and pagination.
- External scholarly search/import: Crossref, PubMed, ORCID (live); Scopus and
  Web of Science (implemented, require provider credentials).
- Admin verification/rejection with required reasons and history.
- Configurable publication rule engine (most-specific-rule selection,
  ambiguity → needs review, max claims per year).
- Points calculation and increment eligibility per academic year (1 July →
  30 June).
- Reports: publications, annual points, verification history, faculty summary,
  with print and CSV export.
- Document/PDF management: magic-byte validation, SHA-256 checksums, size
  limits, soft delete, download, path-traversal/IDOR protection.
- PDF text extraction and processing states.
- RAG foundation: cleaning, deterministic chunking, embeddings, MongoDB vector
  storage with honest brute-force cosine fallback.
- Grounded AI question answering with authoritative backend citations,
  relevance cutoff, prompt-injection defense and safe failure handling.
- AI Research Assistant UI with scope selection, session-only conversation and
  safe configuration/error states.

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, React Router 6, Axios, Vite |
| Backend | Python 3.12, FastAPI, Uvicorn, Pydantic v2 |
| Database | MongoDB (PyMongo) |
| Auth | JWT (PyJWT), bcrypt/pwdlib password hashing |
| PDF | PyMuPDF |
| External APIs | Crossref, PubMed, ORCID, Scopus, Web of Science |
| AI/RAG | Provider-independent embedding + LLM adapters (OpenAI-compatible), MongoDB chunk store |
| Testing | pytest (backend), Node `.mjs` unit harnesses + Python contract flows (frontend/integration) |

## Documentation Index

- [Architecture](ARCHITECTURE.md)
- [Database Design](DATABASE_DESIGN.md)
- [API Documentation](API_DOCUMENTATION.md)
- [AI/RAG Architecture](AI_RAG_ARCHITECTURE.md)
- [Security](SECURITY.md)
- [Testing](TESTING.md)
- [Setup & Deployment](SETUP_AND_DEPLOYMENT.md)
- [User Workflows](USER_WORKFLOWS.md)
- [Final Project Report](FINAL_PROJECT_REPORT.md)

## Configuration Status (summary)

| Capability | Status |
|---|---|
| MongoDB, auth, publications, verification, points, documents, RAG retrieval | **IMPLEMENTED** and verified end-to-end |
| Crossref, PubMed, ORCID | **CONFIGURED** (public APIs, no credentials required) and verified live |
| Scopus, Web of Science | **IMPLEMENTED**, **NOT CONFIGURED** — require provider API keys |
| RAG embeddings (semantic) | **IMPLEMENTED**; live semantic embeddings require `RAG_EMBEDDING_PROVIDER=openai` + key (**NOT CONFIGURED** here) |
| RAG LLM answer generation | **IMPLEMENTED**; live generation requires `RAG_LLM_PROVIDER=openai` + key (**NOT CONFIGURED** here) |
