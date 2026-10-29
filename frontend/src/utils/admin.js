import { getErrorMessage } from './errors'
import { formatDate, typeLabel } from './publication'

export { DEPARTMENT_PROGRAMS, DESIGNATION_OPTIONS } from './facultyOptions'

export function departmentProgramLabel(departmentId) {
  return departmentId || '—'
}

export function getAdminError(
  error,
  fallback = 'Something went wrong. Please try again.',
) {
  if (!error || !error.response) {
    return 'Unable to connect to the server.'
  }
  const status = error.response.status
  if (status === 401) {
    return 'Your session has expired. Please sign in again.'
  }
  if (status === 403) {
    return 'Admin role required.'
  }
  if (status === 404) {
    return 'Requested resource was not found.'
  }
  return getErrorMessage(error, fallback)
}

export const ADMIN_EMPTY = {
  academicYears: 'No academic years found.',
  departments: 'No departments found.',
  faculty: 'No faculty members found.',
  rules: 'No publication rules found.',
  eligibility: 'No eligibility configurations found.',
}

export const ADMIN_PERMISSION_TITLE = "You don't have permission"
export const ADMIN_PERMISSION_TEXT =
  'The administration console is available to administrators only.'

export function splitList(text) {
  return String(text || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

export function joinList(list) {
  return Array.isArray(list) ? list.join(', ') : ''
}

export function splitPositions(text) {
  return String(text || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item) => Number(item))
    .filter((item) => Number.isInteger(item) && item > 0)
}

export function joinPositions(list) {
  return Array.isArray(list) ? list.join(', ') : ''
}

export function departmentName(departments, departmentId) {
  if (!departmentId) return '—'
  const found = departments.find(
    (item) => item.department_id === departmentId,
  )
  return found ? found.name : '—'
}

export function isActiveLabel(isActive) {
  return isActive ? 'Active' : 'Inactive'
}

export function typeOrAny(value) {
  return value ? typeLabel(value) : 'Any type'
}

export function formatDateValue(value) {
  return formatDate(value) || '—'
}

export function rangeLabel(from, to) {
  if (!from && !to) return '—'
  return `${from ? formatDateValue(from) : '…'} – ${to ? formatDateValue(to) : '…'}`
}

export function validateDates(fromValue, toValue, message) {
  if (fromValue && toValue && fromValue >= toValue) {
    return message
  }
  return ''
}

export function nonNegativeInteger(value) {
  const text = String(value).trim()
  if (!/^\d+$/.test(text)) return false
  return true
}
