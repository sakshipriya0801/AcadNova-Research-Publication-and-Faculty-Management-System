export const PUBLICATION_TYPES = [
  { value: 'research_publication', label: 'Research Publication' },
  { value: 'collaborative_publication', label: 'Collaborative Publication' },
  { value: 'book_editor', label: 'Book Editor' },
  { value: 'book_chapter', label: 'Book Chapter' },
  { value: 'conference_proceeding', label: 'Conference Proceeding' },
  { value: 'patent', label: 'Patent' },
  { value: 'copyright', label: 'Copyright' },
  { value: 'startup', label: 'Startup' },
  { value: 'project', label: 'Project' },
  { value: 'consultancy', label: 'Consultancy' },
  { value: 'other', label: 'Other' },
]

export const PUBLICATION_SOURCES = [
  { value: 'manual', label: 'Manual' },
  { value: 'crossref', label: 'Crossref' },
  { value: 'pubmed', label: 'PubMed' },
  { value: 'orcid', label: 'ORCID' },
  { value: 'scopus', label: 'Scopus' },
  { value: 'web_of_science', label: 'Web of Science' },
]

export const STATUS_META = {
  pending: { label: 'Pending', symbol: '⏳' },
  verified: { label: 'Verified', symbol: '✓' },
  rejected: { label: 'Rejected', symbol: '✕' },
  needs_review: { label: 'Needs Review', symbol: '!' },
}

export const SORT_FIELDS = [
  { value: 'publication_date', label: 'Publication date' },
  { value: 'created_at', label: 'Date added' },
  { value: 'title', label: 'Title' },
]

export function typeLabel(value) {
  if (!value) return '—'
  return PUBLICATION_TYPES.find((item) => item.value === value)?.label || value
}

export function sourceLabel(value) {
  if (!value) return '—'
  return PUBLICATION_SOURCES.find((item) => item.value === value)?.label || value
}

export function statusMeta(value) {
  return STATUS_META[value] || { label: value || 'Unknown', symbol: '•' }
}

const MONTHS = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
]

export function formatDate(value) {
  if (!value) return null
  const [year, month, day] = String(value).slice(0, 10).split('-').map(Number)
  if (!year || !month || !day) return String(value)
  return `${String(day).padStart(2, '0')} ${MONTHS[month - 1]} ${year}`
}

export function yearFromDate(value) {
  if (!value) return null
  const year = Number(String(value).slice(0, 4))
  return Number.isFinite(year) && year > 1000 ? year : null
}

export function academicYearFromDate(value) {
  if (!value) return null
  const [year, month] = String(value).slice(0, 10).split('-').map(Number)
  if (!year || !month) return null
  const startYear = month >= 7 ? year : year - 1
  return `${startYear}-${startYear + 1}`
}
