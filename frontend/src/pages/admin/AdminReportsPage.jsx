import { useCallback, useEffect, useState } from 'react'
import LoadingScreen from '../../components/LoadingScreen'
import { getAdminSummary, listPublicationsAdmin } from '../../services/adminService'
import { getAdminError } from '../../utils/admin'

async function countByStatus(status) {
  try {
    const { data } = await listPublicationsAdmin({
      page: 1,
      page_size: 1,
      verification_status: status,
    })
    return data?.total ?? 0
  } catch {
    return null
  }
}

export default function AdminReportsPage() {
  const [summary, setSummary] = useState(null)
  const [counts, setCounts] = useState({ pending: 0, verified: 0, rejected: 0, needs_review: 0 })
  const [state, setState] = useState('loading')
  const [error, setError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  const load = useCallback(() => {
    setState('loading')
    setError('')
    Promise.all([
      getAdminSummary(),
      countByStatus('pending'),
      countByStatus('verified'),
      countByStatus('rejected'),
      countByStatus('needs_review'),
    ])
      .then(([summaryRes, pending, verified, rejected, needsReview]) => {
        setSummary(summaryRes.data)
        setCounts({
          pending: pending ?? 0,
          verified: verified ?? 0,
          rejected: rejected ?? 0,
          needs_review: needsReview ?? 0,
        })
        setState('ready')
      })
      .catch((err) => {
        setError(getAdminError(err))
        setState('error')
      })
  }, [])

  useEffect(() => {
    load()
  }, [load, reloadKey])

  if (state === 'loading') {
    return <LoadingScreen message="Loading analytics…" />
  }

  const cards = summary
    ? [
        { label: 'Total Faculty', value: summary.faculty_count },
        { label: 'Active Faculty', value: summary.active_faculty_count },
        { label: 'Total Publications', value: summary.publication_count },
        { label: 'Pending Verification', value: counts.pending },
        { label: 'Verified', value: counts.verified },
        { label: 'Rejected', value: counts.rejected },
        { label: 'Needs Review', value: counts.needs_review },
        { label: 'Academic Years', value: summary.academic_year_count },
      ]
    : []

  return (
    <div className="page admin-page">
      <div className="page__header">
        <div>
          <h1 className="page__title">Reports &amp; Analytics</h1>
          <p className="page__subtitle">
            Institutional publication and verification statistics.
          </p>
        </div>
        <div className="page__header-actions">
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => setReloadKey((key) => key + 1)}
          >
            Refresh
          </button>
        </div>
      </div>

      {state === 'error' ? (
        <p className="alert alert--danger" role="alert">
          {error}
        </p>
      ) : null}

      {summary ? (
        <>
          <section className="admin-stats" aria-label="Summary statistics">
            {cards.map((card) => (
              <div key={card.label} className="admin-stat">
                <span className="admin-stat__value">{card.value}</span>
                <span className="admin-stat__label">{card.label}</span>
              </div>
            ))}
          </section>

          <section className="panel">
            <h2 className="panel__title">Verification overview</h2>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th scope="col">Status</th>
                    <th scope="col">Publications</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>Pending</td>
                    <td>{counts.pending}</td>
                  </tr>
                  <tr>
                    <td>Verified</td>
                    <td>{counts.verified}</td>
                  </tr>
                  <tr>
                    <td>Rejected</td>
                    <td>{counts.rejected}</td>
                  </tr>
                  <tr>
                    <td>Needs review</td>
                    <td>{counts.needs_review}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p className="admin-form__hint">
              Current academic year: {summary.current_academic_year || 'Not set'}.
            </p>
          </section>
        </>
      ) : null}
    </div>
  )
}
