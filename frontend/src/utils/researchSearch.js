// Metadata + validation for the unified research-publication search.

export const RESEARCH_SEARCH_TYPES = [
  { value: 'faculty', label: 'Faculty ID / Employee ID', placeholder: 'e.g. FAC-123 or EMP-456', needsSource: false, hint: 'Find publications for a faculty account (admin only).' },
  { value: 'scopus_author', label: 'Scopus Author ID', placeholder: 'e.g. 58644291200', needsSource: false, hint: 'Search Scopus by author ID.' },
  { value: 'orcid', label: 'ORCID iD', placeholder: 'e.g. 0000-0002-1825-0097', needsSource: false, hint: 'Search public works by ORCID.' },
  { value: 'author_name', label: 'Author Name', placeholder: 'e.g. Sakshi Priya', needsSource: true, hint: 'Search by the name under which you publish.' },
  { value: 'doi', label: 'DOI', placeholder: 'e.g. 10.1000/xyz123', needsSource: true, hint: 'Search by DOI.' },
  { value: 'title', label: 'Publication Title', placeholder: 'e.g. machine learning in education', needsSource: true, hint: 'Search by publication title.' },
]

export const RESEARCH_SOURCES = [
  { value: 'crossref', label: 'Crossref' },
  { value: 'pubmed', label: 'PubMed' },
  { value: 'scopus', label: 'Scopus' },
  { value: 'web_of_science', label: 'Web of Science' },
  { value: 'orcid', label: 'ORCID' },
]

export function researchSearchType(value) {
  return RESEARCH_SEARCH_TYPES.find((type) => type.value === value) || RESEARCH_SEARCH_TYPES[0]
}

export function validateResearchSearch(type, q) {
  if (!type) return 'Select a search type.'
  if (type === 'faculty') return '' // faculty users default to their own profile
  if (!String(q || '').trim()) return 'Enter a search term.'
  return ''
}

export function researchStatusLabel(status) {
  if (!status) return ''
  return status.replace(/_/g, ' ')
}

export function researchStatusClass(status) {
  if (!status) return 'admin-status admin-status--pending'
  return `admin-status admin-status--${status === 'verified' ? 'verified' : status === 'rejected' ? 'rejected' : 'pending'}`
}
