import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { listPublications } from '../services/publicationService'
import { listPublicationDocuments } from '../services/documentService'
import { getKnowledgeStatus, queryResearch } from '../services/ragService'
import { getPublicationError, getRagQueryError } from '../utils/errors'
import {
  AI_NOT_CONFIGURED_DETAIL,
  MAX_QUESTION_LENGTH,
  SUGGESTED_QUESTIONS,
  buildQueryRequest,
  formatRelevance,
  formatSourceLocation,
  isNoAnswerResponse,
  isProcessedDocument,
  parseAnswerBlocks,
  processingLabel,
  sourceLink,
  validateQuestion,
} from '../utils/researchAssistant'

function SourceList({ sources, docNames, publicationMap }) {
  if (!sources || sources.length === 0) return null
  return (
    <div className="ra-sources">
      <p className="ra-sources__title">Sources</p>
      <ul className="ra-sources__list">
        {sources.map((source, index) => {
          const name =
            publicationMap[source.publication_id] ||
            docNames[source.document_id] ||
            'Research document'
          const relevance = formatRelevance(source.relevance_score)
          return (
            <li
              key={`${source.document_id || 'doc'}-${source.chunk_index ?? index}-${index}`}
              className="ra-source"
            >
              <Link className="ra-source__link" to={sourceLink(source)}>
                <span aria-hidden="true">📄</span>
                <span className="ra-source__name">{name}</span>
              </Link>
              <span className="ra-source__page">{formatSourceLocation(source)}</span>
              {relevance ? (
                <span className="ra-source__rel">Relevance {relevance}</span>
              ) : null}
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function Message({ message, docNames, publicationMap }) {
  if (message.role === 'user') {
    return (
      <div className="ra-msg ra-msg--user">
        <p className="ra-msg__who">You</p>
        <p className="ra-msg__text">{message.text}</p>
      </div>
    )
  }

  if (message.kind === 'config') {
    return (
      <div className="ra-msg ra-msg--assistant">
        <p className="ra-msg__who">Research AI</p>
        <div className="alert alert--warning" role="alert">
          AI analysis is not configured on this server. Please contact your
          administrator.
        </div>
      </div>
    )
  }

  if (message.kind === 'error') {
    return (
      <div className="ra-msg ra-msg--assistant">
        <p className="ra-msg__who">Research AI</p>
        <div className="alert alert--danger" role="alert">
          {message.text}
        </div>
      </div>
    )
  }

  const blocks = parseAnswerBlocks(message.answer)
  return (
    <div className="ra-msg ra-msg--assistant">
      <p className="ra-msg__who">Research AI</p>
      <div className="ra-msg__answer">
        {blocks.map((block, index) =>
          block.type === 'ul' ? (
            <ul key={index}>
              {block.items.map((item, itemIndex) => (
                <li key={itemIndex}>{item}</li>
              ))}
            </ul>
          ) : (
            <p key={index}>{block.text}</p>
          ),
        )}
      </div>
      {message.noAnswer ? (
        <p className="ra-note">No sufficiently relevant source was found.</p>
      ) : null}
      <SourceList
        sources={message.sources}
        docNames={docNames}
        publicationMap={publicationMap}
      />
      {message.model ? (
        <p className="ra-meta">
          Model: {message.model}
          {typeof message.processingTimeMs === 'number'
            ? ` · ${message.processingTimeMs} ms`
            : ''}
        </p>
      ) : null}
    </div>
  )
}

export default function ResearchAssistantPage() {
  const [publications, setPublications] = useState([])
  const [pubsStatus, setPubsStatus] = useState('loading')
  const [pubsError, setPubsError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  const [scopeValue, setScopeValue] = useState('all')
  const [documents, setDocuments] = useState([])
  const [docsStatus, setDocsStatus] = useState('idle')
  const [ragStatusByDoc, setRagStatusByDoc] = useState({})
  const [selectedDocumentId, setSelectedDocumentId] = useState('')

  const [question, setQuestion] = useState('')
  const [composerError, setComposerError] = useState('')
  const [messages, setMessages] = useState([])
  const [asking, setAsking] = useState(false)
  const [docNames, setDocNames] = useState({})

  const textareaRef = useRef(null)
  const loadedPubDocs = useRef(new Set())

  const publicationMap = useMemo(
    () =>
      Object.fromEntries(
        publications.map((pub) => [pub.publication_id, pub.title]),
      ),
    [publications],
  )

  const selectedPublicationId = scopeValue.startsWith('pub:')
    ? scopeValue.slice(4)
    : ''
  const scopeType = selectedPublicationId ? 'publication' : 'all'

  useEffect(() => {
    let cancelled = false
    setPubsStatus('loading')
    setPubsError('')
    listPublications({
      page: 1,
      page_size: 100,
      sort_by: 'publication_date',
      sort_order: 'desc',
    })
      .then((response) => {
        if (cancelled) return
        setPublications(response.data.items || [])
        setPubsStatus('ready')
      })
      .catch((error) => {
        if (cancelled) return
        setPubsError(getPublicationError(error))
        setPubsStatus('error')
      })
    return () => {
      cancelled = true
    }
  }, [reloadKey])

  useEffect(() => {
    if (!selectedPublicationId) {
      setDocuments([])
      setRagStatusByDoc({})
      setSelectedDocumentId('')
      setDocsStatus('idle')
      return undefined
    }
    let cancelled = false
    setDocsStatus('loading')
    setSelectedDocumentId('')
    listPublicationDocuments(selectedPublicationId)
      .then(async (response) => {
        const items = response.data || []
        const statuses = await Promise.all(
          items.map((doc) =>
            getKnowledgeStatus(selectedPublicationId, doc.id)
              .then((result) => result.data?.rag_status)
              .catch(() => null),
          ),
        )
        if (cancelled) return
        const map = {}
        items.forEach((doc, index) => {
          map[doc.id] = statuses[index] || 'pending'
        })
        setDocuments(items)
        setRagStatusByDoc(map)
        setDocNames((prev) => ({
          ...prev,
          ...Object.fromEntries(items.map((doc) => [doc.id, doc.original_filename])),
        }))
        loadedPubDocs.current.add(selectedPublicationId)
        setDocsStatus('ready')
      })
      .catch(() => {
        if (!cancelled) setDocsStatus('error')
      })
    return () => {
      cancelled = true
    }
  }, [selectedPublicationId])

  function ensureSourceNames(sources) {
    const publicationIds = [
      ...new Set((sources || []).map((source) => source.publication_id).filter(Boolean)),
    ]
    publicationIds.forEach((pid) => {
      if (loadedPubDocs.current.has(pid)) return
      loadedPubDocs.current.add(pid)
      listPublicationDocuments(pid)
        .then((response) => {
          const items = response.data || []
          setDocNames((prev) => ({
            ...prev,
            ...Object.fromEntries(items.map((doc) => [doc.id, doc.original_filename])),
          }))
        })
        .catch(() => {})
    })
  }

  function submitQuestion() {
    if (asking) return
    const text = question.trim()
    const invalid = validateQuestion(text)
    if (invalid) {
      setComposerError(invalid)
      return
    }
    setComposerError('')
    const request = buildQueryRequest({
      question: text,
      scopeType,
      publicationId: selectedPublicationId,
      documentId: selectedDocumentId,
    })
    setQuestion('')
    setMessages((prev) => [
      ...prev,
      { id: `q-${prev.length}`, role: 'user', text },
    ])
    setAsking(true)
    queryResearch(request)
      .then((response) => {
        const data = response.data || {}
        ensureSourceNames(data.sources)
        setMessages((prev) => [
          ...prev,
          {
            id: `a-${prev.length}`,
            role: 'assistant',
            answer: data.answer,
            sources: data.sources || [],
            noAnswer: isNoAnswerResponse(data),
            model: data.model,
            processingTimeMs: data.processing_time_ms,
          },
        ])
      })
      .catch((error) => {
        const status = error?.response?.status
        const detail = error?.response?.data?.detail
        const isConfigError =
          status === 503 && detail === AI_NOT_CONFIGURED_DETAIL
        setMessages((prev) => [
          ...prev,
          isConfigError
            ? { id: `a-${prev.length}`, role: 'assistant', kind: 'config' }
            : {
                id: `a-${prev.length}`,
                role: 'assistant',
                kind: 'error',
                text: getRagQueryError(error),
              },
        ])
      })
      .finally(() => setAsking(false))
  }

  function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      submitQuestion()
    }
  }

  function handleSuggestion(suggestion) {
    setQuestion(suggestion)
    if (textareaRef.current) textareaRef.current.focus()
  }

  const hasProcessedDocument =
    documents.length > 0 &&
    documents.some((doc) => isProcessedDocument(ragStatusByDoc[doc.id]))

  return (
    <div className="page ra-page">
      <div className="page__header">
        <div>
          <h1 className="page__title">AI Research Assistant</h1>
          <p className="page__subtitle">
            Ask questions about your uploaded research documents.
          </p>
        </div>
      </div>

      {pubsStatus === 'loading' ? (
        <p className="panel__empty" role="status">
          Loading your research documents…
        </p>
      ) : null}

      {pubsStatus === 'error' ? (
        <div className="ra-error">
          <p className="alert alert--danger" role="alert">
            {pubsError}
          </p>
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => setReloadKey((key) => key + 1)}
          >
            Try Again
          </button>
        </div>
      ) : null}

      {pubsStatus === 'ready' && publications.length === 0 ? (
        <div className="empty-state">
          <p className="empty-state__title">No processed research documents yet.</p>
          <p className="empty-state__text">
            Upload and process a publication document for AI analysis first.
          </p>
          <Link className="btn btn--primary" to="/documents">
            Go to Documents
          </Link>
        </div>
      ) : null}

      {publications.length > 0 ? (
        <>
          <section className="panel ra-scope" aria-label="Research scope">
            <h2 className="panel__title">Research Scope</h2>
            <div className="ra-scope__grid">
              <div className="field">
                <label className="field__label" htmlFor="ra-scope">
                  Search within
                </label>
                <select
                  id="ra-scope"
                  className="field__input"
                  value={scopeValue}
                  onChange={(event) => setScopeValue(event.target.value)}
                  disabled={asking}
                >
                  <option value="all">All My Research Documents</option>
                  <optgroup label="Publications">
                    {publications.map((pub) => (
                      <option key={pub.publication_id} value={`pub:${pub.publication_id}`}>
                        {pub.title}
                      </option>
                    ))}
                  </optgroup>
                </select>
              </div>

              {selectedPublicationId ? (
                <div className="field">
                  <label className="field__label" htmlFor="ra-document">
                    Document (optional)
                  </label>
                  <select
                    id="ra-document"
                    className="field__input"
                    value={selectedDocumentId}
                    onChange={(event) => setSelectedDocumentId(event.target.value)}
                    disabled={asking || docsStatus === 'loading'}
                  >
                    <option value="">Whole publication</option>
                    {documents.map((doc) => {
                      const status = ragStatusByDoc[doc.id]
                      const selectable = isProcessedDocument(status)
                      return (
                        <option key={doc.id} value={doc.id} disabled={!selectable}>
                          {doc.original_filename} — {processingLabel(status)}
                        </option>
                      )
                    })}
                  </select>
                </div>
              ) : null}
            </div>

            {selectedPublicationId && docsStatus === 'ready' && !hasProcessedDocument ? (
              <p className="ra-hint">
                Process this document for AI analysis first.{' '}
                <Link to="/documents">Go to Documents</Link>
              </p>
            ) : null}
          </section>

          <section className="panel ra-chat" aria-label="AI conversation">
            <div className="ra-suggest">
              <p className="ra-suggest__title">Suggested questions</p>
              <div className="ra-suggest__items">
                {SUGGESTED_QUESTIONS.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    className="btn btn--small btn--ghost"
                    onClick={() => handleSuggestion(suggestion)}
                    disabled={asking}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>

            <div className="ra-conversation" aria-live="polite">
              {messages.length === 0 && !asking ? (
                <p className="ra-empty">
                  Ask a question to get started. Answers are grounded in your
                  uploaded documents.
                </p>
              ) : null}

              {messages.map((message) => (
                <Message
                  key={message.id}
                  message={message}
                  docNames={docNames}
                  publicationMap={publicationMap}
                />
              ))}

              {asking ? (
                <div className="ra-msg ra-msg--assistant">
                  <p className="ra-msg__who">Research AI</p>
                  <p className="ra-loading" role="status">
                    <span className="ra-spinner" aria-hidden="true" />
                    Research AI is analyzing your documents…
                  </p>
                </div>
              ) : null}
            </div>

            <form
              className="ra-composer"
              onSubmit={(event) => {
                event.preventDefault()
                submitQuestion()
              }}
            >
              <label className="visually-hidden" htmlFor="ra-question">
                Ask a question about your research
              </label>
              <textarea
                id="ra-question"
                ref={textareaRef}
                className="field__input ra-composer__input"
                rows={2}
                maxLength={MAX_QUESTION_LENGTH}
                placeholder="Ask a question about your research..."
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={handleKeyDown}
                disabled={asking}
              />
              <button
                type="submit"
                className="btn btn--primary ra-composer__send"
                disabled={asking || !question.trim()}
              >
                {asking ? 'Analyzing…' : 'Ask AI'}
              </button>
            </form>

            {composerError ? (
              <p className="alert alert--danger" role="alert">
                {composerError}
              </p>
            ) : null}
          </section>
        </>
      ) : null}
    </div>
  )
}
