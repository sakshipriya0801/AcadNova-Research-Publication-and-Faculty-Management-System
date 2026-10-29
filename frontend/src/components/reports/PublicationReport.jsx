import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { listPublications } from '../../services/publicationService'
import { listPublicationDocuments } from '../../services/documentService'
import {
  EMPTY_REPORT_MESSAGE,
  authorsLabel,
  csvFilename,
  downloadCsv,
  getReportError,
  indexingLabel,
  mapWithConcurrency,
  publicationYearLabel,
  reportTypeLabel,
  venueLabel,
} from '../../utils/reports'
import {
  PUBLICATION_SOURCES,
  formatDate,
  sourceLabel,
  statusMeta,
  typeLabel,
} from '../../utils/publication'

const STATUS_FILTERS = [
  { value: '', label: 'All statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'verified', label: 'Verified' },
  { value: 'rejected', label: 'Rejected' },
]

const SOURCE_FILTERS = [
  { value: '', label: 'All sources' },
  ...PUBLICATION_SOURCES,
]

const PAGE_SIZE_OPTIONS = [10, 25, 50]

const CSV_HEADERS = [
  'Title',
  'Publication Type',
  'Authors',
  'Journal/Conference',
  'DOI',
  'Source',
  'Indexing',
  'Publication Year',
  'Verification Status',
  'Points',
  'Documents',
]

export default function PublicationReport({ yearId, yearName }) {
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [sourceFilter, setSourceFilter] = useState('')
  const [indexingFilter, setIndexingFilter] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [data, setData] = useState(null)
  const [status, setStatus] = useState('loading')
  const [errorMessage, setErrorMessage] = useState('')
  const [reloadKey, setReloadKey] = useState(0)
  const [indexingOptions, setIndexingOptions] = useState([])
  const [docCounts, setDocCounts] = useState({})

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim())
      setPage(1)
    }, 400)
    return () => clearTimeout(timer)
  }, [searchInput])

  const hasActiveQuery =
    Boolean(search) || Boolean(statusFilter) || Boolean(sourceFilter) || Boolean(indexingFilter)

  const clearFilters = useCallback(() => {
    setSearchInput('')
    setSearch('')
    setStatusFilter('')
    setSourceFilter('')
    setIndexingFilter('')
    setPage(1)
  }, [])

  useEffect(() => {
    if (!yearId) return undefined
    let cancelled = false
    setStatus('loading')

    const params = {
      page,
      page_size: pageSize,
      academic_year_id: yearId,
      sort_by: 'publication_date',
      sort_order: 'desc',
    }
    if (search) params.search = search
    if (statusFilter) params.verification_status = statusFilter
    if (sourceFilter) params.source = sourceFilter
    if (indexingFilter) params.indexing = indexingFilter

    listPublications(params)
      .then((response) => {
        if (cancelled) return
        const payload = response.data || {}
        setData(payload)
        const indexes = new Set()
        for (const item of payload.items || []) {
          for (const value of item.indexing || []) {
            if (value) indexes.add(value)
          }
        }
        if (indexes.size > 0) {
          setIndexingOptions((current) =>
            Array.from(new Set([...current, ...indexes])).sort(),
          )
        }
        setErrorMessage('')
        setStatus('ready')
      })
      .catch((error) => {
        if (cancelled) return
        setErrorMessage(getReportError(error))
        setStatus('error')
      })

    return () => {
      cancelled = true
    }
  }, [yearId, page, pageSize, search, statusFilter, sourceFilter, indexingFilter, reloadKey])

  const items = useMemo(() => (data && Array.isArray(data.items) ? data.items : []), [data])

  useEffect(() => {
    let cancelled = false
    setDocCounts({})
    if (items.length === 0) return undefined
    mapWithConcurrency(items, 6, async (publication) => {
      try {
        const response = await listPublicationDocuments(publication.publication_id)
        const count = Array.isArray(response.data) ? response.data.length : 0
        return [publication.publication_id, count]
      } catch (error) {
        return [publication.publication_id, null]
      }
    }).then((pairs) => {
      if (cancelled) return
      setDocCounts(Object.fromEntries(pairs))
    })
    return () => {
      cancelled = true
    }
  }, [items])

  const handleExport = useCallback(() => {
    const rows = items.map((publication) => [
      publication.title,
      typeLabel(publication.publication_type),
      authorsLabel(publication),
      venueLabel(publication),
      publication.doi || '',
      sourceLabel(publication.source),
      indexingLabel(publication),
      publicationYearLabel(publication),
      statusMeta(publication.verification_status).label,
      publication.verification_status === 'verified'
        ? publication.points_awarded ?? 0
        : '—',
      (() => {
        const count = docCounts[publication.publication_id]
        return count === null || count === undefined ? '—' : count
      })(),
    ])
    downloadCsv(
      csvFilename(reportTypeLabel('publications'), yearName),
      CSV_HEADERS,
      rows,
    )
  }, [items, docCounts, yearName])

  const total = data ? data.total : 0
  const totalPages = data ? Math.max(data.total_pages, 1) : 1

  return (
    <section className="panel report-section" aria-label="Publication report">
      <div className="panel__head report-section__head">
        <h2 className="panel__title">
          Publication Report<span className="report-section__year"> · {yearName}</span>
        </h2>
        <button
          type="button"
          className="btn btn--ghost no-print"
          onClick={handleExport}
          disabled={items.length === 0}
        >
          Export CSV
        </button>
      </div>

      <div className="pub-toolbar no-print" aria-label="Search and filter this report">
        <div className="pub-toolbar__search">
          <label className="field__label" htmlFor="report-pub-search">
            Search
          </label>
          <input
            id="report-pub-search"
            className="field__input"
            type="search"
            placeholder="Search title, author or DOI…"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
          />
        </div>
        <div className="pub-toolbar__filters">
          <div className="field">
            <label className="field__label" htmlFor="report-pub-status">
              Status
            </label>
            <select
              id="report-pub-status"
              className="field__input"
              value={statusFilter}
              onChange={(event) => {
                setStatusFilter(event.target.value)
                setPage(1)
              }}
            >
              {STATUS_FILTERS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label className="field__label" htmlFor="report-pub-source">
              Source
            </label>
            <select
              id="report-pub-source"
              className="field__input"
              value={sourceFilter}
              onChange={(event) => {
                setSourceFilter(event.target.value)
                setPage(1)
              }}
            >
              {SOURCE_FILTERS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label className="field__label" htmlFor="report-pub-indexing">
              Indexing
            </label>
            <select
              id="report-pub-indexing"
              className="field__input"
              value={indexingFilter}
              onChange={(event) => {
                setIndexingFilter(event.target.value)
                setPage(1)
              }}
            >
              <option value="">All indexing</option>
              {indexingOptions.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </div>
          {hasActiveQuery ? (
            <button type="button" className="btn btn--ghost" onClick={clearFilters}>
              Clear filters
            </button>
          ) : null}
        </div>
      </div>

      {status === 'error' ? (
        <div className="alert alert--danger" role="alert">
          {errorMessage}{' '}
          <button
            type="button"
            className="btn btn--ghost btn--inline"
            onClick={() => setReloadKey((key) => key + 1)}
          >
            Try Again
          </button>
        </div>
      ) : null}

      {status === 'loading' && !data ? (
        <div className="report-loading" role="status">
          Loading report data…
        </div>
      ) : null}

      {status !== 'error' && data && items.length === 0 ? (
        <div className="empty-state">
          <p className="empty-state__title">
            {hasActiveQuery ? 'No publications match your search or filters.' : EMPTY_REPORT_MESSAGE}
          </p>
          <p className="empty-state__text">
            {hasActiveQuery
              ? 'Try changing your search or filters.'
              : 'Publications for this academic year will appear here.'}
          </p>
          {hasActiveQuery ? (
            <button type="button" className="btn btn--ghost" onClick={clearFilters}>
              Clear filters
            </button>
          ) : null}
        </div>
      ) : null}

      {status !== 'error' && items.length > 0 ? (
        <div className={`table-wrap${status === 'loading' ? ' report-table--busy' : ''}`}>
          <table className="table report-table">
            <caption className="visually-hidden">
              Publication report for {yearName}
            </caption>
            <thead>
              <tr>
                <th scope="col">Title</th>
                <th scope="col">Publication Type</th>
                <th scope="col">Authors</th>
                <th scope="col">Journal/Conference</th>
                <th scope="col">DOI</th>
                <th scope="col">Source/Indexing</th>
                <th scope="col">Publication Year</th>
                <th scope="col">Verification Status</th>
                <th scope="col">Points</th>
                <th scope="col">Documents</th>
              </tr>
            </thead>
            <tbody>
              {items.map((publication) => {
                const meta = statusMeta(publication.verification_status)
                const venue = venueLabel(publication)
                const index = indexingLabel(publication)
                const docCount = docCounts[publication.publication_id]
                return (
                  <tr key={publication.publication_id}>
                    <td className="table__title">
                      <Link
                        className="report-table__link"
                        to={`/publications/${publication.publication_id}`}
                      >
                        {publication.title}
                      </Link>
                    </td>
                    <td>{typeLabel(publication.publication_type)}</td>
                    <td className="report-table__wrap">{authorsLabel(publication) || '—'}</td>
                    <td className="report-table__wrap">{venue || '—'}</td>
                    <td className="report-table__mono">{publication.doi || '—'}</td>
                    <td className="report-table__wrap">
                      {sourceLabel(publication.source)}
                      {index ? <span className="report-table__sub">{index}</span> : null}
                    </td>
                    <td>{publicationYearLabel(publication)}</td>
                    <td>
                      <span
                        className={`status-pill status-pill--${publication.verification_status}`}
                      >
                        <span aria-hidden="true">{meta.symbol}</span> {meta.label}
                      </span>
                    </td>
                    <td className="report-table__points">
                      {publication.verification_status === 'verified'
                        ? publication.points_awarded ?? 0
                        : '—'}
                    </td>
                    <td>
                      <Link
                        className="report-table__link"
                        to={`/publications/${publication.publication_id}`}
                      >
                        {docCount === null || docCount === undefined
                          ? '—'
                          : docCount === 0
                            ? 'None'
                            : `${docCount} document${docCount === 1 ? '' : 's'}`}
                      </Link>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      ) : null}

      {status !== 'error' && items.length > 0 ? (
        <div className="pub-pagination no-print">
          <p className="pub-pagination__info">
            Showing {items.length} of {total} publication{total === 1 ? '' : 's'}
            {' · '}Page {page} of {totalPages}
          </p>
          <div className="pub-pagination__controls">
            <div className="field field--inline">
              <label className="field__label" htmlFor="report-page-size">
                Per page
              </label>
              <select
                id="report-page-size"
                className="field__input field__input--compact"
                value={pageSize}
                onChange={(event) => {
                  setPageSize(Number(event.target.value))
                  setPage(1)
                }}
              >
                {PAGE_SIZE_OPTIONS.map((size) => (
                  <option key={size} value={size}>
                    {size}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              className="btn btn--ghost"
              onClick={() => setPage((current) => Math.max(1, current - 1))}
              disabled={page <= 1 || status === 'loading'}
            >
              Previous
            </button>
            <button
              type="button"
              className="btn btn--ghost"
              onClick={() => setPage((current) => current + 1)}
              disabled={page >= totalPages || status === 'loading'}
            >
              Next
            </button>
          </div>
        </div>
      ) : null}
    </section>
  )
}
