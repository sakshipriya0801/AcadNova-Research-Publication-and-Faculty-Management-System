import api from './api'

// Admin: verify or reject a publication
export function verifyPublication(publicationId, action, reason, notes) {
  return api.post(`/api/admin/publications/${publicationId}/verification`, {
    action,
    reason,
    notes,
  })
}

// Faculty: view own publication verification history
export function getVerificationHistory(publicationId) {
  return api.get(`/api/publications/${publicationId}/verification-history`)
}

// Admin: view any publication verification history
export function getAdminVerificationHistory(publicationId) {
  return api.get(`/api/admin/publications/${publicationId}/verification-history`)
}

// Admin: publication review list
export function listPublicationsAdmin(params) {
  return api.get('/api/admin/publications', { params })
}
