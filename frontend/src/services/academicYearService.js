import api from './api'

// Faculty-facing read-only list (management stays under /api/admin).
export function listAcademicYears() {
  return api.get('/api/academic-years')
}
