# User Workflows

## Faculty

### Getting started
1. **Register** at `/register` (email, password, name, employee id, designation)
   or **Log in** at `/login`.
2. Land on the **Dashboard**.

### Manage profile
- `/profile` → view/edit name, designation, department, ORCID, Scopus ID, Web of
  Science Researcher ID, PubMed ID, research interests, photo URL. Changes are
  saved via `PUT /api/faculty/profile` and persisted in MongoDB.

### Manage publications
- `/publications` — list own publications with search, filters, sorting and
  pagination.
- `/publications/new` — create a publication manually (backend assigns academic
  year, `pending` verification status and 0 points).
- `/publications/search` — search Crossref, PubMed, ORCID (and Scopus/WoS when
  configured) and **import** a result (stored as `pending`).
- `/publications/:id` — details; `/publications/:id/edit` — edit; delete is
  available for owned publications.

### Evidence documents
- `/documents` (or from a publication) — select a publication, then upload PDF
  evidence, download, view extracted content/metadata, and delete (soft).
- PDF text extraction: use **Process** on a document to extract page text.

### Points & eligibility
- `/points` — summary, category totals, per-publication breakdown and the
  **Recalculate** action. Eligibility is shown against the institutional
  threshold for the faculty member's designation.

### Reports
- `/reports` — publication, annual points, verification and faculty-summary
  reports; print and CSV export (built from backend data).

### AI Research Assistant
- `/research-assistant` — choose a scope (**All my documents**, a **publication**,
  or a specific **processed document**), optionally use a suggested question,
  and ask.
- The answer is generated only from retrieved content; **Sources** list the real
  publication/document and page numbers (or "Page information unavailable") and
  link to the publication.
- Only documents with `rag_status = completed` are selectable; unprocessed ones
  link to Documents. If the server has no AI provider configured, the assistant
  shows *"AI analysis is not configured on this server."* — never a fake answer.
- The conversation is session-only and clears on refresh.

## Admin

Admin accounts (no faculty profile) see an **Admin Console** group in the
sidebar:

- `/admin` — summary statistics and shortcuts.
- `/admin/review` and `/admin/review/:id` — review pending publications, then
  **verify** or **reject** (a rejection reason is required). History is recorded.
- `/admin/academic-years` — create/edit/set-current/delete (1 Jul → 30 Jun).
- `/admin/departments` — create/edit/deactivate/delete.
- `/admin/faculty` — search/filter, edit profiles, activate/deactivate.
- `/admin/rules` — manage publication rules (points, indexing, positions,
  status). Changing points on an active rule requires explicit confirmation.
- `/admin/eligibility` — manage designation thresholds.
- `/reports` — institutional reports.

All admin forms call real backend APIs; no statistics are hardcoded.

## Worked Example — Publication to Points

1. Faculty creates a research publication indexed in Scopus as 1st author.
2. Admin opens the review queue and **verifies** it.
3. The rule engine matches the most specific rule (`RULE-001`,
   1st/corresponding author, Scopus/WoS/PubMed = 100 points); ambiguity would
   produce `needs_review`.
4. Faculty recalculates points → 100 for the academic year; eligibility against
   the 100-point Assistant Professor threshold is shown.
5. Faculty uploads the PDF evidence and (optionally) processes it for AI.
6. Faculty asks the AI assistant a question; the answer cites the PDF's page.
