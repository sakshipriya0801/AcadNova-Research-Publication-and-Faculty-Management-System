import api from './api'

export function searchScopus(params) {
  return api.get('/api/scopus/search', { params })
}

export function getScopusPublication(recordId) {
  return api.get(`/api/scopus/publication/${recordId}`)
}

export function getScopusAuthor(authorId) {
  return api.get(`/api/scopus/author/${authorId}`)
}

export function importScopusPublication(data) {
  return api.post('/api/publications/import-external', data)
}
