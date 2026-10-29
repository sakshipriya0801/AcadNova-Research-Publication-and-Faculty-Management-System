import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import AcadNovaLogo from './AcadNovaLogo'

const ADMIN_NAV = [
  {
    heading: 'Overview',
    items: [{ to: '/admin/dashboard', label: 'Dashboard' }],
  },
  {
    heading: 'Faculty',
    items: [
      { to: '/admin/faculty', label: 'Faculty Management' },
      { to: '/admin/approvals', label: 'Registration Approvals' },
    ],
  },
  {
    heading: 'Publications',
    items: [
      { to: '/admin/publications', label: 'Publications' },
      { to: '/admin/search', label: 'Research Search' },
      { to: '/admin/review', label: 'Verification Queue' },
    ],
  },
  {
    heading: 'Insights',
    items: [{ to: '/admin/reports', label: 'Reports & Analytics' }],
  },
]

function linkClass({ isActive }) {
  return `sidebar__link${isActive ? ' sidebar__link--active' : ''}`
}

export default function AdminSidebar({ open, onClose, onNavigate }) {
  const { logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/admin/login', { replace: true })
  }

  return (
    <>
      <button
        type="button"
        className={`sidebar-overlay${open ? ' sidebar-overlay--visible' : ''}`}
        onClick={onClose}
        aria-label="Close navigation menu"
        tabIndex={open ? 0 : -1}
      />
      <aside
        className={`sidebar sidebar--admin${open ? ' sidebar--open' : ''}`}
        id="admin-sidebar"
        aria-label="Administrator navigation"
      >
        <div className="sidebar__brandmark">
          <AcadNovaLogo variant="full" size="md" showTagline tone="dark" />
        </div>

        <nav aria-label="Administrator navigation">
          {ADMIN_NAV.map((group) => (
            <div key={group.heading} className="sidebar__group">
              <p className="sidebar__heading">{group.heading}</p>
              <ul className="sidebar__list">
                {group.items.map((item) => (
                  <li key={item.to}>
                    <NavLink
                      to={item.to}
                      className={linkClass}
                      onClick={onNavigate}
                      end={item.to === '/admin/dashboard'}
                    >
                      {item.label}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>

        <div className="sidebar__footer">
          <button
            type="button"
            className="btn btn--ghost btn--block"
            onClick={handleLogout}
          >
            Log out
          </button>
        </div>
      </aside>
    </>
  )
}
