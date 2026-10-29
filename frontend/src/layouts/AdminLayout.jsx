import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import Navbar from '../components/Navbar'
import AdminSidebar from '../components/AdminSidebar'

export default function AdminLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()

  useEffect(() => {
    setSidebarOpen(false)
  }, [location.pathname])

  return (
    <div className="app-shell app-shell--admin">
      <Navbar
        onToggleSidebar={() => setSidebarOpen((open) => !open)}
        sidebarOpen={sidebarOpen}
        logoutTo="/admin/login"
        sidebarId="admin-sidebar"
      />
      <div className="app-shell__body">
        <AdminSidebar
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          onNavigate={() => setSidebarOpen(false)}
        />
        <main className="app-shell__main" id="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
