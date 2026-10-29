import { useCallback, useEffect, useState } from 'react'
import LoadingScreen from '../../components/LoadingScreen'
import { getAuditLogs } from '../../services/adminService'
import { getAdminError } from '../../utils/admin'
import { formatDate } from '../../utils/publication'

const PAGE_SIZE = 25

function whenLabel(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString()
}

function summarize(value) {
  if (value == null) return '—'
  if (typeof value === 'string') return value
  try {
    const text = JSON.stringify(value)
    return text.length > 80 ? `${text.slice(0, 77)}…` : text
  } catch {
    return '—'
  }
}

export default function AdminAuditLogsPage() {
  const [action, setAction] = useState('')
  const [entityType, setEntityType] = useState('')
  const [page, setPage] = useState(1)
  const [data, setData] = useState({ items: [], total: 0, total_pages: 0 })
  const [state, setState] = useState('loading')
  const [error, setError] = useState('')

  useEffect(() => {
    setPage(1)
  }, [action, entityType])

  const load = useCallback(() => {
    setState('loading')
    setError('')
    const params = { page, page_size: PAGE_SIZE }
    if (action) params.action = action
    if (entityType) params.entity_type = entityType
    getAuditLogs(params)
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
  }, [page, action, entityType])

  useEffect(() => {
    load()
  }, [load])

  if (state === 'loading' && data.items.length === 0) {
    return <LoadingScreen message="Loading audit logs…" />
  }

  return (
    <div className="page admin-page">
      <div className="page__header">
        <div>
          <h1 className="page__title">Verification History &amp; Audit Logs</h1>
          <p className="page__subtitle">
            Recorded administrative actions and verification activity.
          </p>
        </div>
      </div>

      <section className="panel" aria-label="Audit filters">
        <div className="admin-page__toolbar">
          <div className="field">
            <label className="field__label" htmlFor="audit-action">
              Action contains
            </label>
            <input
              id="audit-action"
              className="field__input"
              type="search"
              placeholder="e.g. verify, update, create"
              value={action}
              onChange={(event) => setAction(event.target.value.trim())}
            />
          </div>
          <div className="field">
            <label className="field__label" htmlFor="audit-entity">
              Entity type
            </label>
            <input
              id="audit-entity"
              className="field__input"
              type="search"
              placeholder="e.g. publication, document, faculty"
              value={entityType}
              onChange={(event) => setEntityType(event.target.value.trim())}
            />
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
          <p className="panel__empty">No audit records found.</p>
        ) : null}

        {data.items.length > 0 ? (
          <>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th scope="col">When</th>
                    <th scope="col">Action</th>
                    <th scope="col">Entity</th>
                    <th scope="col">Entity ID</th>
                    <th scope="col">Details</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((item, index) => (
                    <tr key={item.audit_id || `${item.action}-${index}`}>
                      <td>{whenLabel(item.timestamp)}</td>
                      <td>{item.action}</td>
                      <td>{item.entity_type || '—'}</td>
                      <td>
                        <span className="admin-ellipsis" title={item.entity_id || ''}>
                          {item.entity_id || '—'}
                        </span>
                      </td>
                      <td>
                        <span className="admin-audit__detail" title={summarize(item.new_value)}>
                          {summarize(item.new_value ?? item.old_value)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {data.total_pages > 1 ? (
              <div className="admin-pager">
                <span className="admin-pager__info">
                  Page {page} of {data.total_pages} · {data.total} records
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
