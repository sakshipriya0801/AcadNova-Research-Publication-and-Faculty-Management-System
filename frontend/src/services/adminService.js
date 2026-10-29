import api from './api'

// Academic years
export function createAcademicYear(data) {
  return api.post('/api/admin/academic-years', data)
}
export function listAcademicYears() {
  return api.get('/api/admin/academic-years')
}
export function updateAcademicYear(id, data) {
  return api.put(`/api/admin/academic-years/${id}`, data)
}
export function setCurrentAcademicYear(id) {
  return api.patch(`/api/admin/academic-years/${id}/current`)
}
export function deleteAcademicYear(id) {
  return api.delete(`/api/admin/academic-years/${id}`)
}

// Departments
export function createDepartment(data) {
  return api.post('/api/admin/departments', data)
}
export function listDepartments() {
  return api.get('/api/admin/departments')
}
export function updateDepartment(id, data) {
  return api.put(`/api/admin/departments/${id}`, data)
}
export function deactivateDepartment(id) {
  return api.patch(`/api/admin/departments/${id}/deactivate`)
}
export function deleteDepartment(id) {
  return api.delete(`/api/admin/departments/${id}`)
}

// Faculty
export function listFaculty(params) {
  return api.get('/api/admin/faculty', { params })
}
export function createFaculty(data) {
  return api.post('/api/admin/faculty', data)
}
export function listFacultyApplications(params) {
  return api.get('/api/admin/faculty/approvals', { params })
}
export function approveFaculty(facultyId) {
  return api.post(`/api/admin/faculty/${facultyId}/approve`)
}
export function rejectFaculty(facultyId, reason) {
  return api.post(`/api/admin/faculty/${facultyId}/reject`, { reason })
}
export function getFaculty(id) {
  return api.get(`/api/admin/faculty/${id}`)
}
export function updateFaculty(id, data) {
  return api.put(`/api/admin/faculty/${id}`, data)
}
export function setFacultyStatus(id, isActive) {
  return api.patch(`/api/admin/faculty/${id}/status`, { is_active: isActive })
}

// Rules
export function listRules() {
  return api.get('/api/admin/rules')
}
export function createRule(data) {
  return api.post('/api/admin/rules', data)
}
export function updateRule(id, data) {
  return api.put(`/api/admin/rules/${id}`, data)
}
export function setRuleStatus(id, isActive) {
  return api.patch(`/api/admin/rules/${id}/status`, { is_active: isActive })
}

// Eligibility rules
export function listEligibilityRules() {
  return api.get('/api/admin/eligibility-rules')
}
export function createEligibilityRule(data) {
  return api.post('/api/admin/eligibility-rules', data)
}
export function updateEligibilityRule(id, data) {
  return api.put(`/api/admin/eligibility-rules/${id}`, data)
}
export function setEligibilityRuleStatus(id, isActive) {
  return api.patch(`/api/admin/eligibility-rules/${id}/status`, { is_active: isActive })
}

// Summary
export function getAdminSummary() {
  return api.get('/api/admin/summary')
}

// Publications (admin browse / review)
export function listPublicationsAdmin(params) {
  return api.get('/api/admin/publications', { params })
}

// Audit logs (verification history / admin actions)
export function getAuditLogs(params) {
  return api.get('/api/admin/audit-logs', { params })
}

// Administrator accounts
export function listAdminAccounts() {
  return api.get('/api/admin/accounts')
}
export function createAdminAccount(data) {
  return api.post('/api/admin/accounts', data)
}

// Administrator invitations
export function listInvitations() {
  return api.get('/api/admin/invitations')
}
export function createInvitation(data) {
  return api.post('/api/admin/invitations', data)
}
export function revokeInvitation(invitationId) {
  return api.post(`/api/admin/invitations/${invitationId}/revoke`)
}
