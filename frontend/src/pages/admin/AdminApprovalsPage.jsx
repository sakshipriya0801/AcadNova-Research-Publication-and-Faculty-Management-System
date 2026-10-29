import { useCallback, useEffect, useState } from 'react'
import LoadingScreen from '../../components/LoadingScreen'
import {
  approveFaculty,
  listFacultyApplications,
  rejectFaculty,
} from '../../services/adminService'
import { getAdminError } from '../../utils/admin'

function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function statusClass(status) {
  return `admin-status admin-status--${status === 'approved' ? 'verified' : status === 'rejected' ? 'rejected' : 'pending'}`
}

export default function AdminApprovalsPage() {
  const [statusFilter, setStatusFilter] = useState('pending')
  const [data, setData] = useState({ items: [], total: 0 })
  const [state, setState] = useState('loading')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busyId, setBusyId] = useState('')
  const [expanded, setExpanded] = useState('')
  const [rejectTarget, setRejectTarget] = useState(null)
  const [rejectReason, setRejectReason] = useState('')
  const [rejectBusy, setRejectBusy] = useState(false)
  const [rejectError, setRejectError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  const load = useCallback(() => {
    setState('loading')
    setError('')
    listFacultyApplications({ approval_status: statusFilter, page: 1, page_size: 100 })
      .then((response) => {
        setData({ items: response.data?.items || [], total: response.data?.total || 0 })
        setState('ready')
      })
      .catch((err) => {
        setError(getAdminError(err))
        setState('error')
      })
  }, [statusFilter, reloadKey])

  useEffect(() => {
    load()
  }, [load])

  function handleApprove(application) {
    setBusyId(application.faculty_id)
    setNotice('')
    approveFaculty(application.faculty_id)
      .then(() => {
        setNotice(`${application.email} was approved.`)
        load()
      })
      .catch((err) => setError(getAdminError(err)))
      .finally(() => setBusyId(''))
  }

  function openReject(application) {
    setRejectTarget(application)
    setRejectReason('')
    setRejectError('')
  }

  function confirmReject() {
    if (!rejectTarget || rejectBusy) return
    setRejectBusy(true)
    setRejectError('')
    rejectFaculty(rejectTarget.faculty_id, rejectReason.trim() || null)
      .then(() => {
        setRejectTarget(null)
        setNotice(`${rejectTarget.email} was rejected.`)
        load()
      })
      .catch((err) => setRejectError(getAdminError(err)))
      .finally(() => setRejectBusy(false))
  }

  return (
    <div className="page admin-page">
      <div className="page__header">
        <div>
          <h1 className="page__title">Registration Approvals</h1>
          <p className="page__subtitle">
            Review and act on faculty registration applications.
          </p>
        </div>
        <div className="page__header-actions">
          <button type="button" className="btn btn--ghost" onClick={() => setReloadKey((k) => k + 1)}>
            Refresh
          </button>
        </div>
      </div>

      <section className="panel" aria-label="Application filters">
        <div className="admin-page__toolbar">
          <div className="field">
            <label className="field__label" htmlFor="approval-status">
              Status
            </label>
            <select
              id="approval-status"
              className="field__input"
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
            >
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="all">All</option>
            </select>
          </div>
        </div>
      </section>

      {notice ? (
        <p className="alert alert--success" role="status">
          {notice}
        </p>
      ) : null}
      {error ? (
        <p className="alert alert--danger" role="alert">
          {error}
        </p>
      ) : null}

      <section className="panel">
        {state === 'loading' ? <LoadingScreen message="Loading applications…" /> : null}

        {state === 'ready' && data.items.length === 0 ? (
          <p className="panel__empty">No registration applications to show.</p>
        ) : null}

        {data.items.length > 0 ? (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">Name</th>
                  <th scope="col">Email</th>
                  <th scope="col">Designation</th>
                  <th scope="col">Applied</th>
                  <th scope="col">Status</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((application) => (
                  <FragmentRow
                    key={application.faculty_id}
                    application={application}
                    expanded={expanded === application.faculty_id}
                    onToggleDetails={() =>
                      setExpanded((current) =>
                        current === application.faculty_id ? '' : application.faculty_id,
                      )
                    }
                    busy={busyId === application.faculty_id}
                    onApprove={() => handleApprove(application)}
                    onReject={() => openReject(application)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      {rejectTarget ? (
        <div className="dialog-backdrop" role="presentation">
          <div
            className="dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="reject-title"
          >
            <h2 className="dialog__title" id="reject-title">
              Reject registration
            </h2>
            <p className="dialog__message">
              Reject the application for {rejectTarget.email}? You may provide a
              reason.
            </p>
            <div className="field">
              <label className="field__label" htmlFor="reject-reason">
                Reason (optional)
              </label>
              <textarea
                id="reject-reason"
                className="field__input field__input--textarea"
                rows={3}
                value={rejectReason}
                onChange={(event) => setRejectReason(event.target.value)}
              />
            </div>
            {rejectError ? (
              <p className="alert alert--danger" role="alert">
                {rejectError}
              </p>
            ) : null}
            <div className="dialog__actions">
              <button
                type="button"
                className="btn btn--ghost"
                onClick={() => {
                  if (!rejectBusy) setRejectTarget(null)
                }}
                disabled={rejectBusy}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn--danger"
                onClick={confirmReject}
                disabled={rejectBusy}
              >
                {rejectBusy ? 'Rejecting…' : 'Reject'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}

function FragmentRow({ application, expanded, onToggleDetails, busy, onApprove, onReject }) {
  return (
    <>
      <tr>
        <td>{application.name || '—'}</td>
        <td>{application.email}</td>
        <td>{application.designation || '—'}</td>
        <td>{formatDate(application.created_at)}</td>
        <td>
          <span className={statusClass(application.approval_status)}>
            {application.approval_status}
          </span>
        </td>
        <td>
          <div className="admin-actions">
            <button
              type="button"
              className="btn btn--small btn--ghost"
              onClick={onToggleDetails}
              aria-expanded={expanded}
            >
              {expanded ? 'Hide' : 'Details'}
            </button>
            {application.approval_status === 'pending' ? (
              <>
                <button
                  type="button"
                  className="btn btn--small btn--primary"
                  onClick={onApprove}
                  disabled={busy}
                >
                  Approve
                </button>
                <button
                  type="button"
                  className="btn btn--small btn--danger-outline"
                  onClick={onReject}
                  disabled={busy}
                >
                  Reject
                </button>
              </>
            ) : null}
          </div>
        </td>
      </tr>
      {expanded ? (
        <tr className="admin-detail-row">
          <td colSpan={6}>
            <dl className="admin-detail-list">
              <div className="admin-detail-list__row">
                <dt>Employee ID</dt>
                <dd>{application.employee_id || '—'}</dd>
              </div>
              <div className="admin-detail-list__row">
                <dt>Department</dt>
                <dd>{application.department_id || '—'}</dd>
              </div>
              <div className="admin-detail-list__row">
                <dt>Rejection reason</dt>
                <dd>{application.rejection_reason || '—'}</dd>
              </div>
            </dl>
          </td>
        </tr>
      ) : null}
    </>
  )
}
