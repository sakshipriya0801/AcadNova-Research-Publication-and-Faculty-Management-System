import api from './api'

export function searchWebOfScience(params) {
  return api.get('/api/web-of-science/search', { params })
}

export function getWebOfSciencePublication(recordId) {
  return api.get(`/api/web-of-science/publication/${recordId}`)
}

export function getWebOfScienceResearcher(researcherId) {
  return api.get(`/api/web-of-science/researcher/${researcherId}`)
}

export function importWebOfSciencePublication(data) {
  return api.post('/api/publications/import-external', data)
}
