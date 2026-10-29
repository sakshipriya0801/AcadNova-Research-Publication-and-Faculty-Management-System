import api from './api'

export function uploadPublicationDocument(publicationId, file, documentType) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('document_type', documentType)
  return api.post(`/api/publications/${publicationId}/documents`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function listPublicationDocuments(publicationId) {
  return api.get(`/api/publications/${publicationId}/documents`)
}

export function downloadPublicationDocument(publicationId, documentId) {
  return api.get(`/api/publications/${publicationId}/documents/${documentId}/download`, {
    responseType: 'blob',
  })
}

export function deletePublicationDocument(publicationId, documentId) {
  return api.delete(`/api/publications/${publicationId}/documents/${documentId}`)
}
