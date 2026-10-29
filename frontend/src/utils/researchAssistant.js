// Pure helpers for the AI Research Assistant. Kept framework-free so they can
// be unit-tested and reused by the page component.

export const MAX_QUESTION_LENGTH = 2000

// Mirrors the backend messages exactly so the UI can recognise these states.
// The frontend never generates answers — it only displays backend responses.
export const AI_NOT_CONFIGURED_DETAIL = 'AI provider is not configured.'
export const NO_ANSWER_MESSAGE =
  'I could not find enough relevant information in the uploaded research documents to answer this question.'

export const SUGGESTED_QUESTIONS = [
  'What is the main objective of this research?',
  'Summarize the methodology.',
  'What are the key findings?',
  'What limitations are mentioned?',
  'Which dataset was used?',
]

// Builds the /api/rag/query body from the selected scope. It intentionally
// never includes faculty_id, embeddings or any authorization fields — the
// backend derives identity from the session and remains authoritative.
export function buildQueryRequest({
  question,
  scopeType = 'all',
  publicationId = '',
  documentId = '',
} = {}) {
  const body = { query: String(question || '').trim() }
  if (scopeType === 'document' && documentId) {
    body.document_id = documentId
  } else if (scopeType === 'publication' && publicationId) {
    body.publication_id = publicationId
  }
  return body
}

export function validateQuestion(question) {
  const text = String(question || '').trim()
  if (!text) return 'Please enter a research question.'
  if (text.length > MAX_QUESTION_LENGTH) {
    return `Questions must be ${MAX_QUESTION_LENGTH} characters or fewer.`
  }
  return ''
}

export function isProcessedDocument(ragStatus) {
  return ragStatus === 'completed'
}

export function processingLabel(ragStatus) {
  if (ragStatus === 'completed') return 'Processed'
  if (ragStatus === 'processing') return 'Processing'
  if (ragStatus === 'failed') return 'Failed'
  return 'Not processed'
}

export function formatSourceLocation(source) {
  const start = source?.page_start
  const end = source?.page_end
  if (start == null && end == null) return 'Page information unavailable'
  if (start != null && end != null && end !== start) return `Pages ${start}–${end}`
  const page = start != null ? start : end
  return `Page ${page}`
}

export function formatRelevance(score) {
  if (typeof score !== 'number' || Number.isNaN(score)) return ''
  return `${Math.round(score * 100)}%`
}

// A backend answer is "no answer" when nothing relevant was retrieved. Real
// answers always carry at least one source.
export function isNoAnswerResponse(response) {
  if (!response) return false
  const sources = response.sources || []
  return response.retrieved_chunks === 0 || sources.length === 0
}

export function sourceLink(source) {
  if (source?.publication_id) return `/publications/${source.publication_id}`
  return '/documents'
}

// Splits a plain-text answer into paragraph and bullet blocks for readable
// rendering. The text is never rewritten.
export function parseAnswerBlocks(answer) {
  const text = String(answer || '').replace(/\r\n/g, '\n')
  const blocks = []
  let paragraph = []
  let list = []

  const flushParagraph = () => {
    if (paragraph.length) {
      blocks.push({ type: 'p', text: paragraph.join(' ') })
      paragraph = []
    }
  }
  const flushList = () => {
    if (list.length) {
      blocks.push({ type: 'ul', items: list })
      list = []
    }
  }

  text.split('\n').forEach((raw) => {
    const line = raw.trim()
    if (!line) {
      flushParagraph()
      flushList()
      return
    }
    const bullet = line.match(/^(?:[-*•]|\d+\.)\s+(.*)$/)
    if (bullet) {
      flushParagraph()
      list.push(bullet[1])
    } else {
      flushList()
      paragraph.push(line)
    }
  })
  flushParagraph()
  flushList()

  return blocks.length ? blocks : [{ type: 'p', text }]
}
