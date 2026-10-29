import api from './api'

export function createPublication(data) {
  return api.post('/api/publications', data)
}

export function listPublications(params) {
  return api.get('/api/publications', { params })
}

export function getPublication(publicationId) {
  return api.get(`/api/publications/${publicationId}`)
}

export function updatePublication(publicationId, data) {
  return api.put(`/api/publications/${publicationId}`, data)
}

export function deletePublication(publicationId) {
  return api.delete(`/api/publications/${publicationId}`)
}
