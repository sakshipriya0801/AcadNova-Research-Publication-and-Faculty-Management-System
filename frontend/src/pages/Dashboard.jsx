import { useCallback, useEffect, useState } from 'react'
import LoadingScreen from '../components/LoadingScreen'
import StatCard from '../components/StatCard'
import { useAuth } from '../hooks/useAuth'
import { getPointsSummary } from '../services/pointsService'
import { listPublications } from '../services/publicationService'
import { getErrorMessage } from '../utils/errors'
import { academicYearFromDate, sourceLabel, statusMeta } from '../utils/publication'

export default function Dashboard() {
  const { user, profile } = useAuth()
  const [state, setState] = useState({ status: 'loading' })
  const [reloadKey, setReloadKey] = useState(0)

  const load = useCallback(async () => {
    setState({ status: 'loading' })
    try {
      const [all, verified, pending] = await Promise.all([
        listPublications({ page: 1, page_size: 6 }),
        listPublications({ page: 1, page_size: 1, verification_status: 'verified' }),
        listPublications({ page: 1, page_size: 1, verification_status: 'pending' }),
      ])

      const recent = all.data.items
      const yearPublication = recent.find((item) => item.academic_year_id) || null

      let points = null
      if (yearPublication?.academic_year_id) {
        try {
          const response = await getPointsSummary(yearPublication.academic_year_id)
          points = response.data
        } catch {
          points = null
        }
      }

      setState({
        status: 'ready',
        total: all.data.total,
        verified: verified.data.total,
        pending: pending.data.total,
        recent,
        points,
        yearLabel: academicYearFromDate(yearPublication?.publication_date),
      })
    } catch (error) {
      setState({ status: 'error', message: getErrorMessage(error) })
    }
  }, [])

  useEffect(() => {
    load()
  }, [load, reloadKey])

  const displayName = profile?.name || user?.email?.split('@')[0] || 'there'

  if (state.status === 'loading') {
    return <LoadingScreen message="Loading your dashboard…" />
  }

  if (state.status === 'error') {
    return (
      <div className="page">
        <div className="empty-state">
          <p className="empty-state__title">Unable to load the dashboard</p>
          <p className="empty-state__text">{state.message}</p>
          <button
            type="button"
            className="btn btn--primary"
            onClick={() => setReloadKey((key) => key + 1)}
          >
            Try again
          </button>
        </div>
      </div>
    )
  }

  const { total, verified, pending, recent, points, yearLabel } = state
  const eligibility = points?.eligibility || null
  const otherStatuses = Math.max(0, total - verified - pending)

  const pointsValue = points
    ? points.total_points
    : total === 0
      ? 0
      : 'N/A'

  const eligibilityValue = eligibility
    ? eligibility.eligible
      ? 'Eligible'
      : 'Pending'
    : 'N/A'

  const eligibilityHint = eligibility
    ? eligibility.reason ||
      (eligibility.remaining_points > 0
        ? `${eligibility.remaining_points} points remaining`
        : 'Requirement reached')
    : 'Not available yet'

  return (
    <div className="page">
      <div className="page__header">
        <div>
          <h1 className="page__title">Welcome back, {displayName}</h1>
          <p className="page__subtitle">
            {yearLabel ? `Academic year ${yearLabel}` : 'Your performance overview'}
          </p>
        </div>
      </div>

      <section className="stat-grid" aria-label="Key statistics">
        <StatCard label="Total Publications" value={total} />
        <StatCard label="Verified Publications" value={verified} />
        <StatCard label="Pending Publications" value={pending} />
        <StatCard
          label="Current Points"
          value={pointsValue}
          hint={yearLabel ? `Academic year ${yearLabel}` : undefined}
        />
        <StatCard label="Eligibility Status" value={eligibilityValue} hint={eligibilityHint} />
      </section>

      <div className="panel-grid">
        <section className="panel" aria-labelledby="eligibility-heading">
          <h2 className="panel__title" id="eligibility-heading">
            Eligibility
          </h2>
          {eligibility ? (
            <dl className="detail-list">
              <div className="detail-list__row">
                <dt>Status</dt>
                <dd>{eligibility.eligible ? 'Eligible' : 'Pending'}</dd>
              </div>
              <div className="detail-list__row">
                <dt>Designation</dt>
                <dd>{eligibility.designation || profile?.designation || 'N/A'}</dd>
              </div>
              <div className="detail-list__row">
                <dt>Required points</dt>
                <dd>{eligibility.required_points ?? 'N/A'}</dd>
              </div>
              <div className="detail-list__row">
                <dt>Earned points</dt>
                <dd>{eligibility.total_points}</dd>
              </div>
              <div className="detail-list__row">
                <dt>Remaining</dt>
                <dd>{eligibility.remaining_points ?? 'N/A'}</dd>
              </div>
              {eligibility.reason ? (
                <p className="detail-list__note">{eligibility.reason}</p>
              ) : null}
            </dl>
          ) : (
            <p className="panel__empty">
              Eligibility information is not available yet. It appears once your
              points are calculated for an academic year.
            </p>
          )}
        </section>

        <section className="panel" aria-labelledby="status-heading">
          <h2 className="panel__title" id="status-heading">
            Publication Status
          </h2>
          <dl className="detail-list">
            <div className="detail-list__row">
              <dt>Verified</dt>
              <dd>{verified}</dd>
            </div>
            <div className="detail-list__row">
              <dt>Pending</dt>
              <dd>{pending}</dd>
            </div>
            <div className="detail-list__row">
              <dt>Other</dt>
              <dd>{otherStatuses}</dd>
            </div>
            <div className="detail-list__row">
              <dt>Total</dt>
              <dd>{total}</dd>
            </div>
          </dl>
        </section>
      </div>

      <section className="panel" aria-labelledby="recent-heading">
        <div className="panel__header">
          <h2 className="panel__title" id="recent-heading">
            Recent Publications
          </h2>
        </div>
        {recent.length === 0 ? (
          <p className="panel__empty">No publications yet.</p>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">Title</th>
                  <th scope="col">Year</th>
                  <th scope="col">Source</th>
                  <th scope="col">Verification</th>
                  <th scope="col">Points</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((publication) => (
                  <tr key={publication.publication_id}>
                    <td className="table__title">{publication.title}</td>
                    <td>
                      {publication.publication_year ||
                        String(publication.publication_date || '').slice(0, 4) ||
                        'N/A'}
                    </td>
                    <td>{sourceLabel(publication.source)}</td>
                    <td>
                      <span
                        className={`status-pill status-pill--${publication.verification_status}`}
                      >
                        {statusMeta(publication.verification_status).label}
                      </span>
                    </td>
                    <td>{publication.points_awarded ?? 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
