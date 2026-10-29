import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  getPointsBreakdown,
  getPointsSummary,
} from '../../services/pointsService'
import {
  EMPTY_REPORT_MESSAGE,
  csvFilename,
  downloadCsv,
  getReportError,
} from '../../utils/reports'
import {
  categoryEntries,
  eligibilityStatus,
  formatDesignation,
} from '../../utils/points'

const CSV_HEADERS = ['Section', 'Category / Rule', 'Publications', 'Points']

function ruleLabel(item) {
  return item.rule_name || item.rule_code || item.reason || 'No matching rule'
}

export default function PointsReport({ yearId, yearName, facultyName }) {
  const [summary, setSummary] = useState(null)
  const [breakdown, setBreakdown] = useState([])
  const [status, setStatus] = useState('loading')
  const [errorMessage, setErrorMessage] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    if (!yearId) return undefined
    let cancelled = false
    setStatus('loading')
    Promise.all([getPointsSummary(yearId), getPointsBreakdown(yearId)])
      .then(([summaryResponse, breakdownResponse]) => {
        if (cancelled) return
        setSummary(summaryResponse.data)
        setBreakdown(
          Array.isArray(breakdownResponse.data) ? breakdownResponse.data : [],
        )
        setErrorMessage('')
        setStatus('ready')
      })
      .catch((error) => {
        if (cancelled) return
        setErrorMessage(getReportError(error))
        setStatus('error')
      })
    return () => {
      cancelled = true
    }
  }, [yearId, reloadKey])

  const categories = useMemo(
    () => categoryEntries(summary ? summary.category_points : null),
    [summary],
  )

  const ruleGroups = useMemo(() => {
    const groups = new Map()
    for (const item of breakdown) {
      const label = ruleLabel(item)
      const existing = groups.get(label) || { label, publications: 0, points: 0 }
      existing.publications += 1
      existing.points += Number(item.points) || 0
      groups.set(label, existing)
    }
    return Array.from(groups.values())
  }, [breakdown])

  const zeroPointItems = useMemo(
    () => breakdown.filter((item) => (Number(item.points) || 0) === 0),
    [breakdown],
  )

  const handleExport = useCallback(() => {
    const rows = []
    for (const category of categories) {
      rows.push(['Category', category.label, '', category.points])
    }
    for (const group of ruleGroups) {
      rows.push(['Rule', group.label, group.publications, group.points])
    }
    rows.push(['Total', '', breakdown.length, summary ? summary.total_points : 0])
    downloadCsv(csvFilename('annual-points-report', yearName), CSV_HEADERS, rows)
  }, [categories, ruleGroups, breakdown, summary, yearName])

  if (status === 'loading') {
    return (
      <section className="panel report-section" aria-label="Annual points report">
        <div className="panel__head report-section__head">
          <h2 className="panel__title">
            Annual Points Report<span className="report-section__year"> · {yearName}</span>
          </h2>
        </div>
        <div className="report-loading" role="status">
          Loading report data…
        </div>
      </section>
    )
  }

  if (status === 'error') {
    return (
      <section className="panel report-section" aria-label="Annual points report">
        <div className="panel__head report-section__head">
          <h2 className="panel__title">
            Annual Points Report<span className="report-section__year"> · {yearName}</span>
          </h2>
        </div>
        <div className="alert alert--danger" role="alert">
          {errorMessage}{' '}
          <button
            type="button"
            className="btn btn--ghost btn--inline"
            onClick={() => setReloadKey((key) => key + 1)}
          >
            Try Again
          </button>
        </div>
      </section>
    )
  }

  const eligibility = summary ? summary.eligibility : null
  const eligibilityState = eligibilityStatus(eligibility)
  const designation =
    formatDesignation(eligibility?.designation) || 'Not set'

  return (
    <section className="panel report-section" aria-label="Annual points report">
      <div className="panel__head report-section__head">
        <h2 className="panel__title">
          Annual Points Report<span className="report-section__year"> · {yearName}</span>
        </h2>
        <button
          type="button"
          className="btn btn--ghost no-print"
          onClick={handleExport}
          disabled={!summary}
        >
          Export CSV
        </button>
      </div>

      <dl className="detail-list report-meta">
        <div className="detail-list__row">
          <dt>Academic Year</dt>
          <dd>{yearName}</dd>
        </div>
        <div className="detail-list__row">
          <dt>Faculty Name</dt>
          <dd>{facultyName || '—'}</dd>
        </div>
        <div className="detail-list__row">
          <dt>Designation</dt>
          <dd>{designation}</dd>
        </div>
        <div className="detail-list__row">
          <dt>Total Points</dt>
          <dd>{summary ? summary.total_points : '—'}</dd>
        </div>
        <div className="detail-list__row">
          <dt>Required Points</dt>
          <dd>{eligibility?.required_points ?? 'Not configured'}</dd>
        </div>
        <div className="detail-list__row">
          <dt>Eligibility Status</dt>
          <dd>
            {eligibilityState.label}
            <span className="report-meta__hint">{eligibilityState.message}</span>
          </dd>
        </div>
      </dl>

      <div className="report-table-group">
        <h3 className="report-table-group__title">Points by category</h3>
        <div className="table-wrap">
          <table className="table report-table">
            <caption className="visually-hidden">
              Points by category for {yearName}
            </caption>
            <thead>
              <tr>
                <th scope="col">Category</th>
                <th scope="col" className="report-table__points-col">Points</th>
              </tr>
            </thead>
            <tbody>
              {categories.map((category) => (
                <tr key={category.key}>
                  <td>{category.label}</td>
                  <td className="report-table__points">{category.points}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <th scope="row">Total</th>
                <td className="report-table__points">
                  {summary ? summary.total_points : 0}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      <div className="report-table-group">
        <h3 className="report-table-group__title">Points by rule</h3>
        {ruleGroups.length === 0 ? (
          <div className="empty-state">
            <p className="empty-state__title">{EMPTY_REPORT_MESSAGE}</p>
            <p className="empty-state__text">
              Verified publications are matched against the institutional rules
              for this academic year.
            </p>
          </div>
        ) : (
          <>
            <div className="table-wrap">
              <table className="table report-table">
                <caption className="visually-hidden">
                  Points by rule for {yearName}
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Category / Rule</th>
                    <th scope="col" className="report-table__count-col">Publications</th>
                    <th scope="col" className="report-table__points-col">Points</th>
                  </tr>
                </thead>
                <tbody>
                  {ruleGroups.map((group) => (
                    <tr key={group.label}>
                      <td>{group.label}</td>
                      <td className="report-table__count">{group.publications}</td>
                      <td className="report-table__points">{group.points}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr>
                    <th scope="row">Total</th>
                    <td className="report-table__count">{breakdown.length}</td>
                    <td className="report-table__points">
                      {summary ? summary.total_points : 0}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
            {zeroPointItems.length > 0 ? (
              <div className="report-note">
                <p className="report-note__title">
                  Verified publications without awarded points
                </p>
                <ul className="report-note__list">
                  {zeroPointItems.map((item) => (
                    <li key={item.publication_id}>
                      <span className="report-note__name">{item.title}</span>
                      <span className="report-note__reason">
                        {item.reason || 'No reason provided'}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </>
        )}
      </div>

      <p className="panel__note">
        Values are produced by the institutional points engine. Categories and
        rules are shown exactly as awarded by the backend for verified
        publications in {yearName}.
      </p>
    </section>
  )
}
