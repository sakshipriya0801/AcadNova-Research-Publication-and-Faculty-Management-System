import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import Navbar from '../components/Navbar'
import Sidebar from '../components/Sidebar'

export default function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()

  useEffect(() => {
    setSidebarOpen(false)
  }, [location.pathname])

  return (
    <div className="app-shell">
      <Navbar
        onToggleSidebar={() => setSidebarOpen((open) => !open)}
        sidebarOpen={sidebarOpen}
      />
      <div className="app-shell__body">
        <Sidebar
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
