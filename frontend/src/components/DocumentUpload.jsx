import { useRef, useState } from 'react'
import { uploadPublicationDocument } from '../services/documentService'
import {
  DOCUMENT_TYPES,
  formatFileSize,
  getDocumentError,
  validateDocumentFile,
} from '../utils/documents'

export default function DocumentUpload({ publicationId, onUploaded, onCancel }) {
  const inputRef = useRef(null)
  const [file, setFile] = useState(null)
  const [documentType, setDocumentType] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  function handleFileChange(event) {
    setFile(event.target.files?.[0] || null)
    setError('')
  }

  function handleSubmit(event) {
    event.preventDefault()
    if (busy) return
    const fileError = validateDocumentFile(file)
    if (fileError) {
      setError(fileError)
      return
    }
    if (!documentType) {
      setError('Please select a document type.')
      return
    }
    setBusy(true)
    setError('')
    uploadPublicationDocument(publicationId, file, documentType)
      .then((response) => {
        setFile(null)
        setDocumentType('')
        if (inputRef.current) inputRef.current.value = ''
        onUploaded(response.data)
      })
      .catch((uploadError) => {
        setError(getDocumentError(uploadError))
      })
      .finally(() => {
        setBusy(false)
      })
  }

  return (
    <form className="doc-upload" onSubmit={handleSubmit} aria-label="Upload document">
      {error ? (
        <p className="alert alert--danger" role="alert">
          {error}
        </p>
      ) : null}

      <div className="field">
        <label className="field__label" htmlFor="doc-upload-file">
          PDF file
        </label>
        <input
          id="doc-upload-file"
          className="field__input"
          type="file"
          accept=".pdf,application/pdf"
          onChange={handleFileChange}
          disabled={busy}
          ref={inputRef}
        />
      </div>

      {file ? (
        <p className="doc-upload__file" role="status">
          {file.name} · {formatFileSize(file.size)}
        </p>
      ) : null}

      <div className="field">
        <label className="field__label" htmlFor="doc-upload-type">
          Document type
        </label>
        <select
          id="doc-upload-type"
          className="field__input"
          value={documentType}
          onChange={(event) => {
            setDocumentType(event.target.value)
            setError('')
          }}
          disabled={busy}
        >
          <option value="">Select document type</option>
          {DOCUMENT_TYPES.map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
        </select>
      </div>

      <div className="doc-upload__actions">
        <button type="submit" className="btn btn--primary" disabled={busy}>
          {busy ? 'Uploading…' : 'Upload'}
        </button>
        <button
          type="button"
          className="btn btn--ghost"
          onClick={onCancel}
          disabled={busy}
        >
          Cancel
        </button>
      </div>
    </form>
  )
}
