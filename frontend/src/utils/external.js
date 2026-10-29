import { getErrorMessage } from './errors'
import { formatDate } from './publication'

export const EXTERNAL_SOURCES = [
  { value: 'crossref', label: 'Crossref' },
  { value: 'pubmed', label: 'PubMed' },
  { value: 'orcid', label: 'ORCID' },
  { value: 'scopus', label: 'Scopus' },
  { value: 'web_of_science', label: 'Web of Science' },
]

export const SEARCH_PAGE_SIZE = 10

const MATCH_SOURCES = ['orcid', 'scopus', 'web_of_science']

export function sourceLabel(value) {
  const found = EXTERNAL_SOURCES.find((item) => item.value === value)
  return found ? found.label : value || '—'
}

export function requiresAuthorMatch(value) {
  return MATCH_SOURCES.includes(value)
}

export function validateSearch(source, query, advanced = {}) {
  if (!source) return 'Select a source to search.'
  const hasQuery = String(query || '').trim()
  const hasAdvanced = ['title', 'author', 'doi', 'author_id'].some((key) =>
    String(advanced?.[key] || '').trim(),
  )
  if (!hasQuery && !hasAdvanced) return 'Enter a search term.'
  return ''
}

export function buildSearchRequest({ source, query, title, author, doi, author_id, page }) {
  const current = Math.max(1, Number(page) || 1)
  const trimmed = {
    query: String(query || '').trim(),
    title: String(title || '').trim(),
    author: String(author || '').trim(),
    doi: String(doi || '').trim(),
    author_id: String(author_id || '').trim(),
  }

  if (source === 'orcid') {
    return { kind: 'orcid', params: { page: current, page_size: SEARCH_PAGE_SIZE } }
  }

  const params = {
    query: trimmed.query,
    page: current,
    page_size: SEARCH_PAGE_SIZE,
  }
  if (trimmed.title) params.title = trimmed.title
  if (trimmed.author) params.author = trimmed.author
  if (trimmed.doi) params.doi = trimmed.doi

  if (source === 'scopus') {
    if (trimmed.author_id) params.author_id = trimmed.author_id
    return { kind: 'scopus', params }
  }
  if (source === 'web_of_science') return { kind: 'web_of_science', params }
  return { kind: 'external', params: { source, ...params } }
}

export function formatAuthors(authors, limit = 3) {
  const names = (authors || [])
    .map((author) => {
      if (author?.name && String(author.name).trim()) return String(author.name).trim()
      const given = author?.given_name ? String(author.given_name).trim() : ''
      const family = author?.family_name ? String(author.family_name).trim() : ''
      return [given, family].filter(Boolean).join(' ')
    })
    .filter(Boolean)
  if (names.length === 0) return null
  if (names.length <= limit) return names.join(', ')
  return `${names.slice(0, limit).join(', ')}, et al.`
}

export function externalIdentifier(result) {
  if (result?.source_record_id && String(result.source_record_id).trim()) {
    return String(result.source_record_id).trim()
  }
  const identifiers = result?.external_identifiers
  if (identifiers && typeof identifiers === 'object') {
    const values = Object.values(identifiers).filter(Boolean)
    if (values.length > 0) return String(values[0])
  }
  return null
}

export function resultTitle(result) {
  const title = result?.title && String(result.title).trim()
  if (title) return String(title).trim()
  return externalIdentifier(result) || 'Untitled record'
}

export function hasImportableTitle(result) {
  return Boolean(result?.title && String(result.title).trim())
}

export function safeExternalUrl(url) {
  if (!url) return null
  const value = String(url).trim()
  return /^https?:\/\/\S+$/i.test(value) ? value : null
}

export function formatResultDate(result) {
  if (result?.publication_date) return formatDate(result.publication_date)
  if (result?.publication_year) return String(result.publication_year)
  return null
}

export function externalResultRows(result) {
  if (!result) return []
  const rows = []
  const push = (label, value, href) => {
    if (value === null || value === undefined) return
    const text = String(value).trim()
    if (!text) return
    rows.push(href ? { label, value: text, href } : { label, value: text })
  }
  push('Journal', result.journal)
  push('Conference', result.conference)
  push('Publisher', result.publisher)
  push('Publication date', formatResultDate(result))
  push('DOI', result.doi)
  push('Source', sourceLabel(result.source))
  push(
    'Indexing',
    Array.isArray(result.indexing) ? result.indexing.filter(Boolean).join(', ') : null,
  )
  push('External ID', externalIdentifier(result))
  const url = safeExternalUrl(result.url)
  push('URL', url, url)
  return rows
}

export function totalPages(total, pageSize = SEARCH_PAGE_SIZE) {
  const size = Number(pageSize) > 0 ? Number(pageSize) : SEARCH_PAGE_SIZE
  const count = Number(total) > 0 ? Math.ceil(Number(total) / size) : 1
  return Math.max(1, count)
}

export function buildImportPayload(result, options = {}) {
  return {
    source: options.source || result.source,
    source_record_id: result.source_record_id ?? null,
    title: String(result.title || '').trim(),
    abstract: result.abstract ?? null,
    authors: (result.authors || []).map((author) => ({
      name: author.name ?? null,
      given_name: author.given_name ?? null,
      family_name: author.family_name ?? null,
      email: author.email ?? null,
      affiliation: Array.isArray(author.affiliation) ? author.affiliation : null,
      author_position: author.author_position ?? null,
      orcid_id: author.orcid_id ?? null,
      scopus_author_id: author.scopus_author_id ?? null,
      web_of_science_researcher_id: author.web_of_science_researcher_id ?? null,
    })),
    journal: result.journal ?? null,
    conference: result.conference ?? null,
    publisher: result.publisher ?? null,
    doi: result.doi ?? null,
    publication_date: result.publication_date ?? null,
    publication_year: result.publication_year ?? null,
    url: safeExternalUrl(result.url),
    indexing: Array.isArray(result.indexing) ? result.indexing.filter(Boolean) : [],
    external_identifiers:
      result.external_identifiers && typeof result.external_identifiers === 'object'
        ? result.external_identifiers
        : {},
    academic_year_id: options.academicYearId ?? null,
    author_match_confirmed: Boolean(options.authorMatchConfirmed),
  }
}

function responseDetail(error) {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail.trim()
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') return item
        return typeof item?.msg === 'string' ? item.msg : ''
      })
      .filter(Boolean)
      .join(' ')
      .trim()
  }
  return ''
}

function safeDetail(error, fallback) {
  const detail = responseDetail(error)
  if (detail && detail.length <= 160 && !/Traceback|\/home\/|self\./i.test(detail)) {
    return detail
  }
  return fallback
}

export function isAuthorConfirmationError(error) {
  return (
    error?.response?.status === 400 &&
    /author_match_confirmed/i.test(responseDetail(error))
  )
}

export function getAuthorMatchFactors(error) {
  const detail = responseDetail(error)
  const match = detail.match(/factors:\s*([^)]*)\)?/i)
  return match ? match[1].trim().replace(/;.*$/, '') : ''
}

export function normalizeDoi(value) {
  if (!value) return ''
  let doi = String(value).trim().toLowerCase()
  doi = doi.replace(/^https?:\/\/(dx\.)?doi\.org\//, '')
  doi = doi.replace(/^doi:\s*/, '')
  return doi
}

export function sameDoi(a, b) {
  const left = normalizeDoi(a)
  const right = normalizeDoi(b)
  return Boolean(left) && left === right
}

export function isDuplicateImportError(error) {
  return error?.response?.status === 409
}

export function getExternalSearchError(error, source) {
  if (!error?.response) return 'Unable to connect to the server.'
  const status = error.response.status
  const label = sourceLabel(source)
  if (status === 401) return 'Your session has expired. Please sign in again.'
  if (status === 403) return "You don't have permission to search this source."
  if (status === 404) return 'No matching publication was found.'
  if (status === 429) return 'External source rate limit reached. Please try again later.'
  if (status === 502 || status === 504) return 'External source is temporarily unavailable.'
  if (status === 503) {
    if (/not configured/i.test(responseDetail(error))) {
      return `${label} search is currently unavailable because the external API is not configured.`
    }
    return 'External source is temporarily unavailable.'
  }
  if (status === 400) {
    return safeDetail(error, 'Please check your search and try again.')
  }
  if (status >= 500) return 'Something went wrong. Please try again.'
  return getErrorMessage(error)
}

export function getExternalImportError(error, source) {
  if (!error?.response) return 'Unable to connect to the server.'
  const status = error.response.status
  const label = sourceLabel(source)
  if (status === 401) return 'Your session has expired. Please sign in again.'
  if (status === 403) return "You don't have permission to import publications."
  if (status === 404) return 'No matching publication was found.'
  if (status === 409) return 'This publication is already in your publication list.'
  if (status === 429) return 'External source rate limit reached. Please try again later.'
  if (status === 502 || status === 504) return 'External source is temporarily unavailable.'
  if (status === 503) {
    if (/not configured/i.test(responseDetail(error))) {
      return `${label} is currently unavailable because the external API is not configured.`
    }
    return 'External source is temporarily unavailable.'
  }
  if (status === 400) {
    return safeDetail(error, 'Please review the publication details and try again.')
  }
  if (status >= 500) return 'Something went wrong. Please try again.'
  return getErrorMessage(error)
}
