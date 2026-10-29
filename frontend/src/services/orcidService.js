import api from './api'

export function getOrcidProfile() {
  return api.get('/api/orcid/profile')
}

export function getOrcidWorks(params) {
  return api.get('/api/orcid/works', { params })
}

export function searchOrcidResearchers(params) {
  return api.get('/api/orcid/search', { params })
}

export function getOrcidResearcher(orcidId) {
  return api.get(`/api/orcid/researcher/${orcidId}`)
}

export function getOrcidWork(workId) {
  return api.get(`/api/orcid/works/${workId}`)
}

export function importOrcidWork(data) {
  return api.post('/api/publications/import-external', data)
}
