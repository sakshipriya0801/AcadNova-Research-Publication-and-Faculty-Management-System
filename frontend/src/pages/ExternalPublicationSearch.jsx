import { useState } from 'react'
import { Link } from 'react-router-dom'
import ResearchSearchPanel from '../components/ResearchSearchPanel'

import ExternalPublicationDetails from '../components/ExternalPublicationDetails'
import ImportExternalConfirm from '../components/ImportExternalConfirm'
import LoadingScreen from '../components/LoadingScreen'
import {
  searchExternalPublications,
} from '../services/externalPublicationService'
import { getOrcidWorks } from '../services/orcidService'
import { searchScopus } from '../services/scopusService'
import { searchWebOfScience } from '../services/webOfScienceService'
import {
  EXTERNAL_SOURCES,
  buildSearchRequest,
  externalResultRows,
  formatAuthors,
  formatResultDate,
  getExternalSearchError,
  hasImportableTitle,
  requiresAuthorMatch,
  resultTitle,
  sourceLabel,
  totalPages,
  validateSearch,
} from '../utils/external'

const CARD_ROW_LABELS = ['DOI', 'Source', 'Publisher', 'External ID', 'Indexing']

export default function ExternalPublicationSearch() {
  const [source, setSource] = useState('crossref')
  const [query, setQuery] = useState('')
  const [advanced, setAdvanced] = useState({ title: '', author: '', doi: '', author_id: '' })
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [validationError, setValidationError] = useState('')
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [status, setStatus] = useState('idle')
  const [errorMessage, setErrorMessage] = useState('')
  const [selected, setSelected] = useState(null)
  const [importTarget, setImportTarget] = useState(null)
  const [notice, setNotice] = useState('')

  const sourceLabelText = sourceLabel(source)
  const pages = data ? totalPages(data.total, data.page_size) : 1

  function runSearch(nextPage) {
    const validation = validateSearch(source, query, advanced)
    setValidationError(validation)
    if (validation) return

    setStatus('loading')
    setErrorMessage('')
    const request = buildSearchRequest({
      source,
      query,
      title: advanced.title,
      author: advanced.author,
      doi: advanced.doi,
      author_id: advanced.author_id,
      page: nextPage,
    })

    let call
    if (request.kind === 'orcid') call = getOrcidWorks(request.params)
    else if (request.kind === 'scopus') call = searchScopus(request.params)
    else if (request.kind === 'web_of_science') call = searchWebOfScience(request.params)
    else call = searchExternalPublications(request.params)

    call
      .then((response) => {
        setData(response.data)
        setPage(nextPage)
        setStatus('ready')
      })
      .catch((error) => {
        setErrorMessage(getExternalSearchError(error, source))
        setStatus('error')
      })
  }

  function handleSubmit(event) {
    event.preventDefault()
    runSearch(1)
  }

  function handleSourceChange(event) {
    setSource(event.target.value)
    setData(null)
    setPage(1)
    setStatus('idle')
    setErrorMessage('')
    setValidationError('')
  }

  function goToPage(nextPage) {
    if (nextPage < 1 || nextPage > pages || nextPage === page) return
    runSearch(nextPage)
  }

  function closeImport(message) {
    setImportTarget(null)
    if (message) setNotice(message)
  }

  const showResults = Boolean(data && data.results.length > 0)
  const showEmpty = status === 'ready' && data && data.results.length === 0

  return (
    <div className="page ext-page">
      <div className="page__header">
        <div>
          <h1 className="page__title">Search Publications</h1>
          <p className="page__subtitle">
            Search scholarly databases and import records into your publication list.
            Imports are added as Pending until verified.
          </p>
        </div>
        <Link className="btn btn--ghost" to="/publications">
          My Publications
        </Link>
      </div>

      {notice ? (
        <div className="alert alert--success pub-alert" role="status">
          <span>{notice}</span>
          <button
            type="button"
            className="pub-alert__close"
            onClick={() => setNotice('')}
            aria-label="Dismiss message"
          >
            ✕
          </button>
        </div>
      ) : null}

      <ResearchSearchPanel />

      <section className="ext-search" aria-label="Search external publications">
        <form className="ext-search__bar" onSubmit={handleSubmit} noValidate>
          <div className="field ext-search__field">
            <label className="field__label" htmlFor="ext-source">
              Source
            </label>
            <select
              id="ext-source"
              className="field__input"
              value={source}
              onChange={handleSourceChange}
            >
              {EXTERNAL_SOURCES.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </div>

          <div className="field ext-search__field ext-search__field--grow">
            <label className="field__label" htmlFor="ext-query">
              Search
            </label>
            <input
              id="ext-query"
              className="field__input"
              type="search"
              placeholder="e.g. machine learning in education"
              value={query}
              onChange={(event) => {
                setQuery(event.target.value)
                if (validationError) setValidationError('')
              }}
              aria-invalid={Boolean(validationError)}
              aria-describedby={validationError ? 'ext-query-error' : undefined}
            />
          </div>

          <div className="ext-search__submit">
            <button type="submit" className="btn btn--primary" disabled={status === 'loading'}>
              {status === 'loading' ? 'Searching…' : 'Search'}
            </button>
          </div>
        </form>

        {validationError ? (
          <p className="field__error" id="ext-query-error" role="alert">
            {validationError}
          </p>
        ) : null}

        {source === 'orcid' ? (
          <p className="ext-search__hint">
            ORCID shows the works recorded on your connected ORCID profile; the search
            term is not sent to ORCID.
          </p>
        ) : (
          <button
            type="button"
            className="btn btn--ghost btn--small ext-search__advanced-toggle"
            onClick={() => setShowAdvanced((open) => !open)}
            aria-expanded={showAdvanced}
            aria-controls="ext-advanced"
          >
            {showAdvanced ? 'Hide advanced search' : 'Advanced search'}
          </button>
        )}

        {showAdvanced && source !== 'orcid' ? (
          <div className="ext-search__advanced" id="ext-advanced">
            <div className="field">
              <label className="field__label" htmlFor="ext-title">
                Title
              </label>
              <input
                id="ext-title"
                className="field__input"
                type="text"
                value={advanced.title}
                onChange={(event) =>
                  setAdvanced((current) => ({ ...current, title: event.target.value }))
                }
              />
            </div>
            <div className="field">
              <label className="field__label" htmlFor="ext-author">
                Author
              </label>
              <input
                id="ext-author"
                className="field__input"
                type="text"
                value={advanced.author}
                onChange={(event) =>
                  setAdvanced((current) => ({ ...current, author: event.target.value }))
                }
              />
            </div>
            <div className="field">
              <label className="field__label" htmlFor="ext-doi">
                DOI
              </label>
              <input
                id="ext-doi"
                className="field__input"
                type="text"
                placeholder="10.1000/xyz123"
                value={advanced.doi}
                onChange={(event) =>
                  setAdvanced((current) => ({ ...current, doi: event.target.value }))
                }
              />
            </div>
            {source === 'scopus' ? (
              <div className="field">
                <label className="field__label" htmlFor="ext-author-id">
                  Scopus Author ID
                </label>
                <input
                  id="ext-author-id"
                  className="field__input"
                  type="text"
                  placeholder="e.g. 58644291200"
                  value={advanced.author_id}
                  onChange={(event) =>
                    setAdvanced((current) => ({ ...current, author_id: event.target.value }))
                  }
                />
              </div>
            ) : null}
          </div>
        ) : null}
      </section>

      <section className="ext-results" aria-label="Search results" aria-busy={status === 'loading'}>
        <div className="ext-results__header">
          <h2 className="ext-results__title">Results</h2>
          {status === 'loading' ? (
            <p className="ext-results__status" role="status">
              Searching {sourceLabelText}…
            </p>
          ) : status === 'ready' && data ? (
            <p className="ext-results__status" role="status">
              Found {data.total} result{data.total === 1 ? '' : 's'}
            </p>
          ) : null}
        </div>

        {status === 'error' ? (
          <div className="alert alert--danger" role="alert">
            {errorMessage}{' '}
            <button
              type="button"
              className="btn btn--ghost btn--inline"
              onClick={() => runSearch(page)}
            >
              Retry
            </button>
          </div>
        ) : null}

        {status === 'idle' && !data ? (
          <div className="empty-state">
            <p className="empty-state__title">Search scholarly databases to find publications.</p>
            <p className="empty-state__text">
              Choose a source, enter a search term, then select Import to add a record.
            </p>
          </div>
        ) : null}

        {status === 'loading' && !data ? (
          <LoadingScreen message={`Searching ${sourceLabelText}…`} />
        ) : null}

        {showEmpty ? (
          <div className="empty-state">
            <p className="empty-state__title">No publications found for this search.</p>
            <p className="empty-state__text">Try a different term or source.</p>
          </div>
        ) : null}

        {showResults ? (
          <ul className="ext-cards">
            {(data.results || []).map((item, index) => {
              const authors = formatAuthors(item.authors, 4)
              const date = formatResultDate(item)
              const venue = item.journal || item.conference
              const rows = externalResultRows(item).filter((row) =>
                CARD_ROW_LABELS.includes(row.label),
              )
              const importable = hasImportableTitle(item)
              return (
                <li className="ext-card" key={item.source_record_id || index}>
                  <div className="ext-card__body">
                    <h3 className="ext-card__title">{resultTitle(item)}</h3>
                    {authors ? <p className="ext-card__authors">{authors}</p> : null}
                    {venue || date ? (
                      <p className="ext-card__meta">
                        {venue}
                        {venue && date ? ' • ' : ''}
                        {date || ''}
                      </p>
                    ) : null}
                    <dl className="ext-card__rows">
                      {rows.map((row) => (
                        <div className="ext-card__row" key={row.label}>
                          <dt>{row.label}</dt>
                          <dd>
                            {row.href ? (
                              <a href={row.href} target="_blank" rel="noopener noreferrer">
                                {row.value}
                              </a>
                            ) : (
                              row.value
                            )}
                          </dd>
                        </div>
                      ))}
                    </dl>
                  </div>
                  <div className="ext-card__actions">
                    <button
                      type="button"
                      className="btn btn--ghost btn--small"
                      onClick={() => setSelected(item)}
                    >
                      View
                    </button>
                    <button
                      type="button"
                      className="btn btn--primary btn--small"
                      onClick={() => {
                        setSelected(null)
                        setImportTarget(item)
                      }}
                      disabled={!importable}
                      title={importable ? undefined : 'This record has no title to import'}
                    >
                      Import
                    </button>
                  </div>
                </li>
              )
            })}
          </ul>
        ) : null}

        {showResults && pages >= 1 ? (
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
              Page {page} of {pages}
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
      </section>

      <ExternalPublicationDetails
        result={selected}
        source={selected?.source || source}
        onClose={() => setSelected(null)}
        onImport={(item) => {
          setSelected(null)
          setImportTarget(item)
        }}
      />

      {importTarget ? (
        <ImportExternalConfirm
          result={importTarget}
          source={importTarget.source || source}
          onCancel={() => closeImport('')}
          onFinished={closeImport}
        />
      ) : null}
    </div>
  )
}
