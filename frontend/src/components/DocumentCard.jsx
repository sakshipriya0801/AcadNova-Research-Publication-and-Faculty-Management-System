import { formatDate } from '../utils/publication'
import {
  documentTypeLabel,
  formatFileSize,
  formatTextLength,
  pluralPages,
  processingMeta,
} from '../utils/documents'

export default function DocumentCard({
  document,
  busy = '',
  error = '',
  ragStatus = '',
  ragError = '',
  canDelete = true,
  onProcess,
  onProcessAI,
  onContent,
  onMetadata,
  onDownload,
  onDelete,
}) {
  const meta = processingMeta(document.processing_status)
  const processed = document.processing_status === 'processed'
  const failed = document.processing_status === 'failed'
  const idle = document.processing_status === 'not_processed'
  const active = document.processing_status === 'processing'
  const processing = active || busy === 'process'
  const pages = pluralPages(document.page_count)
  const textLength = formatTextLength(document.extracted_text_length)
  const size = formatFileSize(document.file_size)
  const aiBusy = busy === 'ai'
  const ragCompleted = ragStatus === 'completed'
  const ragFailed = ragStatus === 'failed'
  const ragProcessing = ragStatus === 'processing'

  return (
    <article className="doc-card" aria-label={`Document ${document.original_filename}`}>
      <div className="doc-card__head">
        <h3 className="doc-card__title">{document.original_filename}</h3>
        <span className={`doc-status doc-status--${document.processing_status}`}>
          <span aria-hidden="true">{meta.symbol}</span> {meta.label}
        </span>
      </div>

      <p className="doc-card__meta">
        {documentTypeLabel(document.document_type)}
        {size ? ` · ${size}` : ''}
        {document.created_at ? ` · Uploaded ${formatDate(document.created_at)}` : ''}
      </p>

      {pages || textLength ? (
        <p className="doc-card__stats">
          {[pages, textLength].filter(Boolean).join(' · ')}
        </p>
      ) : null}

      {failed && !error && document.processing_error ? (
        <p className="doc-card__hint">
          PDF processing failed. {document.processing_error}
        </p>
      ) : null}

      {processed || ragStatus ? (
        <p className="doc-card__hint">
          {ragError
            ? `AI indexing failed. ${ragError}`
            : ragProcessing || aiBusy
              ? 'Preparing AI index…'
              : ragCompleted
                ? 'AI index ready.'
                : ragFailed
                  ? 'AI indexing failed.'
                  : 'Not indexed for AI yet.'}
        </p>
      ) : null}

      {error ? (
        <p className="alert alert--danger" role="alert">
          {error}
        </p>
      ) : null}

      <div className="doc-card__actions">
        {processing ? (
          <button type="button" className="btn btn--small btn--ghost" disabled>
            Processing PDF…
          </button>
        ) : null}

        {(idle || failed) && !processing ? (
          <button
            type="button"
            className="btn btn--small btn--ghost"
            onClick={onProcess}
          >
            {failed ? 'Try Again' : 'Process'}
          </button>
        ) : null}

        {processed ? (
          <button type="button" className="btn btn--small btn--ghost" onClick={onContent}>
            View Content
          </button>
        ) : null}

        {processed ? (
          <button type="button" className="btn btn--small btn--ghost" onClick={onMetadata}>
            Metadata
          </button>
        ) : null}

        {processed && !ragCompleted ? (
          <button
            type="button"
            className="btn btn--small btn--ghost"
            onClick={onProcessAI}
            disabled={aiBusy || ragProcessing}
          >
            {aiBusy || ragProcessing
              ? 'Preparing AI…'
              : ragFailed
                ? 'Retry AI Index'
                : 'Process for AI'}
          </button>
        ) : null}

        <button
          type="button"
          className="btn btn--small btn--ghost"
          onClick={onDownload}
          disabled={busy === 'download'}
        >
          {busy === 'download' ? 'Downloading…' : 'Download'}
        </button>

        {canDelete ? (
          <button
            type="button"
            className="btn btn--small btn--danger-outline"
            onClick={onDelete}
            disabled={busy === 'delete'}
          >
            {busy === 'delete' ? 'Deleting…' : 'Delete'}
          </button>
        ) : null}
      </div>
    </article>
  )
}
