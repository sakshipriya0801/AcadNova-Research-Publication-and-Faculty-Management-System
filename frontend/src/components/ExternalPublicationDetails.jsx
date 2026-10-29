import { useEffect, useRef } from 'react'
import {
  externalResultRows,
  formatAuthors,
  hasImportableTitle,
  requiresAuthorMatch,
  resultTitle,
  sourceLabel,
} from '../utils/external'

export default function ExternalPublicationDetails({ result, source, onClose, onImport }) {
  const dialogRef = useRef(null)
  const closeRef = useRef(null)

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

  if (!result) return null

  const rows = externalResultRows(result)
  const authors = formatAuthors(result.authors, 8)
  const importable = hasImportableTitle(result)

  return (
    <div className="dialog-backdrop" onMouseDown={onClose}>
      <div
        className="dialog dialog--wide"
        role="dialog"
        aria-modal="true"
        aria-labelledby="external-details-title"
        ref={dialogRef}
        tabIndex={-1}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <h2 className="dialog__title" id="external-details-title">
          {resultTitle(result)}
        </h2>

        {authors ? (
          <p className="ext-details__authors">{authors}</p>
        ) : (
          <p className="ext-details__authors">No author information available.</p>
        )}

        <dl className="detail-list">
          {rows.map((row) => (
            <div className="detail-list__row" key={row.label}>
              <dt>{row.label}</dt>
              <dd>
                {row.href ? (
                  <a href={row.href} target="_blank" rel="noopener noreferrer">
                    {row.value}
                  </a>
                ) : (
                  row.value
                )}
              </dd>
            </div>
          ))}
        </dl>

        {result.abstract ? (
          <section className="ext-details__abstract-section">
            <h3 className="ext-details__subtitle">Abstract</h3>
            <p className="ext-details__abstract">{result.abstract}</p>
          </section>
        ) : null}

        <section className="ext-details__match" aria-labelledby="ext-match-heading">
          <h3 className="ext-details__subtitle" id="ext-match-heading">
            Author matching
          </h3>
          {requiresAuthorMatch(source) ? (
            <p>
              The backend checks author matching when you import from{' '}
              {sourceLabel(source)}. If the match is not high confidence you will be
              asked to confirm that you are an author before the import completes.
            </p>
          ) : (
            <p>
              Author matching is not applied when importing from {sourceLabel(source)}.
            </p>
          )}
        </section>

        {!importable ? (
          <p className="alert alert--danger" role="alert">
            This record has no title, so it cannot be imported.
          </p>
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
          <button
            type="button"
            className="btn btn--primary"
            onClick={() => onImport(result)}
            disabled={!importable}
          >
            Import Publication
          </button>
        </div>
      </div>
    </div>
  )
}
