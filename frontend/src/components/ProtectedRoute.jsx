import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import LoadingScreen from './LoadingScreen'

export default function ProtectedRoute({ children }) {
  const { loading, isAuthenticated, user } = useAuth()
  const location = useLocation()

  if (loading) return <LoadingScreen message="Checking your session…" />
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }
  // Administrators use the separate admin console.
  if (user?.role === 'admin') {
    return <Navigate to="/admin/dashboard" replace />
  }
  // Faculty issued a temporary password must change it before anything else.
  if (
    user?.role === 'faculty' &&
    user?.must_change_password &&
    location.pathname !== '/change-password'
  ) {
    return <Navigate to="/change-password" replace />
  }
  return children ?? <Outlet />
}
