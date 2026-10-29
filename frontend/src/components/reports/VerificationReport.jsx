import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { listPublications } from '../../services/publicationService'
import { getVerificationHistory } from '../../services/verificationService'
import {
  EMPTY_REPORT_MESSAGE,
  csvFilename,
  downloadCsv,
  getReportError,
  mapWithConcurrency,
} from '../../utils/reports'
import { statusMeta } from '../../utils/publication'
import {
  formatRecordDate,
  recordActionLabel,
  recordActionSymbol,
} from '../../utils/verification'

const MAX_PAGES = 10
const CSV_HEADERS = [
  'Publication',
  'Current Status',
  'Verification Action',
  'Date/Time',
  'Reason',
  'Notes',
]

async function fetchYearPublications(yearId) {
  const items = []
  let page = 1
  let totalPages = 1
  let total = 0
  while (page <= totalPages && page <= MAX_PAGES) {
    const response = await listPublications({
      academic_year_id: yearId,
      page,
      page_size: 100,
      sort_by: 'publication_date',
      sort_order: 'desc',
    })
    const payload = response.data || {}
    total = payload.total || 0
    items.push(...(Array.isArray(payload.items) ? payload.items : []))
    totalPages = Math.max(payload.total_pages || 1, 1)
    page += 1
  }
  return { items, total }
}

export default function VerificationReport({ yearId, yearName }) {
  const [rows, setRows] = useState([])
  const [status, setStatus] = useState('loading')
  const [phase, setPhase] = useState('publications')
  const [errorMessage, setErrorMessage] = useState('')
  const [capped, setCapped] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    if (!yearId) return undefined
    let cancelled = false
    setStatus('loading')
    setPhase('publications')

    fetchYearPublications(yearId)
      .then(async ({ items, total }) => {
        if (cancelled) return
        setCapped(total > items.length)
        if (items.length === 0) {
          setRows([])
          setErrorMessage('')
          setStatus('ready')
          return
        }
        setPhase('history')
        const historyPairs = await mapWithConcurrency(items, 6, async (publication) => {
          const response = await getVerificationHistory(publication.publication_id)
          return [
            publication.publication_id,
            Array.isArray(response.data) ? response.data : [],
          ]
        })
        if (cancelled) return
        const historyById = Object.fromEntries(historyPairs)
        const built = []
        for (const publication of items) {
          const records = historyById[publication.publication_id] || []
          for (const record of records) {
            built.push({
              key:
                record.id ||
                `${publication.publication_id}-${record.created_at || ''}`,
              publicationId: publication.publication_id,
              title: publication.title,
              status: publication.verification_status,
              action: recordActionLabel(record),
              actionSymbol: recordActionSymbol(record),
              date: formatRecordDate(record.created_at),
              sortKey: String(record.created_at || ''),
              reason: record.reason || '—',
              notes: record.notes || '—',
            })
          }
        }
        built.sort((a, b) => {
          if (b.sortKey === a.sortKey) return 0
          return b.sortKey > a.sortKey ? 1 : -1
        })
        setRows(built)
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

  const sortedRows = useMemo(() => rows, [rows])

  const handleExport = useCallback(() => {
    const exportRows = sortedRows.map((row) => [
      row.title,
      statusMeta(row.status).label,
      row.action,
      row.date,
      row.reason,
      row.notes,
    ])
    downloadCsv(
      csvFilename('verification-report', yearName),
      CSV_HEADERS,
      exportRows,
    )
  }, [sortedRows, yearName])

  const loadingText =
    phase === 'history'
      ? 'Loading verification history…'
      : 'Loading report data…'

  return (
    <section className="panel report-section" aria-label="Verification report">
      <div className="panel__head report-section__head">
        <h2 className="panel__title">
          Verification Report<span className="report-section__year"> · {yearName}</span>
        </h2>
        <button
          type="button"
          className="btn btn--ghost no-print"
          onClick={handleExport}
          disabled={sortedRows.length === 0}
        >
          Export CSV
        </button>
      </div>

      {status === 'loading' ? (
        <div className="report-loading" role="status">
          {loadingText}
        </div>
      ) : null}

      {status === 'error' ? (
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
      ) : null}

      {status === 'ready' && sortedRows.length === 0 ? (
        <div className="empty-state">
          <p className="empty-state__title">{EMPTY_REPORT_MESSAGE}</p>
          <p className="empty-state__text">
            Verification activity for this academic year will appear here once
            publications are reviewed.
          </p>
        </div>
      ) : null}

      {status === 'ready' && sortedRows.length > 0 ? (
        <>
          <div className="table-wrap">
            <table className="table report-table">
              <caption className="visually-hidden">
                Verification report for {yearName}
              </caption>
              <thead>
                <tr>
                  <th scope="col">Publication</th>
                  <th scope="col">Current Status</th>
                  <th scope="col">Verification Action</th>
                  <th scope="col">Date/Time</th>
                  <th scope="col">Reason</th>
                  <th scope="col">Notes</th>
                </tr>
              </thead>
              <tbody>
                {sortedRows.map((row) => {
                  const meta = statusMeta(row.status)
                  return (
                    <tr key={row.key}>
                      <td className="table__title">
                        <Link
                          className="report-table__link"
                          to={`/publications/${row.publicationId}`}
                        >
                          {row.title}
                        </Link>
                      </td>
                      <td>
                        <span className={`status-pill status-pill--${row.status}`}>
                          <span aria-hidden="true">{meta.symbol}</span> {meta.label}
                        </span>
                      </td>
                      <td>
                        <span aria-hidden="true">{row.actionSymbol}</span>{' '}
                        {row.action}
                      </td>
                      <td className="report-table__wrap">{row.date}</td>
                      <td className="report-table__wrap">{row.reason}</td>
                      <td className="report-table__wrap">{row.notes}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <p className="report-count">
            {sortedRows.length} verification record
            {sortedRows.length === 1 ? '' : 's'} · newest first
          </p>
          {capped ? (
            <p className="panel__note">
              Only the most recent publications for this academic year were
              included.
            </p>
          ) : null}
        </>
      ) : null}
    </section>
  )
}
