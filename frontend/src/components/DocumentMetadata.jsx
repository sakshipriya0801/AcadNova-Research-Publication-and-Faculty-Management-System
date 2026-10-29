import { useEffect, useRef, useState } from 'react'
import { getDocumentMetadata } from '../services/pdfProcessingService'
import { getDocumentError, pluralPages } from '../utils/documents'

const METADATA_FIELDS = [
  { key: 'title', label: 'Title' },
  { key: 'author', label: 'Author' },
  { key: 'subject', label: 'Subject' },
  { key: 'keywords', label: 'Keywords' },
  { key: 'creator', label: 'Creator' },
  { key: 'producer', label: 'Producer' },
  { key: 'creation_date', label: 'Creation Date' },
  { key: 'modification_date', label: 'Modification Date' },
]

export default function DocumentMetadata({ publicationId, document, onClose }) {
  const dialogRef = useRef(null)
  const closeRef = useRef(null)
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')
  const [metadata, setMetadata] = useState(null)

  useEffect(() => {
    if (!document) return undefined
    let cancelled = false
    setStatus('loading')
    setError('')
    setMetadata(null)
    getDocumentMetadata(publicationId, document.id)
      .then((response) => {
        if (cancelled) return
        setMetadata(response.data)
        setStatus('ready')
      })
      .catch((loadError) => {
        if (cancelled) return
        setError(getDocumentError(loadError))
        setStatus('error')
      })
    return () => {
      cancelled = true
    }
  }, [publicationId, document])

  useEffect(() => {
    closeRef.current?.focus()

    function onKeyDown(event) {
      if (event.key === 'Escape') {
        event.stopPropagation()
        onClose()
        return
      }
      if (event.key === 'Tab' && dialogRef.current) {
        const focusable = dialogRef.current.querySelectorAll(
          'button:not([disabled]), a[href]',
        )
        if (focusable.length === 0) return
        const first = focusable[0]
        const last = focusable[focusable.length - 1]
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault()
          last.focus()
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault()
          first.focus()
        }
      }
    }

    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [onClose])

  if (!document) return null

  return (
    <div className="dialog-backdrop" onMouseDown={onClose}>
      <div
        className="dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="doc-metadata-title"
        ref={dialogRef}
        tabIndex={-1}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <h2 className="dialog__title" id="doc-metadata-title">
          PDF metadata
        </h2>
        <p className="doc-viewer__filename">{document.original_filename}</p>

        {status === 'loading' ? (
          <p className="doc-viewer__state" role="status">
            Loading metadata…
          </p>
        ) : null}

        {status === 'error' ? (
          <p className="alert alert--danger" role="alert">
            {error}
          </p>
        ) : null}

        {status === 'ready' && metadata ? (
          <>
            <dl className="detail-list">
              {METADATA_FIELDS.map((field) => (
                <div className="detail-list__row" key={field.key}>
                  <dt>{field.label}</dt>
                  <dd>{metadata[field.key] || 'Not available'}</dd>
                </div>
              ))}
              <div className="detail-list__row">
                <dt>Page Count</dt>
                <dd>{pluralPages(metadata.page_count) || 'Not available'}</dd>
              </div>
            </dl>
            <p className="panel__note">
              PDF metadata is extracted from the uploaded file and is not considered
              institutional verification.
            </p>
          </>
        ) : null}

        <div className="dialog__actions">
          <button
            type="button"
            className="btn btn--ghost"
            onClick={onClose}
            ref={closeRef}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
