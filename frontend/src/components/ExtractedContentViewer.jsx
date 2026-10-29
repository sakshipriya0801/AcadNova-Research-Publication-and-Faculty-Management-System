import { useEffect, useRef, useState } from 'react'
import { getExtractedContent } from '../services/pdfProcessingService'
import { formatTextLength, getContentError, pluralPages } from '../utils/documents'

export default function ExtractedContentViewer({ publicationId, document, onClose }) {
  const dialogRef = useRef(null)
  const closeRef = useRef(null)
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')
  const [content, setContent] = useState(null)
  const [pageIndex, setPageIndex] = useState(0)

  useEffect(() => {
    if (!document) return undefined
    let cancelled = false
    setStatus('loading')
    setError('')
    setContent(null)
    setPageIndex(0)
    getExtractedContent(publicationId, document.id)
      .then((response) => {
        if (cancelled) return
        setContent(response.data)
        setStatus('ready')
      })
      .catch((loadError) => {
        if (cancelled) return
        setError(getContentError(loadError))
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

  const pages = content?.pages || []
  const current = pages[pageIndex]
  const totalPages = content?.page_count || pages.length || 0
  const hasAnyText = pages.some((page) => (page.text || '').trim())

  return (
    <div className="dialog-backdrop" onMouseDown={onClose}>
      <div
        className="dialog dialog--wide doc-viewer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="doc-viewer-title"
        ref={dialogRef}
        tabIndex={-1}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <h2 className="dialog__title" id="doc-viewer-title">
          {document.original_filename}
        </h2>

        {status === 'loading' ? (
          <p className="doc-viewer__state" role="status">
            Loading extracted text…
          </p>
        ) : null}

        {status === 'error' ? (
          <div>
            <p className="alert alert--danger" role="alert">
              {error}
            </p>
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
        ) : null}

        {status === 'ready' && content ? (
          <>
            <dl className="detail-list doc-viewer__summary">
              <div className="detail-list__row">
                <dt>Page count</dt>
                <dd>{pluralPages(content.page_count) || '—'}</dd>
              </div>
              <div className="detail-list__row">
                <dt>Text length</dt>
                <dd>{formatTextLength(content.text_length) || '0 characters'}</dd>
              </div>
              <div className="detail-list__row">
                <dt>Extraction method</dt>
                <dd>{content.extraction_method || '—'}</dd>
              </div>
            </dl>

            {!hasAnyText ? (
              <p className="doc-viewer__state">No extracted text is available.</p>
            ) : (
              <>
                <nav className="doc-viewer__nav" aria-label="Extracted text pages">
                  <button
                    type="button"
                    className="btn btn--small btn--ghost"
                    onClick={() => setPageIndex((index) => Math.max(0, index - 1))}
                    disabled={pageIndex <= 0}
                  >
                    Previous
                  </button>
                  <span className="doc-viewer__page-label" aria-live="polite">
                    Page {pageIndex + 1} of {totalPages}
                  </span>
                  <button
                    type="button"
                    className="btn btn--small btn--ghost"
                    onClick={() =>
                      setPageIndex((index) => Math.min(pages.length - 1, index + 1))
                    }
                    disabled={pageIndex >= pages.length - 1}
                  >
                    Next
                  </button>
                </nav>

                <pre className="doc-viewer__text" tabIndex={0}>
                  {current && (current.text || '').trim()
                    ? current.text
                    : 'This page contains no extractable text.'}
                </pre>
              </>
            )}

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
          </>
        ) : null}
      </div>
    </div>
  )
}
