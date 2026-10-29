import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function ForbiddenPage() {
  const { user } = useAuth()
  const home = user?.role === 'admin' ? '/admin/dashboard' : user ? '/dashboard' : '/login'

  return (
    <div className="page">
      <div className="empty-state">
        <p className="empty-state__title">403 — Access denied</p>
        <p className="empty-state__text">
          You do not have permission to view this page. Administrator access is
          required for the admin console.
        </p>
        {user ? (
          <Link className="btn btn--primary" to={home}>
            Back to my dashboard
          </Link>
        ) : (
          <Link className="btn btn--primary" to="/login">
            Go to sign in
          </Link>
        )}
      </div>
    </div>
  )
}
