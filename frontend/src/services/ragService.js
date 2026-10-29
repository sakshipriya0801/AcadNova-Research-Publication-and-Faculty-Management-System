import api from './api'

export function processDocumentKnowledge(publicationId, documentId) {
  return api.post(
    `/api/publications/${publicationId}/documents/${documentId}/knowledge/process`,
  )
}

export function getKnowledgeStatus(publicationId, documentId) {
  return api.get(
    `/api/publications/${publicationId}/documents/${documentId}/knowledge/status`,
  )
}

// Ask a grounded question about the caller's documents. Identity is taken from
// the session by the api.js interceptor; no faculty_id or auth fields are sent.
export function queryResearch({ query, publication_id, document_id, top_k } = {}) {
  const body = { query }
  if (publication_id) body.publication_id = publication_id
  if (document_id) body.document_id = document_id
  if (top_k) body.top_k = top_k
  return api.post('/api/rag/query', body)
}
