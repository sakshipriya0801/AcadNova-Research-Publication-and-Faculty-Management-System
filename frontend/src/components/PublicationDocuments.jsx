import { useCallback, useEffect, useId, useState } from 'react'
import ConfirmDialog from './ConfirmDialog'
import DocumentCard from './DocumentCard'
import DocumentMetadata from './DocumentMetadata'
import DocumentUpload from './DocumentUpload'
import ExtractedContentViewer from './ExtractedContentViewer'
import {
  deletePublicationDocument,
  downloadPublicationDocument,
  listPublicationDocuments,
} from '../services/documentService'
import {
  processDocument,
  getProcessingStatus,
} from '../services/pdfProcessingService'
import {
  getKnowledgeStatus,
  processDocumentKnowledge,
} from '../services/ragService'
import {
  getDocumentError,
  getProcessError,
  getRagError,
  saveBlobResponse,
} from '../utils/documents'

export default function PublicationDocuments({
  publicationId,
  heading,
  showCount = false,
  emptyMessage = 'No documents uploaded yet.',
  canManage = true,
}) {
  const headingId = useId()
  const [documents, setDocuments] = useState([])
  const [listStatus, setListStatus] = useState('loading')
  const [listError, setListError] = useState('')
  const [notice, setNotice] = useState('')
  const [showUpload, setShowUpload] = useState(false)
  const [busyById, setBusyById] = useState({})
  const [errorById, setErrorById] = useState({})
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleteBusy, setDeleteBusy] = useState(false)
  const [deleteError, setDeleteError] = useState('')
  const [contentDoc, setContentDoc] = useState(null)
  const [metadataDoc, setMetadataDoc] = useState(null)

  const load = useCallback(
    (silent = false) => {
      if (!silent) setListStatus('loading')
      return listPublicationDocuments(publicationId)
        .then(async (response) => {
          const items = response.data || []
          const withStatus = items.filter(
            (item) =>
              item.processing_status === 'processed' || item.processing_status === 'failed',
          )
          const statusMap = {}
          if (withStatus.length > 0) {
            const statuses = await Promise.all(
              withStatus.map((item) =>
                getProcessingStatus(publicationId, item.id)
                  .then((result) => result.data)
                  .catch(() => null),
              ),
            )
            withStatus.forEach((item, index) => {
              statusMap[item.id] = statuses[index]
            })
          }
          const merged = items.map((item) => {
            const info = statusMap[item.id]
            if (!info) return item
            return {
              ...item,
              processing_status: info.processing_status ?? item.processing_status,
              processing_error: info.processing_error ?? item.processing_error ?? null,
              page_count: info.page_count ?? item.page_count ?? null,
              extracted_text_length:
                info.extracted_text_length ?? item.extracted_text_length ?? null,
              extracted_at: info.extracted_at ?? item.extracted_at ?? null,
            }
          })
          const processedItems = merged.filter(
            (item) => item.processing_status === 'processed',
          )
          const ragMap = {}
          if (processedItems.length > 0) {
            const ragStatuses = await Promise.all(
              processedItems.map((item) =>
                getKnowledgeStatus(publicationId, item.id)
                  .then((result) => result.data)
                  .catch(() => null),
              ),
            )
            processedItems.forEach((item, index) => {
              ragMap[item.id] = ragStatuses[index]
            })
          }
          const withRag = merged.map((item) => {
            const info = ragMap[item.id]
            if (!info) return item
            return {
              ...item,
              rag_status: info.rag_status,
              rag_error: info.rag_error ?? null,
            }
          })
          setDocuments(withRag)
          setListStatus('ready')
          setListError('')
        })
        .catch((error) => {
          if (silent) return
          setListError(getDocumentError(error))
          setListStatus('error')
        })
    },
    [publicationId],
  )

  useEffect(() => {
    setDocuments([])
    setNotice('')
    setShowUpload(false)
    setBusyById({})
    setErrorById({})
    setContentDoc(null)
    setMetadataDoc(null)
    setDeleteTarget(null)
    load(false)
  }, [load])

  function handleUploaded(document) {
    setNotice('Document uploaded.')
    setShowUpload(false)
    load(true)
    return document
  }

  function setBusy(documentId, kind) {
    setBusyById((current) => ({ ...current, [documentId]: kind }))
  }

  function clearBusy(documentId) {
    setBusyById((current) => {
      const next = { ...current }
      delete next[documentId]
      return next
    })
  }

  function setDocumentError(documentId, message) {
    setErrorById((current) => ({ ...current, [documentId]: message }))
  }

  function clearDocumentError(documentId) {
    setErrorById((current) => {
      const next = { ...current }
      delete next[documentId]
      return next
    })
  }

  function handleProcess(document) {
    if (busyById[document.id]) return
    setBusy(document.id, 'process')
    clearDocumentError(document.id)
    processDocument(publicationId, document.id)
      .then((response) => {
        const info = response.data || {}
        setDocuments((current) =>
          current.map((item) =>
            item.id === document.id
              ? {
                  ...item,
                  processing_status: info.processing_status ?? item.processing_status,
                  processing_error: info.processing_error ?? null,
                  page_count: info.page_count ?? item.page_count ?? null,
                  extracted_text_length:
                    info.extracted_text_length ?? item.extracted_text_length ?? null,
                  extracted_at: info.extracted_at ?? item.extracted_at ?? null,
                }
              : item,
          ),
        )
        load(true)
      })
      .catch((error) => {
        setDocumentError(document.id, getProcessError(error))
        load(true)
      })
      .finally(() => {
        clearBusy(document.id)
      })
  }

  function handleProcessKnowledge(document) {
    if (busyById[document.id]) return
    setBusy(document.id, 'ai')
    clearDocumentError(document.id)
    processDocumentKnowledge(publicationId, document.id)
      .then(() => load(true))
      .catch((error) => {
        setDocumentError(document.id, getRagError(error))
        load(true)
      })
      .finally(() => {
        clearBusy(document.id)
      })
  }

  function handleDownload(document) {    if (busyById[document.id]) return
    setBusy(document.id, 'download')
    clearDocumentError(document.id)
    downloadPublicationDocument(publicationId, document.id)
      .then((response) => {
        saveBlobResponse(response, document.original_filename)
      })
      .catch((error) => {
        setDocumentError(document.id, getDocumentError(error))
      })
      .finally(() => {
        clearBusy(document.id)
      })
  }

  function handleDeleteConfirm() {
    if (!deleteTarget || deleteBusy) return
    setDeleteBusy(true)
    setDeleteError('')
    deletePublicationDocument(publicationId, deleteTarget.id)
      .then(() => {
        setDeleteTarget(null)
        setNotice('Document deleted.')
        load(true)
      })
      .catch((error) => {
        setDeleteError(getDocumentError(error))
      })
      .finally(() => {
        setDeleteBusy(false)
      })
  }

  return (
    <section className="panel doc-section" aria-labelledby={headingId}>
      <div className="doc-section__head">
        <h2 className="panel__title" id={headingId}>
          {heading}
        </h2>
        <div className="doc-section__tools">
          {showCount && listStatus === 'ready' ? (
            <span className="doc-count">Documents ({documents.length})</span>
          ) : null}
          {canManage ? (
            <button
              type="button"
              className="btn btn--ghost btn--small"
              aria-expanded={showUpload}
              onClick={() => {
                setShowUpload((open) => !open)
                setNotice('')
              }}
            >
              {showUpload ? 'Hide Upload' : '+ Upload Document'}
            </button>
          ) : null}
        </div>
      </div>

      {notice ? (
        <div className="alert alert--success" role="status">
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

      {showUpload && canManage ? (
        <DocumentUpload
          publicationId={publicationId}
          onUploaded={handleUploaded}
          onCancel={() => setShowUpload(false)}
        />
      ) : null}

      {listStatus === 'loading' ? (
        <p className="panel__empty" role="status">
          Loading documents…
        </p>
      ) : null}

      {listStatus === 'error' ? (
        <div className="doc-section__error">
          <p className="alert alert--danger" role="alert">
            {listError}
          </p>
          <button type="button" className="btn btn--ghost" onClick={() => load(false)}>
            Try Again
          </button>
        </div>
      ) : null}

      {listStatus === 'ready' && documents.length === 0 ? (
        <p className="panel__empty">{emptyMessage}</p>
      ) : null}

      {documents.length > 0 ? (
        <div className="doc-grid">
          {documents.map((document) => (
            <DocumentCard
              key={document.id}
              document={document}
              busy={busyById[document.id] || ''}
              error={errorById[document.id] || ''}
              ragStatus={document.rag_status || ''}
              ragError={document.rag_error || ''}
              canDelete={canManage}
              onProcess={() => handleProcess(document)}
              onProcessAI={() => handleProcessKnowledge(document)}
              onContent={() => setContentDoc(document)}
              onMetadata={() => setMetadataDoc(document)}
              onDownload={() => handleDownload(document)}
              onDelete={() => {
                setDeleteError('')
                setDeleteTarget(document)
              }}
            />
          ))}
        </div>
      ) : null}

      {contentDoc ? (
        <ExtractedContentViewer
          publicationId={publicationId}
          document={contentDoc}
          onClose={() => setContentDoc(null)}
        />
      ) : null}

      {metadataDoc ? (
        <DocumentMetadata
          publicationId={publicationId}
          document={metadataDoc}
          onClose={() => setMetadataDoc(null)}
        />
      ) : null}

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title="Delete document"
        message="Delete this document? Deleted documents cannot be accessed from the application."
        confirmLabel="Delete"
        busy={deleteBusy}
        error={deleteError}
        onConfirm={handleDeleteConfirm}
        onCancel={() => {
          if (!deleteBusy) setDeleteTarget(null)
        }}
      />
    </section>
  )
}
