import { Outlet } from 'react-router-dom'
import AcadNovaLogo from '../components/AcadNovaLogo'

const HIGHLIGHTS = [
  'Track publications, evidence and verification',
  'Rule-based performance points & eligibility',
  'Grounded AI research assistant',
  'Administrator verification & analytics',
]

export default function AuthLayout() {
  return (
    <div className="auth-shell">
      <aside className="auth-brand">
        <header className="auth-brand__top">
          <AcadNovaLogo variant="full" size="lg" showTagline tone="dark" />
        </header>

        <div className="auth-brand__body">
          <h1 className="auth-brand__headline">
            A new era of research, impact and academic careers.
          </h1>
          <p className="auth-brand__text">
            AcadNova is a unified platform for institutional research output,
            publication verification, performance analytics and AI-assisted
            insights.
          </p>
          <ul className="auth-brand__highlights">
            {HIGHLIGHTS.map((item) => (
              <li key={item}>
                <span className="auth-brand__check" aria-hidden="true">
                  ✓
                </span>
                {item}
              </li>
            ))}
          </ul>
        </div>

        <footer className="auth-brand__footer">
          AcadNova — A New Era of Research.
        </footer>
      </aside>

      <main className="auth-main" id="main-content">
        <div className="auth-card">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
