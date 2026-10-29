import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function NotFound() {
  const { isAuthenticated, loading } = useAuth()
  const target = loading ? '/login' : isAuthenticated ? '/dashboard' : '/login'
  const label = loading ? 'Go to sign in' : isAuthenticated ? 'Go to Dashboard' : 'Go to sign in'

  return (
    <div className="not-found">
      <p className="not-found__code">404</p>
      <h1 className="not-found__title">Page not found</h1>
      <p className="not-found__text">
        The page you are looking for does not exist or may have been moved.
      </p>
      <Link className="btn btn--primary" to={target}>
        {label}
      </Link>
    </div>
  )
}
