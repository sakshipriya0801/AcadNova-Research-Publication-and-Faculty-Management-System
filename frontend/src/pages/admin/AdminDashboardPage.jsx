import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { getAdminSummary, getAuditLogs } from '../../services/adminService'
import LoadingScreen from '../../components/LoadingScreen'
import {
  ADMIN_PERMISSION_TEXT,
  ADMIN_PERMISSION_TITLE,
  getAdminError,
} from '../../utils/admin'

const STATS = [
  { key: 'faculty_count', label: 'Total Faculty' },
  { key: 'active_faculty_count', label: 'Active Faculty' },
  { key: 'pending_registration_count', label: 'Pending Registrations' },
  { key: 'publication_count', label: 'Total Publications' },
  { key: 'pending_verification_count', label: 'Awaiting Verification' },
]

const QUICK_LINKS = [
  {
    to: '/admin/faculty',
    title: 'Faculty Management',
    text: 'Manage faculty and add new faculty accounts.',
  },
  {
    to: '/admin/approvals',
    title: 'Registration Approvals',
    text: 'Approve or reject pending faculty registrations.',
  },
  {
    to: '/admin/review',
    title: 'Verification Queue',
    text: 'Review and verify submitted publications.',
  },
  {
    to: '/admin/publications',
    title: 'Publications',
    text: 'Search and inspect all publication records.',
  },
  {
    to: '/admin/reports',
    title: 'Reports & Analytics',
    text: 'Institution-wide statistics and verification overview.',
  },
]

function activityLabel(action, entityType) {
  const type = entityType ? entityType.replace(/_/g, ' ') : ''
  const verb = action.replace(/_/g, ' ')
  return type ? `${verb} · ${type}` : verb
}

function whenLabel(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString()
}

export default function AdminDashboardPage() {
  const { user } = useAuth()
  const [summary, setSummary] = useState(null)
  const [activity, setActivity] = useState([])
  const [status, setStatus] = useState('loading')
  const [errorMessage, setErrorMessage] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  const isAdmin = user?.role === 'admin'

  const load = useCallback(() => {
    if (!isAdmin) return
    setStatus('loading')
    Promise.all([
      getAdminSummary(),
      getAuditLogs({ page: 1, page_size: 6 }),
    ])
      .then(([summaryRes, auditRes]) => {
        setSummary(summaryRes.data)
        setActivity(auditRes.data?.items || [])
        setStatus('ready')
      })
      .catch((error) => {
        setErrorMessage(getAdminError(error, 'Unable to load dashboard statistics.'))
        setStatus('error')
      })
  }, [isAdmin, reloadKey])

  useEffect(() => {
    load()
  }, [load])

  if (!isAdmin) {
    return (
      <div className="page admin-page">
        <div className="page__header">
          <div>
            <h1 className="page__title">Administration</h1>
          </div>
        </div>
        <div className="empty-state">
          <p className="empty-state__title">{ADMIN_PERMISSION_TITLE}</p>
          <p className="empty-state__text">{ADMIN_PERMISSION_TEXT}</p>
          <Link className="btn btn--primary" to="/dashboard">
            Back to Dashboard
          </Link>
        </div>
      </div>
    )
  }

  if (status === 'loading') {
    return <LoadingScreen message="Loading admin console…" />
  }

  return (
    <div className="page admin-page">
      <div className="page__header">
        <div>
          <h1 className="page__title">Admin Console</h1>
          <p className="page__subtitle">
            Institution-wide statistics and management shortcuts.
          </p>
        </div>
        <div className="page__header-actions">
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => setReloadKey((key) => key + 1)}
          >
            Refresh
          </button>
        </div>
      </div>

      {status === 'error' ? (
        <div className="empty-state">
          <p className="empty-state__title">Unable to load statistics</p>
          <p className="empty-state__text">{errorMessage}</p>
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => setReloadKey((key) => key + 1)}
          >
            Try Again
          </button>
        </div>
      ) : (
        <>
          <div className="admin-stats">
            {STATS.map((stat) => {
              const raw = summary ? summary[stat.key] : null
              return (
                <div className="admin-stat" key={stat.key}>
                  <p className="admin-stat__value">{raw ?? '—'}</p>
                  <p className="admin-stat__label">{stat.label}</p>
                </div>
              )
            })}
          </div>

          <section className="panel" aria-label="Recent activity">
            <h2 className="panel__title">Recent administrative activity</h2>
            {activity.length === 0 ? (
              <p className="panel__empty">No recent activity.</p>
            ) : (
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th scope="col">When</th>
                      <th scope="col">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activity.map((item, index) => (
                      <tr key={item.audit_id || `${item.action}-${index}`}>
                        <td>{whenLabel(item.timestamp)}</td>
                        <td>{activityLabel(item.action, item.entity_type)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <div className="admin-quicknav">
            {QUICK_LINKS.map((item) => (
              <Link className="admin-quick-card" to={item.to} key={item.to}>
                <p className="admin-quick-card__title">{item.title}</p>
                <p className="admin-quick-card__text">{item.text}</p>
              </Link>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
