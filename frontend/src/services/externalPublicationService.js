import api from './api'

export function searchExternalPublications(params) {
  return api.get('/api/publications/search-external', { params })
}

export function getExternalPublication(source, recordId) {
  return api.get(`/api/publications/external/${source}/${recordId}`)
}

export function importExternalPublication(data) {
  return api.post('/api/publications/import-external', data)
}
