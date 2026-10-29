import { getErrorMessage } from './errors'

export const REPORT_TYPES = [
  { id: 'publications', label: 'Publication Report' },
  { id: 'points', label: 'Annual Points Report' },
  { id: 'verification', label: 'Verification Report' },
  { id: 'summary', label: 'Faculty Research Summary' },
]

export const EMPTY_REPORT_MESSAGE =
  'No report data is available for this academic year.'

export function reportTypeLabel(reportType) {
  const match = REPORT_TYPES.find((item) => item.id === reportType)
  return match ? match.label : 'Report'
}

export function getReportError(error, fallback = 'Unable to load report data.') {
  if (!error?.response) return 'Unable to connect to the server.'
  const status = error.response.status
  if (status === 401) return 'Your session has expired. Please sign in again.'
  if (status === 403) return 'You do not have permission to view this report.'
  if (status === 404) return 'Report data was not found.'
  return getErrorMessage(error, fallback)
}

export function venueLabel(publication) {
  if (!publication) return ''
  return (
    publication.journal_name ||
    publication.conference_name ||
    publication.publisher ||
    ''
  )
}

export function authorsLabel(publication) {
  const authors = publication?.authors
  if (!Array.isArray(authors) || authors.length === 0) return ''
  return authors.join(', ')
}

export function publicationYearLabel(publication) {
  if (!publication) return '—'
  if (publication.publication_year) return String(publication.publication_year)
  const date = publication.publication_date
  if (typeof date === 'string' && date.length >= 4) return date.slice(0, 4)
  return '—'
}

export function indexingLabel(publication) {
  const indexing = publication?.indexing
  if (!Array.isArray(indexing) || indexing.length === 0) return ''
  return indexing.join(', ')
}

export function formatDepartment(departments, departmentId) {
  if (!departmentId) return 'Not set'
  const list = Array.isArray(departments) ? departments : []
  const match = list.find((item) => item.department_id === departmentId)
  return match && match.name ? match.name : 'Not set'
}

const FORMULA_PREFIX = /^[=+\-@]/
const PLAIN_NUMBER = /^-?\d+(\.\d+)?$/

export function csvCell(value) {
  if (value === null || value === undefined) return ''
  if (typeof value === 'number') return String(value)
  let text = String(value)
  if (FORMULA_PREFIX.test(text) && !PLAIN_NUMBER.test(text)) {
    text = `'${text}`
  }
  if (/[",\n\r]/.test(text)) {
    text = `"${text.replace(/"/g, '""')}"`
  }
  return text
}

export function toCsv(headers, rows) {
  const lines = [headers.map(csvCell).join(',')]
  for (const row of rows) {
    lines.push(row.map(csvCell).join(','))
  }
  return lines.join('\r\n')
}

export function csvFilename(reportLabel, yearName) {
  const slug = `${reportLabel} ${yearName || ''}`
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
  return `${slug || 'report'}.csv`
}

export function downloadCsv(filename, headers, rows) {
  const csv = toCsv(headers, rows)
  const blob = new Blob([`\ufeff${csv}`], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

export async function mapWithConcurrency(items, limit, mapper) {
  const source = Array.isArray(items) ? items : []
  const results = new Array(source.length)
  let next = 0
  async function worker() {
    while (next < source.length) {
      const index = next
      next += 1
      results[index] = await mapper(source[index], index)
    }
  }
  const workers = []
  const count = Math.max(1, Math.min(limit, source.length || 1))
  for (let i = 0; i < count; i += 1) workers.push(worker())
  await Promise.all(workers)
  return results
}
