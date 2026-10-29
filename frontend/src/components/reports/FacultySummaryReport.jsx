import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import StatCard from '../StatCard'
import { listPublications } from '../../services/publicationService'
import { getPointsSummary } from '../../services/pointsService'
import {
  csvFilename,
  downloadCsv,
  formatDepartment,
  getReportError,
} from '../../utils/reports'
import {
  eligibilityStatus,
  formatDesignation,
} from '../../utils/points'

const STATUS_SYMBOLS = {
  eligible: '✓',
  'not-yet': '⏳',
  unknown: '•',
}

const CSV_HEADERS = ['Metric', 'Value']

async function countPublications(yearId, verificationStatus) {
  const params = { page: 1, page_size: 1, academic_year_id: yearId }
  if (verificationStatus) params.verification_status = verificationStatus
  const response = await listPublications(params)
  const payload = response.data || {}
  return typeof payload.total === 'number' ? payload.total : 0
}

export default function FacultySummaryReport({ yearId, yearName, profile, departments }) {
  const [counts, setCounts] = useState(null)
  const [summary, setSummary] = useState(null)
  const [status, setStatus] = useState('loading')
  const [errorMessage, setErrorMessage] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    if (!yearId) return undefined
    let cancelled = false
    setStatus('loading')
    Promise.all([
      countPublications(yearId, null),
      countPublications(yearId, 'verified'),
      countPublications(yearId, 'pending'),
      countPublications(yearId, 'rejected'),
      getPointsSummary(yearId),
    ])
      .then(([total, verified, pending, rejected, summaryResponse]) => {
        if (cancelled) return
        setCounts({ total, verified, pending, rejected })
        setSummary(summaryResponse.data)
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

  const designation = formatDesignation(profile?.designation) || 'Not set'
  const department = formatDepartment(departments, profile?.department_id)
  const facultyName = profile?.name || '—'
  const eligibility = summary ? summary.eligibility : null
  const eligibilityState = eligibilityStatus(eligibility)

  const handleExport = useCallback(() => {
    const rows = [
      ['Faculty', facultyName],
      ['Designation', designation],
      ['Department', department],
      ['Academic Year', yearName],
      [
        'Total Publications',
        counts ? counts.total : '',
      ],
      ['Verified Publications', counts ? counts.verified : ''],
      ['Pending Publications', counts ? counts.pending : ''],
      ['Rejected Publications', counts ? counts.rejected : ''],
      ['Total Points', summary ? summary.total_points : ''],
      [
        'Required Points',
        eligibility?.required_points ?? 'Not configured',
      ],
      ['Eligibility Status', eligibilityState.label],
    ]
    downloadCsv(csvFilename('faculty-research-summary', yearName), CSV_HEADERS, rows)
  }, [facultyName, designation, department, yearName, counts, summary, eligibility, eligibilityState])

  if (status === 'loading') {
    return (
      <section className="panel report-section" aria-label="Faculty research summary">
        <div className="panel__head report-section__head">
          <h2 className="panel__title">
            Faculty Research Summary
            <span className="report-section__year"> · {yearName}</span>
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
      <section className="panel report-section" aria-label="Faculty research summary">
        <div className="panel__head report-section__head">
          <h2 className="panel__title">
            Faculty Research Summary
            <span className="report-section__year"> · {yearName}</span>
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

  return (
    <section className="panel report-section" aria-label="Faculty research summary">
      <div className="panel__head report-section__head">
        <h2 className="panel__title">
          Faculty Research Summary
          <span className="report-section__year"> · {yearName}</span>
        </h2>
        <button
          type="button"
          className="btn btn--ghost no-print"
          onClick={handleExport}
        >
          Export CSV
        </button>
      </div>

      <dl className="detail-list report-meta">
        <div className="detail-list__row">
          <dt>Faculty</dt>
          <dd>{facultyName}</dd>
        </div>
        <div className="detail-list__row">
          <dt>Designation</dt>
          <dd>{designation}</dd>
        </div>
        <div className="detail-list__row">
          <dt>Department</dt>
          <dd>{department}</dd>
        </div>
        <div className="detail-list__row">
          <dt>Academic Year</dt>
          <dd>{yearName}</dd>
        </div>
      </dl>

      <div className="report-cards">
        <StatCard
          label="Total Publications"
          value={counts ? counts.total : '—'}
          hint={`In ${yearName}`}
        />
        <StatCard
          label="Verified Publications"
          value={counts ? counts.verified : '—'}
          hint="Confirmed by review"
        />
        <StatCard
          label="Pending Publications"
          value={counts ? counts.pending : '—'}
          hint="Awaiting review"
        />
        <StatCard
          label="Rejected Publications"
          value={counts ? counts.rejected : '—'}
          hint="Not accepted"
        />
        <StatCard
          label="Total Points"
          value={summary ? summary.total_points : '—'}
          hint={`Awarded in ${yearName}`}
        />
        <article className="stat-card">
          <p className="stat-card__label">Eligibility Status</p>
          <p className="stat-card__value">
            <span className={`points-status points-status--${eligibilityState.kind}`}>
              <span aria-hidden="true">{STATUS_SYMBOLS[eligibilityState.kind]}</span>{' '}
              {eligibilityState.label}
            </span>
          </p>
          <p className="stat-card__hint">{eligibilityState.message}</p>
        </article>
      </div>

      <div className="report-section__footer no-print">
        <Link className="btn btn--ghost" to="/publications">
          View my publications
        </Link>
      </div>
    </section>
  )
}
