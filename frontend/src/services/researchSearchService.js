import api from './api'

export function searchResearch(params) {
  return api.get('/api/search/research', { params })
}

export function getExternalPublication(source, recordId) {
  return api.get(`/api/publications/external/${source}/${recordId}`)
}
