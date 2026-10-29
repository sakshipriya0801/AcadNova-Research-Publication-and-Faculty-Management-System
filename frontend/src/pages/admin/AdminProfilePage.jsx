import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'

export default function AdminProfilePage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/admin/login', { replace: true })
  }

  return (
    <div className="page admin-page">
      <div className="page__header">
        <div>
          <h1 className="page__title">Profile &amp; Settings</h1>
          <p className="page__subtitle">Your administrator account details.</p>
        </div>
      </div>

      <section className="panel" aria-label="Administrator account">
        <h2 className="panel__title">Account</h2>
        <dl className="admin-detail-list">
          <div className="admin-detail-list__row">
            <dt>Email</dt>
            <dd>{user?.email || '—'}</dd>
          </div>
          <div className="admin-detail-list__row">
            <dt>Role</dt>
            <dd>
              <span className="admin-badge admin-badge--current">Administrator</span>
            </dd>
          </div>
          <div className="admin-detail-list__row">
            <dt>User ID</dt>
            <dd className="admin-ellipsis">{user?.user_id || '—'}</dd>
          </div>
          <div className="admin-detail-list__row">
            <dt>Linked faculty profile</dt>
            <dd>{user?.faculty_id ? user.faculty_id : 'None (administrator account)'}</dd>
          </div>
        </dl>
        <p className="admin-form__hint">
          Administrator accounts are created out-of-band with
          <code> backend/scripts/create_admin.py</code>; there is no public admin
          registration.
        </p>
      </section>

      <section className="panel" aria-label="Session">
        <h2 className="panel__title">Session</h2>
        <button type="button" className="btn btn--danger-outline" onClick={handleLogout}>
          Log out
        </button>
      </section>
    </div>
  )
}
