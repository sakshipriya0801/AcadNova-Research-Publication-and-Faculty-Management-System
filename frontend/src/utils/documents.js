export const DOCUMENT_TYPES = [
  { value: 'research_paper', label: 'Research Paper' },
  { value: 'conference_paper', label: 'Conference Paper' },
  { value: 'book_chapter', label: 'Book Chapter' },
  { value: 'patent_document', label: 'Patent Document' },
  { value: 'copyright_document', label: 'Copyright Document' },
  { value: 'supporting_evidence', label: 'Supporting Evidence' },
  { value: 'other', label: 'Other' },
]

export const MAX_DOCUMENT_SIZE_MB = 20

export const PROCESSING_META = {
  not_processed: { symbol: '○', label: 'Not Processed' },
  processing: { symbol: '⏳', label: 'Processing' },
  processed: { symbol: '✓', label: 'Processed' },
  failed: { symbol: '⚠', label: 'Failed' },
}

export function documentTypeLabel(value) {
  const found = DOCUMENT_TYPES.find((item) => item.value === value)
  return found ? found.label : value || '—'
}

export function processingMeta(value) {
  return PROCESSING_META[value] || PROCESSING_META.not_processed
}

export function formatFileSize(bytes) {
  if (bytes === null || bytes === undefined || bytes === '') return null
  const size = Number(bytes)
  if (!Number.isFinite(size) || size < 0) return null
  if (size >= 1024 * 1024) return `${(size / (1024 * 1024)).toFixed(1)} MB`
  if (size >= 1024) return `${Math.round(size / 1024)} KB`
  return `${size} B`
}

export function pluralPages(count) {
  if (count === null || count === undefined || count === '') return null
  const pages = Number(count)
  if (!Number.isFinite(pages) || pages < 0) return null
  return pages === 1 ? '1 page' : `${pages} pages`
}

export function formatTextLength(length) {
  if (length === null || length === undefined || length === '') return null
  const value = Number(length)
  if (!Number.isFinite(value) || value < 0) return null
  return `${value.toLocaleString('en-GB')} characters`
}

export function isPdfFilename(name) {
  return /\.pdf$/i.test(String(name || '').trim())
}

export function validateDocumentFile(file) {
  if (!file) return 'Please select a PDF file.'
  if (!isPdfFilename(file.name)) return 'Invalid PDF file.'
  if (!file.size) return 'The selected file is empty.'
  if (file.size > MAX_DOCUMENT_SIZE_MB * 1024 * 1024) return 'File is too large.'
  return ''
}

function responseDetail(error) {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail.trim()
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') return item
        return typeof item?.msg === 'string' ? item.msg : ''
      })
      .filter(Boolean)
      .join(' ')
      .trim()
  }
  return ''
}

function safeDetail(error) {
  const detail = responseDetail(error)
  if (detail && detail.length <= 160 && !/Traceback|\/home\/|self\.|storage_path/i.test(detail)) {
    return detail
  }
  return ''
}

export function getDocumentError(error) {
  if (!error?.response) return 'Unable to connect to the server.'
  const status = error.response.status
  if (status === 401) return 'Your session has expired. Please sign in again.'
  if (status === 403) return "You don't have permission to access this document."
  if (status === 404) return 'Document not found.'
  if (status === 409) return 'That document has already been uploaded.'
  if (status === 413) return 'File is too large.'
  if (status === 422) return safeDetail(error) || 'PDF processing failed.'
  if (status === 400) return safeDetail(error) || 'Please check the document and try again.'
  if (status >= 500) return 'Something went wrong while processing the document.'
  return safeDetail(error) || 'Something went wrong. Please try again.'
}

export function getProcessError(error) {
  if (error?.response?.status === 422) {
    const detail = safeDetail(error)
    if (!detail || /^PDF processing failed\.?$/i.test(detail)) return 'PDF processing failed.'
    return `PDF processing failed. ${detail}`
  }
  return getDocumentError(error)
}

export function getRagError(error) {
  if (error?.response?.status === 503) {
    return safeDetail(error) || 'AI service is currently unavailable.'
  }
  return getDocumentError(error)
}

export function getContentError(error) {
  if (error?.response?.status === 404) return 'This PDF has not been processed yet.'
  return getDocumentError(error)
}

export function downloadFileName(header, fallback) {
  const value = String(header || '')
  const star = /filename\*=UTF-8''([^;]+)/i.exec(value)
  if (star) {
    try {
      const decoded = decodeURIComponent(star[1].trim())
      if (decoded) return decoded
    } catch {
      return fallback || 'document.pdf'
    }
  }
  const plain = /filename="?([^";]+)"?/i.exec(value)
  if (plain && plain[1].trim()) return plain[1].trim()
  return fallback || 'document.pdf'
}

export function saveBlobResponse(response, fallbackName) {
  const header = response?.headers?.['content-disposition']
  const name = downloadFileName(header, fallbackName)
  const url = URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('a')
  link.href = url
  link.download = name
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  return name
}
