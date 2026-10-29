import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import AcadNovaLogo from './AcadNovaLogo'

const PAGE_TITLES = {
  '/dashboard': 'Dashboard',
  '/profile': 'My Profile',
  '/points': 'My Points',
  '/documents': 'Documents',
  '/reports': 'Reports',
  '/research-assistant': 'AI Research Assistant',
  '/admin/dashboard': 'Dashboard',
  '/admin/publications': 'Publication Management',
  '/admin/reports': 'Reports & Analytics',
  '/admin/audit': 'Verification History',
  '/admin/accounts': 'Admin Accounts',
  '/admin/profile': 'Profile & Settings',
}

function resolvePageTitle(pathname) {
  if (PAGE_TITLES[pathname]) return PAGE_TITLES[pathname]
  if (pathname.startsWith('/publications/search')) return 'Search & Import'
  if (pathname.startsWith('/publications/new')) return 'Add Publication'
  if (pathname.startsWith('/publications')) return 'Publications'
  if (pathname.startsWith('/admin/review')) return 'Review Queue'
  if (pathname.startsWith('/admin/search')) return 'Research Search'
  if (pathname.startsWith('/admin/academic-years')) return 'Academic Years'
  if (pathname.startsWith('/admin/departments')) return 'Departments'
  if (pathname.startsWith('/admin/faculty')) return 'Faculty'
  if (pathname.startsWith('/admin/approvals')) return 'Registration Approvals'
  if (pathname.startsWith('/admin/rules')) return 'Publication Rules'
  if (pathname.startsWith('/admin/eligibility')) return 'Eligibility'
  if (pathname.startsWith('/admin')) return 'Admin Console'
  return 'Dashboard'
}

const ROLE_LABELS = {
  faculty: 'Faculty',
  admin: 'Administrator',
}

export default function Navbar({
  onToggleSidebar,
  sidebarOpen,
  logoutTo = '/login',
  sidebarId = 'app-sidebar',
}) {
  const { user, profile, logout } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()

  const pageTitle = resolvePageTitle(location.pathname)
  const name = profile?.name || user?.email?.split('@')[0] || 'Account'
  const initials = name
    .split(/\s+/)
    .map((part) => part[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('')
    .toUpperCase()
  const roleLabel = ROLE_LABELS[user?.role] || 'Faculty'

  function handleLogout() {
    logout()
    navigate(logoutTo, { replace: true })
  }

  return (
    <header className="navbar">
      <div className="navbar__left">
        <button
          type="button"
          className="navbar__menu-btn"
          onClick={onToggleSidebar}
          aria-label="Open navigation menu"
          aria-controls={sidebarId}
          aria-expanded={Boolean(sidebarOpen)}
        >
          <span aria-hidden="true">☰</span>
        </button>
        <AcadNovaLogo variant="compact" size="sm" className="navbar__logo" />
        <span className="navbar__page-title">{pageTitle}</span>
      </div>

      <div className="navbar__right">
        <span className="navbar__user">
          <span className="navbar__avatar" aria-hidden="true">
            {initials}
          </span>
          <span className="navbar__user-meta">
            <span className="navbar__user-name">{name}</span>
            <span className="navbar__user-role">{roleLabel}</span>
          </span>
        </span>
        <button type="button" className="btn btn--ghost" onClick={handleLogout}>
          Log out
        </button>
      </div>
    </header>
  )
}
