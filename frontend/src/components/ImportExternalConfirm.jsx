import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listPublications } from '../services/publicationService'
import { importExternalPublication } from '../services/externalPublicationService'
import { listAcademicYears } from '../services/academicYearService'
import { statusMeta } from '../utils/publication'
import {
  buildImportPayload,
  getAuthorMatchFactors,
  getExternalImportError,
  isAuthorConfirmationError,
  isDuplicateImportError,
  requiresAuthorMatch,
  resultTitle,
  sameDoi,
  sourceLabel,
} from '../utils/external'

export default function ImportExternalConfirm({ result, source, onCancel, onFinished }) {
  const navigate = useNavigate()
  const dialogRef = useRef(null)
  const [phase, setPhase] = useState('confirm')
  const [authorConfirmed, setAuthorConfirmed] = useState(false)
  const [message, setMessage] = useState('')
  const [matchFactors, setMatchFactors] = useState('')
  const [publication, setPublication] = useState(null)
  const [existingId, setExistingId] = useState(null)
  const [isExistingLoading, setIsExistingLoading] = useState(false)
  const [academicYears, setAcademicYears] = useState([])
  const [academicYearId, setAcademicYearId] = useState('')

  const busy = phase === 'importing'

  useEffect(() => {
    dialogRef.current?.focus()
  }, [phase])

  useEffect(() => {
    let cancelled = false
    listAcademicYears()
      .then((response) => {
        if (cancelled) return
        const years = response.data || []
        setAcademicYears(years)
        const current = years.find((year) => year.is_current)
        setAcademicYearId(
          current
            ? current.academic_year_id
            : years.length === 1
              ? years[0].academic_year_id
              : '',
        )
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    function onKeyDown(event) {
      if (event.key === 'Escape' && !busy) {
        event.stopPropagation()
        onCancel()
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [busy, onCancel])

  function runImport(confirmedFlag) {
    if (busy) return
    setPhase('importing')
    setMessage('')
    importExternalPublication(
      buildImportPayload(result, {
        source,
        authorMatchConfirmed: confirmedFlag,
        academicYearId,
      }),
    )
      .then((response) => {
        setPublication(response.data)
        setPhase('success')
      })
      .catch((error) => {
        if (isAuthorConfirmationError(error)) {
          setMatchFactors(getAuthorMatchFactors(error))
          setMessage(getExternalImportError(error, source))
          setAuthorConfirmed(false)
          setPhase('author')
          return
        }
        if (isDuplicateImportError(error)) {
          setPhase('duplicate')
          findExisting()
          return
        }
        setMessage(getExternalImportError(error, source))
        setPhase('error')
      })
  }

  function findExisting() {
    const doi = result?.doi
    if (!doi) return
    setIsExistingLoading(true)
    listPublications({
      search: doi,
      page: 1,
      page_size: 10,
      sort_by: 'publication_date',
      sort_order: 'desc',
    })
      .then((response) => {
        const match = (response.data.items || []).find((item) =>
          sameDoi(item.doi, doi),
        )
        if (match) setExistingId(match.publication_id)
      })
      .catch(() => undefined)
      .finally(() => setIsExistingLoading(false))
  }

  function viewPublication() {
    if (!publication) return
    onFinished('Publication imported successfully.')
    navigate(`/publications/${publication.publication_id}`)
  }

  function backToSearch() {
    onFinished(phase === 'success' ? 'Publication imported successfully.' : '')
  }

  const matchLine = requiresAuthorMatch(source)
    ? 'The backend verifies your author match during import.'
    : 'Author matching does not apply to this source.'

  return (
    <div
      className="dialog-backdrop"
      onMouseDown={busy ? undefined : onCancel}
    >
      <div
        className="dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="import-dialog-title"
        aria-describedby="import-dialog-message"
        ref={dialogRef}
        tabIndex={-1}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <h2 className="dialog__title" id="import-dialog-title">
          Import Publication?
        </h2>

        {phase === 'confirm' ? (
          <>
            <dl className="detail-list">
              <div className="detail-list__row">
                <dt>Title</dt>
                <dd>{resultTitle(result)}</dd>
              </div>
              <div className="detail-list__row">
                <dt>Source</dt>
                <dd>{sourceLabel(source)}</dd>
              </div>
              <div className="detail-list__row">
                <dt>Author match</dt>
                <dd>{matchLine}</dd>
              </div>
            </dl>
            <div className="field">
              <label className="field__label" htmlFor="import-academic-year">
                Academic year
              </label>
              <select
                id="import-academic-year"
                className="field__input"
                value={academicYearId}
                onChange={(event) => setAcademicYearId(event.target.value)}
              >
                {academicYears.length === 0 ? (
                  <option value="">No academic years configured</option>
                ) : (
                  <>
                    <option value="">Derive from publication date</option>
                    {academicYears.map((year) => (
                      <option key={year.academic_year_id} value={year.academic_year_id}>
                        {year.name}
                        {year.is_current ? ' (current)' : ''}
                      </option>
                    ))}
                  </>
                )}
              </select>
            </div>
            <p className="dialog__message" id="import-dialog-message">
              This publication will be added as Pending and must be verified before
              points are awarded.
            </p>
            <div className="dialog__actions">
              <button type="button" className="btn btn--ghost" onClick={onCancel}>
                Cancel
              </button>
              <button
                type="button"
                className="btn btn--primary"
                onClick={() => runImport(false)}
              >
                Import
              </button>
            </div>
          </>
        ) : null}

        {phase === 'importing' ? (
          <p className="dialog__message" id="import-dialog-message" role="status">
            Importing from {sourceLabel(source)}…
          </p>
        ) : null}

        {phase === 'author' ? (
          <>
            <p className="alert alert--danger" role="alert" id="import-dialog-message">
              <strong>Author match: needs confirmation.</strong>
              {matchFactors ? ` Backend matching factors: ${matchFactors}.` : ''}
              {' '}
              {message}
            </p>
            <label className="ext-confirm__check" htmlFor="author-confirm-check">
              <input
                id="author-confirm-check"
                type="checkbox"
                checked={authorConfirmed}
                onChange={(event) => setAuthorConfirmed(event.target.checked)}
              />
              <span>I confirm that I am an author of this publication.</span>
            </label>
            <div className="dialog__actions">
              <button type="button" className="btn btn--ghost" onClick={onCancel}>
                Cancel
              </button>
              <button
                type="button"
                className="btn btn--primary"
                onClick={() => runImport(true)}
                disabled={!authorConfirmed}
              >
                Import
              </button>
            </div>
          </>
        ) : null}

        {phase === 'success' && publication ? (
          <>
            <div className="ext-success" id="import-dialog-message">
              <p className="ext-success__line" role="status">
                Publication imported successfully.
              </p>
              <dl className="detail-list">
                <div className="detail-list__row">
                  <dt>Verification status</dt>
                  <dd>
                    <span
                      className={`status-pill status-pill--${publication.verification_status}`}
                    >
                      <span aria-hidden="true">
                        {statusMeta(publication.verification_status).symbol}
                      </span>{' '}
                      {statusMeta(publication.verification_status).label}
                    </span>
                  </dd>
                </div>
                <div className="detail-list__row">
                  <dt>Points</dt>
                  <dd>
                    {publication.points_awarded ?? 0} — awarded after verification and
                    backend calculation
                  </dd>
                </div>
                {requiresAuthorMatch(source) ? (
                  <div className="detail-list__row">
                    <dt>Author match</dt>
                    <dd>
                      {authorConfirmed
                        ? 'Confirmed by you'
                        : 'High confidence — accepted by the backend'}
                    </dd>
                  </div>
                ) : null}
              </dl>
            </div>
            <div className="dialog__actions">
              <button type="button" className="btn btn--ghost" onClick={backToSearch}>
                Back to Search
              </button>
              <button
                type="button"
                className="btn btn--primary"
                onClick={viewPublication}
              >
                View Publication
              </button>
            </div>
          </>
        ) : null}

        {phase === 'duplicate' ? (
          <>
            <p className="alert alert--warning" id="import-dialog-message" role="alert">
              This publication is already in your publication list.
            </p>
            <div className="dialog__actions">
              <button type="button" className="btn btn--ghost" onClick={backToSearch}>
                Back to Search
              </button>
              {existingId ? (
                <button
                  type="button"
                  className="btn btn--primary"
                  onClick={() => {
                    onFinished('')
                    navigate(`/publications/${existingId}`)
                  }}
                >
                  View Existing Publication
                </button>
              ) : (
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={backToSearch}
                  disabled={isExistingLoading}
                >
                  {isExistingLoading ? 'Looking up…' : 'Close'}
                </button>
              )}
            </div>
          </>
        ) : null}

        {phase === 'error' ? (
          <>
            <p className="alert alert--danger" id="import-dialog-message" role="alert">
              {message}
            </p>
            <div className="dialog__actions">
              <button type="button" className="btn btn--ghost" onClick={backToSearch}>
                Back to Search
              </button>
              <button
                type="button"
                className="btn btn--primary"
                onClick={() => runImport(false)}
              >
                Try again
              </button>
            </div>
          </>
        ) : null}
      </div>
    </div>
  )
}
