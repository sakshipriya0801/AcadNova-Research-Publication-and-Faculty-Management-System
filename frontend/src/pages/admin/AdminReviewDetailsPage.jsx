import { useCallback, useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import ConfirmDialog from '../../components/ConfirmDialog'
import LoadingScreen from '../../components/LoadingScreen'
import PublicationDocuments from '../../components/PublicationDocuments'
import RejectPublicationDialog from '../../components/RejectPublicationDialog'
import VerificationHistory from '../../components/VerificationHistory'
import { useAuth } from '../../hooks/useAuth'
import { listFaculty } from '../../services/adminService'
import {
  listPublicationsAdmin,
  verifyPublication,
} from '../../services/verificationService'
import {
  academicYearFromDate,
  formatDate,
  sourceLabel,
  statusMeta,
  typeLabel,
} from '../../utils/publication'
import {
  ACTION_META,
  availableActions,
  findPublicationById,
  getVerificationError,
} from '../../utils/verification'

function Row({ label, children }) {
  if (children === null || children === undefined || children === '') return null
  return (
    <div className="detail-list__row">
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  )
}

export default function AdminReviewDetailsPage() {
  const { id } = useParams()
  const { user } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [publication, setPublication] = useState(null)
  const [status, setStatus] = useState('loading')
  const [errorMessage, setErrorMessage] = useState('')
  const [notice, setNotice] = useState('')
  const [actionBusy, setActionBusy] = useState('')
  const [actionError, setActionError] = useState('')
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [rejectOpen, setRejectOpen] = useState(false)
  const [historyKey, setHistoryKey] = useState(0)
  const [facultyName, setFacultyName] = useState('')

  const isAdmin = user?.role === 'admin'

  useEffect(() => {
    if (!isAdmin || !location.state?.notice) return undefined
    setNotice(location.state.notice)
    return undefined
  }, [isAdmin, location.state])

  const load = useCallback(() => {
    if (!isAdmin) return
    setStatus('loading')
    findPublicationById(
      (page, pageSize) =>
        listPublicationsAdmin({
          page,
          page_size: pageSize,
          sort_by: 'created_at',
          sort_order: 'desc',
        }).then((response) => response.data),
      id,
    )
      .then((found) => {
        if (!found) {
          setErrorMessage('Publication not found.')
          setStatus('error')
          return
        }
        setPublication(found)
        setErrorMessage('')
        setStatus('ready')
      })
      .catch((error) => {
        setErrorMessage(
          getVerificationError(error, 'Unable to load this publication.'),
        )
        setStatus('error')
      })
  }, [id, isAdmin])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (!isAdmin || !publication?.faculty_id) return undefined
    let cancelled = false
    listFaculty({ page: 1, page_size: 100 })
      .then((response) => {
        if (cancelled) return
        const profile = (response.data?.items || []).find(
          (item) => item.faculty_id === publication.faculty_id,
        )
        setFacultyName(profile ? profile.name : '')
      })
      .catch(() => {
        setFacultyName('')
      })
    return () => {
      cancelled = true
    }
  }, [isAdmin, publication])

  function handleVerificationResponse(response) {
    const updated = response.data?.publication
    const action = response.data?.verification?.action
    if (updated) setPublication(updated)
    setNotice(
      action && ACTION_META[action] ? ACTION_META[action].notice : 'Verification updated.',
    )
    setActionError('')
    setConfirmOpen(false)
    setRejectOpen(false)
    setHistoryKey((key) => key + 1)
  }

  function handleVerify() {
    if (actionBusy) return
    setActionBusy('verify')
    setActionError('')
    verifyPublication(id, 'verify', null, null)
      .then(handleVerificationResponse)
      .catch((error) => {
        setActionError(
          getVerificationError(
            error,
            'Something went wrong while updating verification.',
          ),
        )
      })
      .finally(() => {
        setActionBusy('')
      })
  }

  function handleReject(reason) {
    if (actionBusy) return
    setActionBusy('reject')
    setActionError('')
    verifyPublication(id, 'reject', reason, null)
      .then(handleVerificationResponse)
      .catch((error) => {
        setActionError(
          getVerificationError(
            error,
            'Something went wrong while updating verification.',
          ),
        )
      })
      .finally(() => {
        setActionBusy('')
      })
  }

  function handleBack() {
    navigate('/admin/review', notice ? { state: { notice } } : undefined)
  }

  if (!isAdmin) {
    return (
      <div className="page">
        <div className="page__header">
          <div>
            <h1 className="page__title">Publication Review</h1>
          </div>
        </div>
        <div className="empty-state">
          <p className="empty-state__title">You don&apos;t have permission</p>
          <p className="empty-state__text">
            Publication review is available to administrators only.
          </p>
          <Link className="btn btn--primary" to="/dashboard">
            Back to Dashboard
          </Link>
        </div>
      </div>
    )
  }

  if (status === 'loading') {
    return <LoadingScreen message="Loading publication for review…" />
  }

  if (status === 'error') {
    return (
      <div className="page">
        <div className="page__header">
          <div>
            <Link className="pub-details__back" to="/admin/review">
              ← Back to Publication Review
            </Link>
            <h1 className="page__title">Publication Review</h1>
          </div>
        </div>
        <div className="empty-state">
          <p className="empty-state__title">Publication not found</p>
          <p className="empty-state__text">{errorMessage}</p>
          <div className="review-actions">
            <button type="button" className="btn btn--ghost" onClick={load}>
              Try Again
            </button>
            <Link className="btn btn--primary" to="/admin/review">
              Back to Publication Review
            </Link>
          </div>
        </div>
      </div>
    )
  }

  const meta = statusMeta(publication.verification_status)
  const verified = publication.verification_status === 'verified'
  const actions = availableActions(publication.verification_status)
  const yearLabel = academicYearFromDate(publication.publication_date)
  const authors = publication.authors || []
  const indexing = publication.indexing || []
  const keywords = publication.keywords || []

  return (
    <div className="page">
      <div className="page__header">
        <div>
          <Link className="pub-details__back" to="/admin/review">
            ← Back to Publication Review
          </Link>
          <h1 className="page__title">{publication.title}</h1>
          <p className="page__subtitle">
            {typeLabel(publication.publication_type)}
            {publication.sub_type ? ` · ${publication.sub_type}` : ''}
            {formatDate(publication.publication_date)
              ? ` · ${formatDate(publication.publication_date)}`
              : ''}
          </p>
        </div>
        <div className="review-actions">
          {actions.includes('verify') ? (
            <button
              type="button"
              className="btn btn--primary"
              onClick={() => {
                setActionError('')
                setConfirmOpen(true)
              }}
              disabled={Boolean(actionBusy)}
            >
              {actionBusy === 'verify'
                ? ACTION_META.verify.busy
                : ACTION_META.verify.button}
            </button>
          ) : null}
          {actions.includes('reject') ? (
            <button
              type="button"
              className="btn btn--ghost btn--danger-outline"
              onClick={() => {
                setActionError('')
                setRejectOpen(true)
              }}
              disabled={Boolean(actionBusy)}
            >
              {actionBusy === 'reject'
                ? ACTION_META.reject.busy
                : ACTION_META.reject.button}
            </button>
          ) : null}
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

      {actionError && !confirmOpen && !rejectOpen ? (
        <div className="alert alert--danger" role="alert">
          {actionError}
        </div>
      ) : null}

      <div className="panel-grid">
        <section className="panel" aria-labelledby="review-status-heading">
          <h2 className="panel__title" id="review-status-heading">
            Review status
          </h2>
          <dl className="detail-list">
            <Row label="Verification status">
              <span
                className={`status-pill status-pill--${publication.verification_status}`}
              >
                <span aria-hidden="true">{meta.symbol}</span> {meta.label}
              </span>
            </Row>
            <Row label="Points awarded">
              {verified ? publication.points_awarded ?? 0 : '—'}
            </Row>
            <Row label="Submitted by">{facultyName}</Row>
            <Row label="Source">{sourceLabel(publication.source)}</Row>
            <Row label="Academic year">{yearLabel || '—'}</Row>
          </dl>
          <p className="panel__note">
            Points are recalculated by the backend points engine after a
            verification decision.
          </p>
        </section>

        <section className="panel" aria-labelledby="review-authors-heading">
          <h2 className="panel__title" id="review-authors-heading">
            Authors
          </h2>
          {authors.length === 0 ? (
            <p className="panel__empty">No author information.</p>
          ) : (
            <ol className="pub-details__authors">
              {authors.map((author, index) => (
                <li key={`${author}-${index}`}>
                  {author}
                  {publication.faculty_author_position === index + 1 ? (
                    <span className="pub-details__tag">Owner</span>
                  ) : null}
                  {publication.is_corresponding_author &&
                  publication.faculty_author_position === index + 1 ? (
                    <span className="pub-details__tag">Corresponding</span>
                  ) : null}
                </li>
              ))}
            </ol>
          )}
          {publication.author_count ? (
            <p className="panel__empty">Total authors: {publication.author_count}</p>
          ) : null}
        </section>
      </div>

      <section className="panel" aria-labelledby="review-details-heading">
        <h2 className="panel__title" id="review-details-heading">
          Publication details
        </h2>
        <dl className="detail-list detail-list--grid">
          <Row label="Journal">{publication.journal_name}</Row>
          <Row label="Conference">{publication.conference_name}</Row>
          <Row label="Publisher">{publication.publisher}</Row>
          <Row label="DOI">{publication.doi}</Row>
          <Row label="Volume">{publication.volume}</Row>
          <Row label="Issue">{publication.issue}</Row>
          <Row label="Pages">{publication.pages}</Row>
          <Row label="ISSN">{publication.issn}</Row>
          <Row label="ISBN">{publication.isbn}</Row>
          <Row label="Publication year">{publication.publication_year}</Row>
          <Row label="Collaboration type">{publication.collaboration_type}</Row>
          <Row label="External institution">{publication.external_institution}</Row>
          <Row label="Indexing">
            {indexing.length > 0 ? indexing.join(', ') : null}
          </Row>
          <Row label="Keywords">{keywords.length > 0 ? keywords.join(', ') : null}</Row>
          <Row label="Created">{formatDate(publication.created_at)}</Row>
        </dl>
      </section>

      {publication.abstract ? (
        <section className="panel" aria-labelledby="review-abstract-heading">
          <h2 className="panel__title" id="review-abstract-heading">
            Abstract
          </h2>
          <p className="pub-details__abstract">{publication.abstract}</p>
        </section>
      ) : null}

      {publication.source_url || publication.pdf_url ? (
        <section className="panel" aria-labelledby="review-links-heading">
          <h2 className="panel__title" id="review-links-heading">
            Links
          </h2>
          <ul className="pub-details__links">
            {publication.source_url ? (
              <li>
                <a
                  href={publication.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Publication URL
                </a>
              </li>
            ) : null}
            {publication.pdf_url ? (
              <li>
                <a href={publication.pdf_url} target="_blank" rel="noopener noreferrer">
                  PDF
                </a>
              </li>
            ) : null}
          </ul>
        </section>
      ) : null}

      <PublicationDocuments
        publicationId={id}
        heading="Documents & Evidence"
        showCount
        canManage={false}
        emptyMessage="No documents attached to this publication."
      />

      <VerificationHistory
        key={historyKey}
        publicationId={id}
        variant="admin"
        heading="Verification history"
        emptyMessage="No verification activity yet."
      />

      <ConfirmDialog
        open={confirmOpen}
        title="Verify publication"
        message="Verify this publication? The backend will recalculate points for the faculty member."
        confirmLabel={ACTION_META.verify.confirm}
        confirmVariant="primary"
        busy={actionBusy === 'verify'}
        error={actionError}
        onConfirm={handleVerify}
        onCancel={() => {
          if (!actionBusy) setConfirmOpen(false)
        }}
      />

      <RejectPublicationDialog
        open={rejectOpen}
        busy={actionBusy === 'reject'}
        error={actionError}
        onConfirm={handleReject}
        onCancel={() => {
          if (!actionBusy) setRejectOpen(false)
        }}
      />
    </div>
  )
}
