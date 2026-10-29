import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import {
  getExternalPublication,
  searchResearch,
} from '../services/researchSearchService'
import ImportExternalConfirm from './ImportExternalConfirm'
import { getErrorMessage } from '../utils/errors'
import { sourceLabel } from '../utils/external'
import {
  RESEARCH_SEARCH_TYPES,
  RESEARCH_SOURCES,
  researchSearchType,
  researchStatusClass,
  researchStatusLabel,
  validateResearchSearch,
} from '../utils/researchSearch'

function authorsText(result) {
  const authors = Array.isArray(result.authors) ? result.authors : []
  if (authors.length === 0) return null
  return authors.map((a) => (typeof a === 'string' ? a : a.name)).join(', ')
}

function metaLine(result) {
  const parts = []
  if (result.journal) parts.push(result.journal)
  if (result.publication_date) parts.push(String(result.publication_date).slice(0, 10))
  if (result.publication_year) parts.push(String(result.publication_year))
  return parts.filter(Boolean).join(' • ')
}

export default function ResearchSearchPanel() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'

  const [type, setType] = useState('author_name')
  const [q, setQ] = useState('')
  const [source, setSource] = useState('crossref')
  const [validationError, setValidationError] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [status, setStatus] = useState('idle')
  const [results, setResults] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(0)
  const [importTarget, setImportTarget] = useState(null)
  const [importingId, setImportingId] = useState('')

  const currentType = researchSearchType(type)

  function reset() {
    setValidationError('')
    setErrorMessage('')
    setResults([])
    setTotal(0)
    setPage(1)
    setPages(0)
  }

  async function runSearch(nextPage = 1) {
    const validation = validateResearchSearch(type, q)
    if (validation) {
      setValidationError(validation)
      return
    }
    reset()
    setStatus('loading')
    try {
      const params = { type, page: nextPage, page_size: 10 }
      if (q.trim()) params.q = q.trim()
      if (currentType.needsSource && source) params.source = source
      const { data } = await searchResearch(params)
      setResults(data.results || [])
      setTotal(data.total || 0)
      setPage(data.page || nextPage)
      setPages(Math.ceil((data.total || 0) / (data.page_size || 10)))
      setStatus('ready')
    } catch (error) {
      setStatus('error')
      setErrorMessage(getErrorMessage(error))
    }
  }

  function handleSubmit(event) {
    event.preventDefault()
    runSearch(1)
  }

  function goToPage(nextPage) {
    if (nextPage < 1 || nextPage > pages || nextPage === page) return
    runSearch(nextPage)
  }

  function closeImport(message) {
    setImportTarget(null)
    if (message) setErrorMessage(message)
  }

  async function handleImport(result) {
    setImportingId(`${result.source}-${result.source_record_id}`)
    try {
      const { data } = await getExternalPublication(result.source, result.source_record_id)
      setImportTarget(data)
    } catch (error) {
      setErrorMessage(getErrorMessage(error))
    } finally {
      setImportingId('')
    }
  }

  function internalLink(result) {
    if (!result.publication_id) return '#'
    return isAdmin
      ? `/admin/review/${result.publication_id}`
      : `/publications/${result.publication_id}`
  }

  const showResults = results.length > 0
  const showEmpty = status === 'ready' && results.length === 0

  return (
    <section className="ext-search ext-search--panel" aria-label="Research search">
      <form className="ext-search__bar" onSubmit={handleSubmit} noValidate>
        <div className="field ext-search__field">
          <label className="field__label" htmlFor="rs-type">
            Search type
          </label>
          <select
            id="rs-type"
            className="field__input"
            value={type}
            onChange={(event) => {
              setType(event.target.value)
              setValidationError('')
              setErrorMessage('')
            }}
          >
            {RESEARCH_SEARCH_TYPES.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </div>

        <div className="field ext-search__field ext-search__field--grow">
          <label className="field__label" htmlFor="rs-query">
            {currentType.value === 'faculty' ? 'Faculty / Employee ID' : 'Search'}
          </label>
          <input
            id="rs-query"
            className="field__input"
            type="search"
            placeholder={currentType.placeholder}
            value={q}
            onChange={(event) => {
              setQ(event.target.value)
              if (validationError) setValidationError('')
            }}
            aria-invalid={Boolean(validationError)}
            aria-describedby={validationError ? 'rs-query-error' : undefined}
          />
        </div>

        {currentType.needsSource ? (
          <div className="field ext-search__field">
            <label className="field__label" htmlFor="rs-source">
              Source
            </label>
            <select
              id="rs-source"
              className="field__input"
              value={source}
              onChange={(event) => setSource(event.target.value)}
            >
              {RESEARCH_SOURCES.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </div>
        ) : null}

        <div className="ext-search__submit">
          <button type="submit" className="btn btn--primary" disabled={status === 'loading'}>
            {status === 'loading' ? 'Searching…' : 'Search'}
          </button>
        </div>
      </form>

      {validationError ? (
        <p className="field__error" id="rs-query-error" role="alert">
          {validationError}
        </p>
      ) : null}

      {currentType.hint ? <p className="ext-search__hint">{currentType.hint}</p> : null}

      {errorMessage ? (
        <div className="alert alert--danger pub-alert" role="alert">
          <span>{errorMessage}</span>
          <button
            type="button"
            className="pub-alert__close"
            onClick={() => setErrorMessage('')}
            aria-label="Dismiss error"
          >
            ✕
          </button>
        </div>
      ) : null}

      {showEmpty ? (
        <p className="ext-search__empty" role="status">
          No results found.
        </p>
      ) : null}

      {showResults ? (
        <ul className="ext-search__results">
          {results.map((item, index) => {
            const key = item.publication_id || item.source_record_id || index
            const isInternal = item.kind === 'internal'
            return (
              <li className="ext-card" key={key}>
                <div className="ext-card__body">
                  <h3 className="ext-card__title">{item.title || 'Untitled'}</h3>
                  {authorsText(item) ? (
                    <p className="ext-card__authors">{authorsText(item)}</p>
                  ) : null}
                  {metaLine(item) ? <p className="ext-card__meta">{metaLine(item)}</p> : null}
                  <dl className="ext-card__rows">
                    <div className="ext-card__row">
                      <dt>Source</dt>
                      <dd>{sourceLabel(item.source)}</dd>
                    </div>
                    {item.doi ? (
                      <div className="ext-card__row">
                        <dt>DOI</dt>
                        <dd>{item.doi}</dd>
                      </div>
                    ) : null}
                    {isInternal && item.verification_status ? (
                      <div className="ext-card__row">
                        <dt>Status</dt>
                        <dd>
                          <span className={researchStatusClass(item.verification_status)}>
                            {researchStatusLabel(item.verification_status)}
                          </span>
                        </dd>
                      </div>
                    ) : null}
                  </dl>
                </div>
                <div className="ext-card__actions">
                  {isInternal ? (
                    <Link className="btn btn--ghost btn--small" to={internalLink(item)}>
                      View Details
                    </Link>
                  ) : (
                    <button
                      type="button"
                      className="btn btn--primary btn--small"
                      onClick={() => handleImport(item)}
                      disabled={importingId === `${item.source}-${item.source_record_id}`}
                    >
                      {importingId === `${item.source}-${item.source_record_id}`
                        ? 'Loading…'
                        : 'Import'}
                    </button>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      ) : null}

      {showResults && pages > 1 ? (
        <nav className="ext-pagination" aria-label="Search results pages">
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => goToPage(page - 1)}
            disabled={page <= 1 || status === 'loading'}
          >
            Previous
          </button>
          <p className="ext-pagination__info">
            Page {page} of {pages} ({total} results)
          </p>
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => goToPage(page + 1)}
            disabled={page >= pages || status === 'loading'}
          >
            Next
          </button>
        </nav>
      ) : null}

      {importTarget ? (
        <ImportExternalConfirm
          result={importTarget}
          source={importTarget.source || source}
          onCancel={() => closeImport('')}
          onFinished={closeImport}
        />
      ) : null}
    </section>
  )
}
