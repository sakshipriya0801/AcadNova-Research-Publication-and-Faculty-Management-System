import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard' },
  {
    label: 'Publications',
    group: 'publications',
    children: [
      { to: '/publications', label: 'My Publications' },
      { to: '/publications/search', label: 'Search & Import' },
      { to: '/publications/new', label: 'Add Publication' },
    ],
  },
  { to: '/profile', label: 'My Profile' },
  { to: '/points', label: 'Points & Eligibility' },
  { to: '/documents', label: 'Documents' },
  { to: '/research-assistant', label: 'AI Research Assistant' },
  { to: '/reports', label: 'Reports' },
]

function linkClass({ isActive }) {
  return `sidebar__link${isActive ? ' sidebar__link--active' : ''}`
}

function childClass(pathname, to) {
  let active = false
  if (to === '/publications') {
    active =
      pathname === '/publications' ||
      (pathname.startsWith('/publications/') &&
        pathname !== '/publications/search' &&
        pathname !== '/publications/new')
  } else {
    active = pathname === to
  }
  return `sidebar__link sidebar__link--sub${active ? ' sidebar__link--active' : ''}`
}

export default function Sidebar({ open, onClose, onNavigate }) {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
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
        className={`sidebar${open ? ' sidebar--open' : ''}`}
        id="app-sidebar"
        aria-label="Sidebar"
      >
        <nav aria-label="Main navigation">
          <p className="sidebar__heading" id="sidebar-menu-heading">
            Menu
          </p>
          <ul className="sidebar__list" aria-labelledby="sidebar-menu-heading">
            {NAV_ITEMS.map((item) =>
              item.children ? (
                <li key={item.label} className="sidebar__group">
                  <p
                    className={`sidebar__group-heading${
                      location.pathname.startsWith(`/${item.group}`)
                        ? ' sidebar__group-heading--active'
                        : ''
                    }`}
                  >
                    {item.label}
                  </p>
                  <ul className="sidebar__sublist">
                    {item.children.map((child) => (
                      <li key={child.to}>
                        <NavLink
                          to={child.to}
                          className={childClass(location.pathname, child.to)}
                          onClick={onNavigate}
                        >
                          {child.label}
                        </NavLink>
                      </li>
                    ))}
                  </ul>
                </li>
              ) : (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    className={linkClass}
                    onClick={onNavigate}
                  >
                    {item.label}
                  </NavLink>
                </li>
              ),
            )}
          </ul>
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
