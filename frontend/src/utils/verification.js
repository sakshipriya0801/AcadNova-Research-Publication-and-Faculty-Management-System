import { formatDate, statusMeta } from './publication'

// Verification statuses accepted by the admin review queue filter.
export const REVIEW_STATUS_FILTERS = [
  { value: 'pending', label: 'Pending (awaiting review)' },
  { value: 'verified', label: 'Verified' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'needs_review', label: 'Needs review' },
  { value: '', label: 'All statuses' },
]

export const REVIEW_SORT_FIELDS = [
  { value: 'created_at', label: 'Date added' },
  { value: 'publication_date', label: 'Publication date' },
  { value: 'title', label: 'Title' },
]

export const ACTION_META = {
  verify: {
    button: 'Verify publication',
    busy: 'Verifying…',
    confirm: 'Verify',
    notice: 'Publication verified.',
    history: 'Verified',
    symbol: '✓',
  },
  reject: {
    button: 'Reject publication',
    busy: 'Rejecting…',
    confirm: 'Reject publication',
    notice: 'Publication rejected.',
    history: 'Rejected',
    symbol: '✕',
  },
}

export const REASON_REQUIRED_MESSAGE =
  'Reason is required when rejecting a publication.'

// Mirrors the backend allowed transitions.
const ALLOWED_ACTIONS = {
  pending: ['verify', 'reject'],
  verified: ['reject'],
  rejected: ['verify'],
  needs_review: [],
}

export function availableActions(status) {
  return ALLOWED_ACTIONS[status] || []
}

export function validateReason(value) {
  const trimmed = (value || '').trim()
  return trimmed || null
}

export function latestRejection(records) {
  if (!Array.isArray(records)) return null
  return records.find((record) => record.action === 'reject') || null
}

export function recordActionLabel(record) {
  const meta = record && ACTION_META[record.action]
  if (meta) return meta.history
  return 'Status changed'
}

export function recordActionSymbol(record) {
  const meta = record && ACTION_META[record.action]
  return meta ? meta.symbol : '•'
}

export function recordTransition(record) {
  if (!record) return ''
  const from = record.previous_status
    ? statusMeta(record.previous_status).label
    : null
  const to = record.new_status ? statusMeta(record.new_status).label : null
  if (from && to) return `${from} → ${to}`
  return to || from || ''
}

export function formatRecordDate(value) {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return formatDate(value)
  const MONTHS = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
  ]
  const day = String(date.getDate()).padStart(2, '0')
  const month = MONTHS[date.getMonth()]
  const year = date.getFullYear()
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${day} ${month} ${year}, ${hours}:${minutes}`
}

const INTERNAL_ERROR_PATTERN =
  /traceback|\/home\/|\/self\/|storage_path|password_hash|stack trace/i

export function getVerificationError(
  error,
  fallback = 'Something went wrong while updating verification.',
) {
  if (!error || !error.response) {
    return 'Unable to connect to the server.'
  }
  const { status, data } = error.response
  if (status === 401) {
    return 'Your session has expired. Please sign in again.'
  }
  let detail = ''
  if (typeof data?.detail === 'string') {
    detail = data.detail
  } else if (Array.isArray(data?.detail)) {
    detail = data.detail
      .map((item) => (typeof item === 'string' ? item : item?.msg || ''))
      .filter(Boolean)
      .join(' ')
  }
  detail = detail.trim()
  if (!detail || detail.length > 160 || INTERNAL_ERROR_PATTERN.test(detail)) {
    if (status === 403) return 'You do not have permission to perform this action.'
    if (status === 404) return 'Publication not found.'
    return fallback
  }
  return detail
}

// Locate a publication by scanning the paginated admin review list
// (the admin API has no single-publication endpoint).
export async function findPublicationById(
  listFn,
  publicationId,
  pageSize = 100,
) {
  let page = 1
  let totalPages = 1
  do {
    const data = await listFn(page, pageSize)
    const items = (data && data.items) || []
    const found = items.find((item) => item.publication_id === publicationId)
    if (found) return found
    totalPages = (data && data.total_pages) || 1
    page += 1
  } while (page <= totalPages)
  return null
}
