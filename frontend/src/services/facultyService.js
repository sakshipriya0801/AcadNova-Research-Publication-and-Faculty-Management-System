import api from './api'

export function getMyProfile() {
  return api.get('/api/faculty/profile')
}

export function updateMyProfile(data) {
  return api.put('/api/faculty/profile', data)
}
