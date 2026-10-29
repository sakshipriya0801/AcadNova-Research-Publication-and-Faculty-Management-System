import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import LoadingScreen from '../../components/LoadingScreen'
import { listPublicationsAdmin } from '../../services/adminService'
import { formatDate, typeLabel } from '../../utils/publication'
import { getAdminError } from '../../utils/admin'

const PAGE_SIZE = 20
const STATUSES = [
  { value: '', label: 'All statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'verified', label: 'Verified' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'needs_review', label: 'Needs review' },
]

function statusClass(status) {
  return `admin-status admin-status--${status || 'pending'}`
}

export default function AdminPublicationsPage() {
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)
  const [data, setData] = useState({ items: [], total: 0, total_pages: 0 })
  const [state, setState] = useState('loading')
  const [error, setError] = useState('')

  useEffect(() => {
    const timer = setTimeout(() => setSearch(searchInput.trim()), 400)
    return () => clearTimeout(timer)
  }, [searchInput])

  useEffect(() => {
    setPage(1)
  }, [search, status])

  const load = useCallback(() => {
    setState('loading')
    setError('')
    const params = { page, page_size: PAGE_SIZE, sort_by: 'created_at', sort_order: 'desc' }
    if (search) params.search = search
    if (status) params.verification_status = status
    listPublicationsAdmin(params)
      .then((response) => {
        const body = response.data || {}
        setData({
          items: body.items || [],
          total: body.total || 0,
          total_pages: body.total_pages || 0,
        })
        setState('ready')
      })
      .catch((err) => {
        setError(getAdminError(err))
        setState('error')
      })
  }, [page, search, status])

  useEffect(() => {
    load()
  }, [load])

  if (state === 'loading' && data.items.length === 0) {
    return <LoadingScreen message="Loading publications…" />
  }

  return (
    <div className="page admin-page">
      <div className="page__header">
        <div>
          <h1 className="page__title">Publication Management</h1>
          <p className="page__subtitle">
            Search and inspect all publication records across the institution.
          </p>
        </div>
      </div>

      <section className="panel" aria-label="Publication filters">
        <div className="admin-page__toolbar">
          <div className="field admin-page__toolbar-grow">
            <label className="field__label" htmlFor="apub-search">
              Search
            </label>
            <input
              id="apub-search"
              className="field__input"
              type="search"
              placeholder="Title, journal, conference or DOI"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
            />
          </div>
          <div className="field">
            <label className="field__label" htmlFor="apub-status">
              Verification status
            </label>
            <select
              id="apub-status"
              className="field__input"
              value={status}
              onChange={(event) => setStatus(event.target.value)}
            >
              {STATUSES.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {state === 'error' ? (
        <p className="alert alert--danger" role="alert">
          {error}
        </p>
      ) : null}

      <section className="panel">
        {state === 'ready' && data.items.length === 0 ? (
          <p className="panel__empty">No publications match your filters.</p>
        ) : null}

        {data.items.length > 0 ? (
          <>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th scope="col">Title</th>
                    <th scope="col">Type</th>
                    <th scope="col">Date</th>
                    <th scope="col">Status</th>
                    <th scope="col">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((item) => (
                    <tr key={item.publication_id}>
                      <td>
                        <span className="admin-ellipsis" title={item.title}>
                          {item.title}
                        </span>
                      </td>
                      <td>{typeLabel(item.publication_type)}</td>
                      <td>{formatDate(item.publication_date) || '—'}</td>
                      <td>
                        <span className={statusClass(item.verification_status)}>
                          {item.verification_status || 'pending'}
                        </span>
                      </td>
                      <td>
                        <Link
                          className="btn btn--small btn--ghost"
                          to={`/admin/review/${item.publication_id}`}
                        >
                          Inspect
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {data.total_pages > 1 ? (
              <div className="admin-pager">
                <span className="admin-pager__info">
                  Page {page} of {data.total_pages} · {data.total} publications
                </span>
                <div className="admin-pager__controls">
                  <button
                    type="button"
                    className="btn btn--ghost btn--small"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page <= 1}
                  >
                    Previous
                  </button>
                  <button
                    type="button"
                    className="btn btn--ghost btn--small"
                    onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
                    disabled={page >= data.total_pages}
                  >
                    Next
                  </button>
                </div>
              </div>
            ) : null}
          </>
        ) : null}
      </section>
    </div>
  )
}
