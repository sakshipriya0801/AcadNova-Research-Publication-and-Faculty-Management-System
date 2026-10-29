import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import LoadingScreen from './LoadingScreen'

/**
 * Guard for administrator-only routes.
 * - Not signed in  -> administrator portal login
 * - Signed in but not an admin -> 403 forbidden page
 */
export default function AdminRoute({ children }) {
  const { loading, isAuthenticated, user } = useAuth()
  const location = useLocation()

  if (loading) return <LoadingScreen message="Checking your session…" />
  if (!isAuthenticated) {
    return (
      <Navigate to="/login?role=admin" replace state={{ from: location }} />
    )
  }
  if (user?.role !== 'admin') {
    return <Navigate to="/forbidden" replace />
  }
  return children ?? <Outlet />
}
