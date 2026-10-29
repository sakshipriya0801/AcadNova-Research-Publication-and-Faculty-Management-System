import api from './api'

export function getPointsSummary(academicYearId) {
  return api.get('/api/points/summary', { params: { academic_year_id: academicYearId } })
}

export function recalculatePoints(academicYearId) {
  return api.post('/api/points/recalculate', { academic_year_id: academicYearId })
}

export function getPointsBreakdown(academicYearId) {
  return api.get('/api/points/breakdown', { params: { academic_year_id: academicYearId } })
}
