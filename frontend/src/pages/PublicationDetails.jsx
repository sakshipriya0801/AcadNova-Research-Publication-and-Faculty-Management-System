import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import ConfirmDialog from '../components/ConfirmDialog'
import LoadingScreen from '../components/LoadingScreen'
import PublicationDocuments from '../components/PublicationDocuments'
import VerificationHistory from '../components/VerificationHistory'
import { deletePublication, getPublication } from '../services/publicationService'
import { getPublicationError } from '../utils/errors'
import {
  academicYearFromDate,
  formatDate,
  sourceLabel,
  statusMeta,
  typeLabel,
} from '../utils/publication'
import { latestRejection } from '../utils/verification'

function Row({ label, children }) {
  if (children === null || children === undefined || children === '') return null
  return (
    <div className="detail-list__row">
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  )
}

export default function PublicationDetails() {
  const { id } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const [publication, setPublication] = useState(null)
  const [status, setStatus] = useState('loading')
  const [errorMessage, setErrorMessage] = useState('')
  const [notice, setNotice] = useState(location.state?.notice || '')
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deleteBusy, setDeleteBusy] = useState(false)
  const [deleteError, setDeleteError] = useState('')
  const [verificationRecords, setVerificationRecords] = useState([])

  useEffect(() => {
    let cancelled = false
    setStatus('loading')
    getPublication(id)
      .then((response) => {
        if (cancelled) return
        setPublication(response.data)
        setStatus('ready')
      })
      .catch((error) => {
        if (cancelled) return
        setErrorMessage(getPublicationError(error))
        setStatus('error')
      })
    return () => {
      cancelled = true
    }
  }, [id])

  function handleDelete() {
    if (deleteBusy) return undefined
    setDeleteBusy(true)
    setDeleteError('')
    return deletePublication(id)
      .then(() => {
        navigate('/publications', {
          replace: true,
          state: { notice: 'Publication deleted.' },
        })
      })
      .catch((error) => {
        setDeleteError(getPublicationError(error))
      })
      .finally(() => {
        setDeleteBusy(false)
      })
  }

  if (status === 'loading') {
    return <LoadingScreen message="Loading publication…" />
  }

  if (status === 'error') {
    return (
      <div className="page">
        <div className="page__header">
          <h1 className="page__title">Publication</h1>
          <Link className="btn btn--ghost" to="/publications">
            Back to Publications
          </Link>
        </div>
        <div className="empty-state">
          <p className="empty-state__title">Publication not found</p>
          <p className="empty-state__text">{errorMessage}</p>
          <Link className="btn btn--primary" to="/publications">
            Back to Publications
          </Link>
        </div>
      </div>
    )
  }

  const meta = statusMeta(publication.verification_status)
  const verified = publication.verification_status === 'verified'
  const rejection = latestRejection(verificationRecords)
  const yearLabel = academicYearFromDate(publication.publication_date)
  const authors = publication.authors || []
  const indexing = publication.indexing || []
  const keywords = publication.keywords || []

  return (
    <div className="page">
      <div className="page__header">
        <div>
          <Link className="pub-details__back" to="/publications">
            ← Back to Publications
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
        <div className="pub-details__actions">
          <Link className="btn btn--ghost" to={`/publications/${id}/edit`}>
            Edit Publication
          </Link>
          <button
            type="button"
            className="btn btn--ghost btn--danger-outline"
            onClick={() => {
              setDeleteError('')
              setConfirmOpen(true)
            }}
          >
            Delete Publication
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

      <div className="panel-grid">
        <section className="panel" aria-labelledby="status-heading">
          <h2 className="panel__title" id="status-heading">
            Verification &amp; points
          </h2>
          <dl className="detail-list">
            <Row label="Verification status">
              <span className={`status-pill status-pill--${publication.verification_status}`}>
                <span aria-hidden="true">{meta.symbol}</span> {meta.label}
              </span>
            </Row>
            <Row label="Points awarded">
              {verified ? publication.points_awarded ?? 0 : '—'}
            </Row>
            {publication.verification_status === 'rejected' && rejection?.reason ? (
              <Row label="Rejection reason">{rejection.reason}</Row>
            ) : null}
            <Row label="Source">{sourceLabel(publication.source)}</Row>
            <Row label="Academic year">{yearLabel || '—'}</Row>
          </dl>
          <p className="panel__note">
            Points are calculated by the backend points engine after verification.
            An external source does not mean a publication is verified.
          </p>
        </section>

        <section className="panel" aria-labelledby="authors-heading">
          <h2 className="panel__title" id="authors-heading">
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
                    <span className="pub-details__tag">You</span>
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

      <section className="panel" aria-labelledby="details-heading">
        <h2 className="panel__title" id="details-heading">
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
        <section className="panel" aria-labelledby="abstract-heading">
          <h2 className="panel__title" id="abstract-heading">
            Abstract
          </h2>
          <p className="pub-details__abstract">{publication.abstract}</p>
        </section>
      ) : null}

      {publication.source_url || publication.pdf_url ? (
        <section className="panel" aria-labelledby="links-heading">
          <h2 className="panel__title" id="links-heading">
            Links
          </h2>
          <ul className="pub-details__links">
            {publication.source_url ? (
              <li>
                <a href={publication.source_url} target="_blank" rel="noopener noreferrer">
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
        emptyMessage="No documents uploaded yet."
      />

      <VerificationHistory
        publicationId={id}
        variant="faculty"
        heading="Verification history"
        emptyMessage="No verification activity yet."
        onLoaded={setVerificationRecords}
      />

      <ConfirmDialog
        open={confirmOpen}
        title="Delete publication"
        message="Are you sure you want to delete this publication? This cannot be undone."
        confirmLabel="Delete"
        busy={deleteBusy}
        error={deleteError}
        onConfirm={handleDelete}
        onCancel={() => {
          if (!deleteBusy) setConfirmOpen(false)
        }}
      />
    </div>
  )
}
