import { useCallback, useEffect, useState } from 'react'
import LoadingScreen from '../components/LoadingScreen'
import PointsBreakdown from '../components/PointsBreakdown'
import StatCard from '../components/StatCard'
import { listAcademicYears } from '../services/academicYearService'
import {
  getPointsBreakdown,
  getPointsSummary,
  recalculatePoints,
} from '../services/pointsService'
import {
  academicYearOptions,
  eligibilityStatus,
  formatDesignation,
  getPointsError,
  preferredAcademicYearId,
  progressPercent,
} from '../utils/points'

const STATUS_SYMBOLS = {
  eligible: '✓',
  'not-yet': '⏳',
  unknown: '•',
}

export default function PointsPage() {
  const [years, setYears] = useState([])
  const [yearsStatus, setYearsStatus] = useState('loading')
  const [yearsError, setYearsError] = useState('')
  const [yearsReloadKey, setYearsReloadKey] = useState(0)
  const [yearId, setYearId] = useState(null)
  const [summary, setSummary] = useState(null)
  const [breakdown, setBreakdown] = useState([])
  const [dataStatus, setDataStatus] = useState('loading')
  const [dataError, setDataError] = useState('')
  const [dataReloadKey, setDataReloadKey] = useState(0)
  const [notice, setNotice] = useState('')
  const [actionError, setActionError] = useState('')
  const [recalcBusy, setRecalcBusy] = useState(false)

  useEffect(() => {
    let cancelled = false
    setYearsStatus('loading')
    listAcademicYears()
      .then((response) => {
        if (cancelled) return
        const list = Array.isArray(response.data) ? response.data : []
        setYears(list)
        setYearsError('')
        setYearsStatus(list.length === 0 ? 'empty' : 'ready')
        setYearId((current) => {
          const valid = current && list.some((y) => y.academic_year_id === current)
          return valid ? current : preferredAcademicYearId(list)
        })
      })
      .catch((error) => {
        if (cancelled) return
        setYearsError(getPointsError(error))
        setYearsStatus('error')
      })
    return () => {
      cancelled = true
    }
  }, [yearsReloadKey])

  useEffect(() => {
    if (!yearId) return undefined
    let cancelled = false
    setDataStatus('loading')
    Promise.all([getPointsSummary(yearId), getPointsBreakdown(yearId)])
      .then(([summaryResponse, breakdownResponse]) => {
        if (cancelled) return
        setSummary(summaryResponse.data)
        setBreakdown(
          Array.isArray(breakdownResponse.data) ? breakdownResponse.data : [],
        )
        setDataError('')
        setDataStatus('ready')
      })
      .catch((error) => {
        if (cancelled) return
        setDataError(getPointsError(error))
        setDataStatus('error')
      })
    return () => {
      cancelled = true
    }
  }, [yearId, dataReloadKey])

  const handleRecalculate = useCallback(() => {
    if (recalcBusy || !yearId) return
    setRecalcBusy(true)
    setActionError('')
    setNotice('')
    recalculatePoints(yearId)
      .then((response) => {
        setSummary(response.data)
        setNotice('Points recalculated.')
        setDataReloadKey((key) => key + 1)
      })
      .catch((error) => {
        setActionError(
          getPointsError(error, 'Something went wrong while recalculating points.'),
        )
      })
      .finally(() => {
        setRecalcBusy(false)
      })
  }, [recalcBusy, yearId])

  if (yearsStatus === 'loading') {
    return <LoadingScreen message="Loading points…" />
  }

  if (yearsStatus === 'error') {
    return (
      <div className="page">
        <div className="page__header">
          <div>
            <h1 className="page__title">Points &amp; Eligibility</h1>
          </div>
        </div>
        <div className="empty-state">
          <p className="empty-state__title">Unable to load academic years</p>
          <p className="empty-state__text">{yearsError}</p>
          <button
            type="button"
            className="btn btn--primary"
            onClick={() => setYearsReloadKey((key) => key + 1)}
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  if (yearsStatus === 'empty') {
    return (
      <div className="page">
        <div className="page__header">
          <div>
            <h1 className="page__title">Points &amp; Eligibility</h1>
            <p className="page__subtitle">
              Points awarded by the institutional rules engine.
            </p>
          </div>
        </div>
        <div className="empty-state">
          <p className="empty-state__title">No academic year is available.</p>
          <p className="empty-state__text">
            Academic years are configured by the administration. Points cannot
            be displayed until an academic year exists.
          </p>
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => setYearsReloadKey((key) => key + 1)}
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  if (dataStatus === 'loading' || !yearId) {
    return <LoadingScreen message="Loading points…" />
  }

  const selectedYear = years.find((year) => year.academic_year_id === yearId)
  const yearName = selectedYear ? selectedYear.name : ''
  const eligibility = summary ? summary.eligibility : null
  const status = eligibilityStatus(eligibility)
  const percent = summary
    ? progressPercent(summary.total_points, eligibility?.required_points)
    : null
  const designation = formatDesignation(eligibility?.designation)
  const required = eligibility?.required_points ?? null

  return (
    <div className="page points-page">
      <div className="page__header">
        <div>
          <h1 className="page__title">Points &amp; Eligibility</h1>
          <p className="page__subtitle">
            Points awarded by the institutional rules engine for the selected
            academic year.
          </p>
        </div>
        <div className="points-page__actions">
          <div className="field points-page__year">
            <label className="field__label" htmlFor="points-academic-year">
              Academic year
            </label>
            <select
              id="points-academic-year"
              className="field__input"
              value={yearId || ''}
              onChange={(event) => {
                setYearId(event.target.value)
                setNotice('')
                setActionError('')
              }}
            >
              {academicYearOptions(years).map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <button
            type="button"
            className="btn btn--primary points-page__recalc"
            onClick={handleRecalculate}
            disabled={recalcBusy}
          >
            {recalcBusy ? 'Recalculating…' : 'Recalculate Points'}
          </button>
        </div>
      </div>

      {notice ? (
        <div className="alert alert--success pub-alert" role="status">
          <span>{notice}</span>
          <button
            type="button"
            className="pub-alert__close"
            onClick={() => setNotice('')}
            aria-label="Dismiss message"
          >
            ✕
          </button>
        </div>
      ) : null}

      {actionError ? (
        <div className="alert alert--danger" role="alert">
          {actionError}
        </div>
      ) : null}

      {dataStatus === 'error' ? (
        <div className="alert alert--danger" role="alert">
          {dataError}{' '}
          <button
            type="button"
            className="btn btn--ghost btn--inline"
            onClick={() => setDataReloadKey((key) => key + 1)}
          >
            Try Again
          </button>
        </div>
      ) : null}

      {summary && dataStatus !== 'error' ? (
        <>
          <div className="points-cards">
            <StatCard
              label="Total Points"
              value={summary.total_points}
              hint={`Awarded in ${yearName}`}
            />
            <StatCard
              label="Required Points"
              value={required ?? '—'}
              hint={
                designation
                  ? `Minimum for ${designation}`
                  : 'No threshold configured'
              }
            />
            <StatCard
              label="Points Remaining"
              value={eligibility?.remaining_points ?? '—'}
              hint={
                required !== null
                  ? `Of ${required} required points`
                  : 'No threshold configured'
              }
            />
            <article className="stat-card">
              <p className="stat-card__label">Eligibility Status</p>
              <p className="stat-card__value">
                <span className={`points-status points-status--${status.kind}`}>
                  <span aria-hidden="true">{STATUS_SYMBOLS[status.kind]}</span>{' '}
                  {status.label}
                </span>
              </p>
              <p className="stat-card__hint">{status.message}</p>
            </article>
          </div>

          <section className="panel" aria-labelledby="points-progress-heading">
            <h2 className="panel__title" id="points-progress-heading">
              Progress toward eligibility
            </h2>
            {required !== null && percent !== null ? (
              <div className="points-progress">
                <p className="points-progress__label">
                  {summary.total_points} / {required} points
                </p>
                <div
                  className="points-progress__track"
                  role="progressbar"
                  aria-valuenow={summary.total_points}
                  aria-valuemin={0}
                  aria-valuemax={required}
                  aria-label={`Points progress: ${summary.total_points} of ${required}`}
                >
                  <div
                    className={`points-progress__bar points-progress__bar--${status.kind}`}
                    style={{ width: `${percent}%` }}
                  />
                </div>
                <p className="points-progress__caption">{status.message}</p>
              </div>
            ) : (
              <div className="points-progress points-progress--unknown">
                <p className="points-progress__caption">
                  {eligibility?.reason ||
                    'No points data available for your designation.'}
                </p>
              </div>
            )}
          </section>

          <section className="panel points-info" aria-labelledby="points-info-heading">
            <h2 className="panel__title" id="points-info-heading">
              How points are awarded
            </h2>
            <ul className="points-info__list">
              <li>
                Only verified publications contribute to awarded points.
              </li>
              <li>
                Pending and rejected publications do not contribute until their
                verification state permits it.
              </li>
              <li>
                Points are determined by institutional rules configured in the
                system.
              </li>
            </ul>
          </section>

          <PointsBreakdown
            status={dataStatus === 'error' ? 'error' : dataStatus}
            errorMessage={dataError}
            categoryPoints={summary.category_points}
            items={breakdown}
            yearName={yearName}
            onRetry={() => setDataReloadKey((key) => key + 1)}
          />

          <section
            className="panel"
            aria-labelledby="points-eligibility-heading"
          >
            <h2 className="panel__title" id="points-eligibility-heading">
              How eligibility is determined
            </h2>
            <dl className="detail-list">
              {designation ? (
                <div className="detail-list__row">
                  <dt>Your designation</dt>
                  <dd>{designation}</dd>
                </div>
              ) : null}
              <div className="detail-list__row">
                <dt>Required points</dt>
                <dd>{required ?? 'Not configured'}</dd>
              </div>
              <div className="detail-list__row">
                <dt>Total points ({yearName})</dt>
                <dd>{summary.total_points}</dd>
              </div>
              <div className="detail-list__row">
                <dt>Remaining points</dt>
                <dd>{eligibility?.remaining_points ?? '—'}</dd>
              </div>
              <div className="detail-list__row">
                <dt>Status</dt>
                <dd>{status.label}</dd>
              </div>
              {eligibility?.reason ? (
                <div className="detail-list__row">
                  <dt>Details</dt>
                  <dd>{eligibility.reason}</dd>
                </div>
              ) : null}
            </dl>
            <p className="panel__note">
              Your verified publications are matched against the configured
              institutional rules (shown per publication above), and the total
              is compared with the minimum required points for your designation.
            </p>
          </section>
        </>
      ) : null}
    </div>
  )
}
