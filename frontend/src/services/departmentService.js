import api from './api'

// Faculty-facing read-only lookup (management stays under /api/admin).
export function listDepartments() {
  return api.get('/api/departments')
}
