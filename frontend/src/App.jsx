import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import LoadingScreen from './components/LoadingScreen'
import ProtectedRoute from './components/ProtectedRoute'
import AdminRoute from './components/AdminRoute'
import { AuthProvider, useAuth } from './hooks/useAuth'
import AppLayout from './layouts/AppLayout'
import AdminLayout from './layouts/AdminLayout'
import AuthLayout from './layouts/AuthLayout'
import AddPublication from './pages/AddPublication'
import AdminAcademicYearsPage from './pages/admin/AdminAcademicYearsPage'
import AdminAccountsPage from './pages/admin/AdminAccountsPage'
import AdminApprovalsPage from './pages/admin/AdminApprovalsPage'
import AdminAuditLogsPage from './pages/admin/AdminAuditLogsPage'
import AdminDashboardPage from './pages/admin/AdminDashboardPage'
import AdminDepartmentsPage from './pages/admin/AdminDepartmentsPage'
import AdminEligibilityPage from './pages/admin/AdminEligibilityPage'
import AdminFacultyPage from './pages/admin/AdminFacultyPage'
import AdminProfilePage from './pages/admin/AdminProfilePage'
import AdminPublicationsPage from './pages/admin/AdminPublicationsPage'
import AdminRegisterPage from './pages/admin/AdminRegisterPage'
import AdminReportsPage from './pages/admin/AdminReportsPage'
import AdminResearchSearchPage from './pages/admin/AdminResearchSearchPage'
import AdminReviewDetailsPage from './pages/admin/AdminReviewDetailsPage'
import AdminReviewPage from './pages/admin/AdminReviewPage'
import AdminRulesPage from './pages/admin/AdminRulesPage'
import Dashboard from './pages/Dashboard'
import DocumentsPage from './pages/DocumentsPage'
import EditPublication from './pages/EditPublication'
import ExternalPublicationSearch from './pages/ExternalPublicationSearch'
import ChangePasswordPage from './pages/ChangePasswordPage'
import ForbiddenPage from './pages/ForbiddenPage'
import Login from './pages/Login'
import NotFound from './pages/NotFound'
import PointsPage from './pages/PointsPage'
import ProfilePage from './pages/ProfilePage'
import PublicationDetails from './pages/PublicationDetails'
import PublicationsPage from './pages/PublicationsPage'
import Register from './pages/Register'
import ReportsPage from './pages/ReportsPage'
import ResearchAssistantPage from './pages/ResearchAssistantPage'

function HomeRedirect() {
  const { loading, isAuthenticated, user } = useAuth()
  if (loading) return <LoadingScreen message="Checking your session…" />
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return (
    <Navigate
      to={user?.role === 'admin' ? '/admin/dashboard' : '/dashboard'}
      replace
    />
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<HomeRedirect />} />

          {/* Public / authentication pages */}
          <Route element={<AuthLayout />}>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/admin/register" element={<AdminRegisterPage />} />
          </Route>
          <Route
            path="/admin/login"
            element={<Navigate to="/login?role=admin" replace />}
          />

          {/* Faculty portal */}
          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/publications" element={<PublicationsPage />} />
              <Route path="/publications/new" element={<AddPublication />} />
              <Route
                path="/publications/search"
                element={<ExternalPublicationSearch />}
              />
              <Route
                path="/publications/:id/edit"
                element={<EditPublication />}
              />
              <Route
                path="/publications/:id"
                element={<PublicationDetails />}
              />
              <Route path="/profile" element={<ProfilePage />} />
              <Route path="/points" element={<PointsPage />} />
              <Route path="/documents" element={<DocumentsPage />} />
              <Route path="/reports" element={<ReportsPage />} />
              <Route
                path="/research-assistant"
                element={<ResearchAssistantPage />}
              />
            </Route>
            <Route
              path="/change-password"
              element={<ChangePasswordPage />}
            />
          </Route>

          {/* Administrator portal */}
          <Route element={<AdminRoute />}>
            <Route element={<AdminLayout />}>
              <Route path="/admin" element={<Navigate to="/admin/dashboard" replace />} />
              <Route path="/admin/dashboard" element={<AdminDashboardPage />} />
              <Route path="/admin/faculty" element={<AdminFacultyPage />} />
              <Route path="/admin/approvals" element={<AdminApprovalsPage />} />
              <Route path="/admin/review" element={<AdminReviewPage />} />
              <Route
                path="/admin/review/:id"
                element={<AdminReviewDetailsPage />}
              />
              <Route
                path="/admin/publications"
                element={<AdminPublicationsPage />}
              />
              <Route
                path="/admin/search"
                element={<AdminResearchSearchPage />}
              />
              <Route
                path="/admin/academic-years"
                element={<AdminAcademicYearsPage />}
              />
              <Route
                path="/admin/departments"
                element={<AdminDepartmentsPage />}
              />
              <Route path="/admin/rules" element={<AdminRulesPage />} />
              <Route
                path="/admin/eligibility"
                element={<AdminEligibilityPage />}
              />
              <Route path="/admin/reports" element={<AdminReportsPage />} />
              <Route path="/admin/audit" element={<AdminAuditLogsPage />} />
              <Route path="/admin/accounts" element={<AdminAccountsPage />} />
              <Route path="/admin/profile" element={<AdminProfilePage />} />
            </Route>
          </Route>

          <Route path="/forbidden" element={<ForbiddenPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
