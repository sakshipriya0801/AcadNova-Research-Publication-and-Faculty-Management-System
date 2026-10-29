import api from './api'
import { clearToken } from '../utils/auth'

export function login(email, password) {
  return api.post('/api/auth/login', { email, password })
}

export function register(data) {
  return api.post('/api/auth/register', data)
}

// Administrator registration using a valid invitation token.
export function registerAdmin(data) {
  return api.post('/api/auth/admin-register', data)
}

export function getCurrentUser() {
  return api.get('/api/auth/me')
}

export function changePassword(newPassword, confirmPassword) {
  return api.post('/api/auth/change-password', {
    new_password: newPassword,
    confirm_password: confirmPassword,
  })
}

export function logout() {
  clearToken()
}
