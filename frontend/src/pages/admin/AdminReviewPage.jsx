import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { listFaculty } from '../../services/adminService'
import { listPublicationsAdmin } from '../../services/verificationService'
import {
  formatDate,
  sourceLabel,
  statusMeta,
  typeLabel,
} from '../../utils/publication'
import {
  getVerificationError,
  REVIEW_SORT_FIELDS,
  REVIEW_STATUS_FILTERS,
} from '../../utils/verification'

const PAGE_SIZE_OPTIONS = [10, 25, 50]

export default function AdminReviewPage() {
  const { user } = useAuth()
  const location = useLocation()
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('pending')
  const [sortBy, setSortBy] = useState('created_at')
  const [sortOrder, setSortOrder] = useState('desc')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [data, setData] = useState(null)
  const [status, setStatus] = useState('loading')
  const [errorMessage, setErrorMessage] = useState('')
  const [notice, setNotice] = useState(location.state?.notice || '')
  const [reloadKey, setReloadKey] = useState(0)
  const [facultyNames, setFacultyNames] = useState({})

  const isAdmin = user?.role === 'admin'
  const items = data?.items || []
  const total = data?.total ?? 0
  const totalPages = data?.total_pages ?? 0

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim())
      setPage(1)
    }, 400)
    return () => clearTimeout(timer)
  }, [searchInput])

  useEffect(() => {
    if (!isAdmin) return undefined
    let cancelled = false
    listFaculty({ page: 1, page_size: 100 })
      .then((response) => {
        if (cancelled) return
        const map = {}
        for (const profile of response.data?.items || []) {
          map[profile.faculty_id] = profile.name
        }
        setFacultyNames(map)
      })
      .catch(() => {
        setFacultyNames({})
      })
    return () => {
      cancelled = true
    }
  }, [isAdmin])

  const load = useCallback(() => {
    if (!isAdmin) return
    setStatus('loading')
    const params = {
      page,
      page_size: pageSize,
      sort_by: sortBy,
      sort_order: sortOrder,
    }
    if (search) params.search = search
    if (statusFilter) params.verification_status = statusFilter
    listPublicationsAdmin(params)
      .then((response) => {
        setData(response.data)
        setErrorMessage('')
        setStatus('ready')
      })
      .catch((error) => {
        setErrorMessage(
          getVerificationError(error, 'Unable to load the review queue.'),
        )
        setStatus('error')
      })
  }, [
    isAdmin,
    page,
    pageSize,
    search,
    sortOrder,
    sortBy,
    statusFilter,
    reloadKey,
  ])

  useEffect(() => {
    load()
  }, [load])

  const hasActiveQuery = Boolean(search) || Boolean(statusFilter)

  const statusLabel = useMemo(() => {
    const option = REVIEW_STATUS_FILTERS.find(
      (item) => item.value === statusFilter,
    )
    return option ? option.label : ''
  }, [statusFilter])

  if (!isAdmin) {
    return (
      <div className="page">
        <div className="page__header">
          <div>
            <h1 className="page__title">Publication Review</h1>
          </div>
        </div>
        <div className="empty-state">
          <p className="empty-state__title">You don&apos;t have permission</p>
          <p className="empty-state__text">
            The review queue is available to administrators only.
          </p>
          <Link className="btn btn--primary" to="/dashboard">
            Back to Dashboard
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="page publications-page">
      <div className="page__header">
        <div>
          <h1 className="page__title">Publication Review</h1>
          <p className="page__subtitle">
            {total > 0
              ? `${total} publication${total === 1 ? '' : 's'}${
                  statusFilter === 'pending'
                    ? ' awaiting review'
                    : ` with status “${statusLabel}”`
                }`
              : statusFilter === 'pending'
                ? 'Publications awaiting verification'
                : 'Review publications across all faculty'}
          </p>
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
          <label className="field__label" htmlFor="review-search">
            Search
          </label>
          <div className="pub-toolbar__search-row">
            <input
              id="review-search"
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
            <label className="field__label" htmlFor="review-status">
              Status
            </label>
            <select
              id="review-status"
              className="field__input"
              value={statusFilter}
              onChange={(event) => {
                setStatusFilter(event.target.value)
                setPage(1)
              }}
            >
              {REVIEW_STATUS_FILTERS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="pub-toolbar__sort">
          <div className="field">
            <label className="field__label" htmlFor="review-sort">
              Sort by
            </label>
            <select
              id="review-sort"
              className="field__input"
              value={sortBy}
              onChange={(event) => setSortBy(event.target.value)}
            >
              {REVIEW_SORT_FIELDS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <button
            type="button"
            className="btn btn--ghost pub-toolbar__sort-dir"
            onClick={() =>
              setSortOrder((order) => (order === 'desc' ? 'asc' : 'desc'))
            }
            aria-label={`Sort order: ${
              sortOrder === 'desc' ? 'descending' : 'ascending'
            }. Activate to switch.`}
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

      {status === 'loading' && !data ? (
        <p className="pub-toolbar__updating" role="status">
          Loading publications…
        </p>
      ) : null}

      {status !== 'error' && status !== 'loading' && items.length === 0 ? (
        <div className="empty-state">
          <p className="empty-state__title">
            {hasActiveQuery
              ? 'No publications found.'
              : 'No publications yet.'}
          </p>
          <p className="empty-state__text">
            {statusFilter === 'pending' && !search
              ? 'Every publication has been reviewed.'
              : 'Try changing your search or filters.'}
          </p>
          {hasActiveQuery ? (
            <button
              type="button"
              className="btn btn--ghost"
              onClick={() => {
                setSearchInput('')
                setStatusFilter('')
                setPage(1)
              }}
            >
              Clear search and filters
            </button>
          ) : null}
        </div>
      ) : null}

      {items.length > 0 ? (
        <section
          className={`panel${status === 'loading' ? ' panel--busy' : ''}`}
          aria-label="Publications awaiting review"
          aria-busy={status === 'loading'}
        >
          <div className="table-wrap">
            <table className="table pub-table">
              <caption className="visually-hidden">
                Publications in the review queue
              </caption>
              <thead>
                <tr>
                  <th scope="col">Title</th>
                  <th scope="col">Faculty</th>
                  <th scope="col">Type</th>
                  <th scope="col">Date</th>
                  <th scope="col">Source</th>
                  <th scope="col">Status</th>
                  <th scope="col">Points</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((publication) => {
                  const meta = statusMeta(publication.verification_status)
                  const venue =
                    publication.journal_name || publication.conference_name
                  return (
                    <tr key={publication.publication_id}>
                      <td className="table__title">
                        <Link
                          className="pub-table__title-link"
                          to={`/admin/review/${publication.publication_id}`}
                        >
                          {publication.title}
                        </Link>
                        {venue ? <span className="table__subtitle">{venue}</span> : null}
                      </td>
                      <td>
                        {publication.faculty_id
                          ? facultyNames[publication.faculty_id] || '—'
                          : '—'}
                      </td>
                      <td>{typeLabel(publication.publication_type)}</td>
                      <td>
                        {formatDate(publication.publication_date) ||
                          publication.publication_year ||
                          '—'}
                      </td>
                      <td>{sourceLabel(publication.source)}</td>
                      <td>
                        <span
                          className={`status-pill status-pill--${publication.verification_status}`}
                        >
                          <span aria-hidden="true">{meta.symbol}</span>{' '}
                          {meta.label}
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
                            to={`/admin/review/${publication.publication_id}`}
                          >
                            Review
                          </Link>
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
              Showing {items.length} of {total} publication
              {total === 1 ? '' : 's'}
              {' · '}Page {page} of {Math.max(totalPages, 1)}
            </p>
            <div className="pub-pagination__controls">
              <div className="field field--inline">
                <label className="field__label" htmlFor="review-page-size">
                  Per page
                </label>
                <select
                  id="review-page-size"
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
      ) : null}
    </div>
  )
}
