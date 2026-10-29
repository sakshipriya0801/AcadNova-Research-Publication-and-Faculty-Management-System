import api from './api'

export function processDocument(publicationId, documentId) {
  return api.post(`/api/publications/${publicationId}/documents/${documentId}/process`)
}

export function getProcessingStatus(publicationId, documentId) {
  return api.get(`/api/publications/${publicationId}/documents/${documentId}/processing-status`)
}

export function getExtractedContent(publicationId, documentId) {
  return api.get(`/api/publications/${publicationId}/documents/${documentId}/content`)
}

export function getDocumentMetadata(publicationId, documentId) {
  return api.get(`/api/publications/${publicationId}/documents/${documentId}/metadata`)
}
