import { useCallback, useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import ConfirmDialog from '../components/ConfirmDialog'
import LoadingScreen from '../components/LoadingScreen'
import {
  deletePublication,
  listPublications,
} from '../services/publicationService'
import { getPublicationError } from '../utils/errors'
import {
  PUBLICATION_SOURCES,
  PUBLICATION_TYPES,
  SORT_FIELDS,
  formatDate,
  sourceLabel,
  statusMeta,
  typeLabel,
  yearFromDate,
} from '../utils/publication'

const STATUS_FILTERS = [
  { value: '', label: 'All statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'verified', label: 'Verified' },
  { value: 'rejected', label: 'Rejected' },
]

const PAGE_SIZE_OPTIONS = [10, 25, 50]

const EMPTY_FILTERS = {
  verification_status: '',
  publication_type: '',
  source: '',
  indexing: '',
  publication_year: '',
}

export default function PublicationsPage() {
  const location = useLocation()
  const [notice, setNotice] = useState(location.state?.notice || '')

  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const [sortBy, setSortBy] = useState('publication_date')
  const [sortOrder, setSortOrder] = useState('desc')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [reloadKey, setReloadKey] = useState(0)

  const [data, setData] = useState(null)
  const [status, setStatus] = useState('loading')
  const [errorMessage, setErrorMessage] = useState('')

  const [yearOptions, setYearOptions] = useState([])
  const [indexingOptions, setIndexingOptions] = useState([])

  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleteBusy, setDeleteBusy] = useState(false)
  const [deleteError, setDeleteError] = useState('')

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim())
      setPage(1)
    }, 400)
    return () => clearTimeout(timer)
  }, [searchInput])

  const collectOptions = useCallback((items) => {
    const years = new Set()
    const indexes = new Set()
    for (const item of items || []) {
      const year = item.publication_year || yearFromDate(item.publication_date)
      if (year) years.add(year)
      for (const value of item.indexing || []) {
        if (value) indexes.add(value)
      }
    }
    if (years.size > 0) {
      setYearOptions((current) =>
        Array.from(new Set([...current, ...years])).sort((a, b) => b - a),
      )
    }
    if (indexes.size > 0) {
      setIndexingOptions((current) =>
        Array.from(new Set([...current, ...indexes])).sort(),
      )
    }
  }, [])

  useEffect(() => {
    listPublications({
      page: 1,
      page_size: 100,
      sort_by: 'publication_date',
      sort_order: 'desc',
    })
      .then((response) => collectOptions(response.data.items))
      .catch(() => undefined)
  }, [collectOptions])

  useEffect(() => {
    let cancelled = false
    setStatus('loading')

    const params = { page, page_size: pageSize, sort_by: sortBy, sort_order: sortOrder }
    if (search) params.search = search
    if (filters.verification_status) params.verification_status = filters.verification_status
    if (filters.publication_type) params.publication_type = filters.publication_type
    if (filters.source) params.source = filters.source
    if (filters.indexing) params.indexing = filters.indexing
    if (filters.publication_year) params.publication_year = Number(filters.publication_year)

    listPublications(params)
      .then((response) => {
        if (cancelled) return
        setData(response.data)
        collectOptions(response.data.items)
        setStatus('ready')
      })
      .catch((error) => {
        if (cancelled) return
        setErrorMessage(getPublicationError(error))
        setStatus('error')
      })

    return () => {
      cancelled = true
    }
  }, [search, filters, sortBy, sortOrder, page, pageSize, reloadKey, collectOptions])

  function updateFilter(field, value) {
    setFilters((current) => ({ ...current, [field]: value }))
    setPage(1)
  }

  function clearSearchAndFilters() {
    setSearchInput('')
    setSearch('')
    setFilters(EMPTY_FILTERS)
    setPage(1)
  }

  function confirmDelete() {
    if (!deleteTarget || deleteBusy) return undefined
    setDeleteBusy(true)
    setDeleteError('')
    return deletePublication(deleteTarget.publication_id)
      .then(() => {
        setDeleteTarget(null)
        setNotice('Publication deleted.')
        if (data && data.items.length === 1 && page > 1) {
          setPage(page - 1)
        } else {
          setReloadKey((key) => key + 1)
        }
      })
      .catch((error) => {
        setDeleteError(getPublicationError(error))
      })
      .finally(() => {
        setDeleteBusy(false)
      })
  }

  const hasActiveQuery =
    Boolean(search) ||
    Object.values(filters).some((value) => value !== '' && value !== null)

  const items = data?.items || []
  const total = data?.total ?? 0
  const totalPages = data?.total_pages ?? 0

  if (status === 'loading' && !data) {
    return <LoadingScreen message="Loading publications…" />
  }

  if (status === 'error' && !data) {
    return (
      <div className="page">
        <div className="page__header">
          <h1 className="page__title">My Publications</h1>
          <Link className="btn btn--primary" to="/publications/new">
            + Add Publication
          </Link>
        </div>
        <div className="empty-state">
          <p className="empty-state__title">Unable to load publications</p>
          <p className="empty-state__text">{errorMessage}</p>
          <button
            type="button"
            className="btn btn--primary"
            onClick={() => setReloadKey((key) => key + 1)}
          >
            Try again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="page publications-page">
      <div className="page__header">
        <div>
          <h1 className="page__title">My Publications</h1>
          <p className="page__subtitle">
            {total > 0
              ? `${total} publication${total === 1 ? '' : 's'} in your record`
              : 'Publications you have added to the system'}
          </p>
        </div>
        <div className="page__header-actions">
          <Link className="btn btn--ghost" to="/publications/search">
            Search &amp; Import
          </Link>
          <Link className="btn btn--primary" to="/publications/new">
            + Add Publication
          </Link>
        </div>
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

      <section className="pub-toolbar" aria-label="Search and filter publications">
        <div className="pub-toolbar__search">
          <label className="field__label" htmlFor="pub-search">
            Search
          </label>
          <div className="pub-toolbar__search-row">
            <input
              id="pub-search"
              className="field__input"
              type="search"
              placeholder="Search by title, journal, conference or DOI"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
            />
            {searchInput ? (
              <button
                type="button"
                className="btn btn--ghost"
                onClick={() => setSearchInput('')}
              >
                Clear
              </button>
            ) : null}
          </div>
        </div>

        <div className="pub-toolbar__filters">
          <div className="field">
            <label className="field__label" htmlFor="filter-status">
              Status
            </label>
            <select
              id="filter-status"
              className="field__input"
              value={filters.verification_status}
              onChange={(event) => updateFilter('verification_status', event.target.value)}
            >
              {STATUS_FILTERS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div className="field">
            <label className="field__label" htmlFor="filter-type">
              Type
            </label>
            <select
              id="filter-type"
              className="field__input"
              value={filters.publication_type}
              onChange={(event) => updateFilter('publication_type', event.target.value)}
            >
              <option value="">All types</option>
              {PUBLICATION_TYPES.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div className="field">
            <label className="field__label" htmlFor="filter-year">
              Year
            </label>
            <select
              id="filter-year"
              className="field__input"
              value={filters.publication_year}
              onChange={(event) => updateFilter('publication_year', event.target.value)}
            >
              <option value="">All years</option>
              {yearOptions.map((year) => (
                <option key={year} value={year}>
                  {year}
                </option>
              ))}
            </select>
          </div>

          <div className="field">
            <label className="field__label" htmlFor="filter-source">
              Source
            </label>
            <select
              id="filter-source"
              className="field__input"
              value={filters.source}
              onChange={(event) => updateFilter('source', event.target.value)}
            >
              <option value="">All sources</option>
              {PUBLICATION_SOURCES.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div className="field">
            <label className="field__label" htmlFor="filter-indexing">
              Indexing
            </label>
            <select
              id="filter-indexing"
              className="field__input"
              value={filters.indexing}
              onChange={(event) => updateFilter('indexing', event.target.value)}
            >
              <option value="">All indexing</option>
              {indexingOptions.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="pub-toolbar__sort">
          <div className="field">
            <label className="field__label" htmlFor="sort-by">
              Sort by
            </label>
            <select
              id="sort-by"
              className="field__input"
              value={sortBy}
              onChange={(event) => setSortBy(event.target.value)}
            >
              {SORT_FIELDS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <button
            type="button"
            className="btn btn--ghost pub-toolbar__sort-dir"
            onClick={() => setSortOrder((order) => (order === 'desc' ? 'asc' : 'desc'))}
            aria-label={`Sort order: ${sortOrder === 'desc' ? 'descending' : 'ascending'}. Activate to switch.`}
          >
            {sortOrder === 'desc' ? '↓ Descending' : '↑ Ascending'}
          </button>
        </div>
      </section>

      {status === 'error' ? (
        <div className="alert alert--danger" role="alert">
          {errorMessage}{' '}
          <button
            type="button"
            className="btn btn--ghost btn--inline"
            onClick={() => setReloadKey((key) => key + 1)}
          >
            Retry
          </button>
        </div>
      ) : null}

      {status === 'loading' && data ? (
        <p className="pub-toolbar__updating" role="status">
          Updating results…
        </p>
      ) : null}

      {items.length === 0 ? (
        <div className="empty-state">
          <p className="empty-state__title">
            {hasActiveQuery ? 'No publications found.' : 'No publications yet.'}
          </p>
          <p className="empty-state__text">
            {hasActiveQuery
              ? 'Try changing your search or filters.'
              : 'Add your first publication to start building your record.'}
          </p>
          {hasActiveQuery ? (
            <button type="button" className="btn btn--ghost" onClick={clearSearchAndFilters}>
              Clear search and filters
            </button>
          ) : (
            <Link className="btn btn--primary" to="/publications/new">
              + Add Publication
            </Link>
          )}
        </div>
      ) : (
        <section
          className={`panel${status === 'loading' ? ' panel--busy' : ''}`}
          aria-label="Publications list"
          aria-busy={status === 'loading'}
        >
          <div className="table-wrap">
            <table className="table pub-table">
              <caption className="visually-hidden">Your publications</caption>
              <thead>
                <tr>
                  <th scope="col">Title</th>
                  <th scope="col">Type</th>
                  <th scope="col">Date</th>
                  <th scope="col">Source</th>
                  <th scope="col">Indexing</th>
                  <th scope="col">Status</th>
                  <th scope="col">Points</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((publication) => {
                  const meta = statusMeta(publication.verification_status)
                  const venue = publication.journal_name || publication.conference_name
                  return (
                    <tr key={publication.publication_id}>
                      <td className="table__title">
                        <Link
                          className="pub-table__title-link"
                          to={`/publications/${publication.publication_id}`}
                        >
                          {publication.title}
                        </Link>
                        {venue ? <span className="table__subtitle">{venue}</span> : null}
                      </td>
                      <td>{typeLabel(publication.publication_type)}</td>
                      <td>
                        {formatDate(publication.publication_date) ||
                          publication.publication_year ||
                          '—'}
                      </td>
                      <td>{sourceLabel(publication.source)}</td>
                      <td>
                        {publication.indexing?.length
                          ? publication.indexing.join(', ')
                          : '—'}
                      </td>
                      <td>
                        <span
                          className={`status-pill status-pill--${publication.verification_status}`}
                        >
                          <span aria-hidden="true">{meta.symbol}</span> {meta.label}
                        </span>
                      </td>
                      <td className="pub-table__points">
                        {publication.verification_status === 'verified'
                          ? publication.points_awarded ?? 0
                          : '—'}
                      </td>
                      <td>
                        <div className="pub-table__actions">
                          <Link
                            className="btn btn--ghost btn--small"
                            to={`/publications/${publication.publication_id}`}
                          >
                            View
                          </Link>
                          <Link
                            className="btn btn--ghost btn--small"
                            to={`/publications/${publication.publication_id}/edit`}
                          >
                            Edit
                          </Link>
                          <button
                            type="button"
                            className="btn btn--ghost btn--small btn--danger-outline"
                            onClick={() => {
                              setDeleteError('')
                              setDeleteTarget(publication)
                            }}
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          <div className="pub-pagination">
            <p className="pub-pagination__info">
              Showing {items.length} of {total} publication{total === 1 ? '' : 's'}
              {' · '}Page {page} of {Math.max(totalPages, 1)}
            </p>
            <div className="pub-pagination__controls">
              <div className="field field--inline">
                <label className="field__label" htmlFor="page-size">
                  Per page
                </label>
                <select
                  id="page-size"
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
        </section>
      )}

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title="Delete publication"
        message={`Are you sure you want to delete "${
          deleteTarget?.title || 'this publication'
        }"? This cannot be undone.`}
        confirmLabel="Delete"
        busy={deleteBusy}
        error={deleteError}
        onConfirm={confirmDelete}
        onCancel={() => {
          if (!deleteBusy) {
            setDeleteTarget(null)
            setDeleteError('')
          }
        }}
      />
    </div>
  )
}
