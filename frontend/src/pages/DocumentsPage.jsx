import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import LoadingScreen from '../components/LoadingScreen'
import PublicationDocuments from '../components/PublicationDocuments'
import { listPublications } from '../services/publicationService'
import { getPublicationError } from '../utils/errors'

const PAGE_SIZE = 20

export default function DocumentsPage() {
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [publications, setPublications] = useState([])
  const [total, setTotal] = useState(0)
  const [pubStatus, setPubStatus] = useState('loading')
  const [pubError, setPubError] = useState('')
  const [selectedId, setSelectedId] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim())
    }, 400)
    return () => clearTimeout(timer)
  }, [searchInput])

  useEffect(() => {
    let cancelled = false
    setPubStatus('loading')
    setPubError('')
    const params = {
      page: 1,
      page_size: PAGE_SIZE,
      sort_by: 'publication_date',
      sort_order: 'desc',
    }
    if (search) params.search = search
    listPublications(params)
      .then((response) => {
        if (cancelled) return
        const items = response.data.items || []
        setPublications(items)
        setTotal(response.data.total ?? items.length)
        setSelectedId((current) => {
          if (current && items.some((item) => item.publication_id === current)) {
            return current
          }
          return items[0]?.publication_id || ''
        })
        setPubStatus('ready')
      })
      .catch((error) => {
        if (cancelled) return
        setPubError(getPublicationError(error))
        setPubStatus('error')
      })
    return () => {
      cancelled = true
    }
  }, [search, reloadKey])

  if (pubStatus === 'loading' && publications.length === 0 && !search) {
    return <LoadingScreen message="Loading publications…" />
  }

  const selected = publications.find((item) => item.publication_id === selectedId)

  return (
    <div className="page">
      <div className="page__header">
        <div>
          <h1 className="page__title">Documents</h1>
          <p className="page__subtitle">
            Upload and manage evidence documents for your publications.
          </p>
        </div>
        <div className="page__header-actions">
          <Link className="btn btn--ghost" to="/publications">
            My Publications
          </Link>
        </div>
      </div>

      {pubStatus === 'error' ? (
        <div className="doc-picker__error">
          <p className="alert alert--danger" role="alert">
            {pubError}
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

      {pubStatus === 'ready' && total === 0 && !search ? (
        <div className="empty-state">
          <p className="empty-state__title">No publications available.</p>
          <p className="empty-state__text">Add a publication first.</p>
          <Link className="btn btn--primary" to="/publications/new">
            Add Publication
          </Link>
        </div>
      ) : null}

      {pubStatus === 'ready' && publications.length === 0 && search ? (
        <div className="empty-state">
          <p className="empty-state__title">No publications match your search.</p>
          <p className="empty-state__text">
            Try a different title, journal, conference or DOI.
          </p>
        </div>
      ) : null}

      {publications.length > 0 ? (
        <section className="panel doc-picker" aria-label="Select a publication">
          <div className="field">
            <label className="field__label" htmlFor="doc-pub-search">
              Find publication
            </label>
            <input
              id="doc-pub-search"
              className="field__input"
              type="search"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Search by title, journal, conference or DOI"
            />
          </div>

          <div className="field">
            <label className="field__label" htmlFor="doc-pub-select">
              Select Publication
            </label>
            <select
              id="doc-pub-select"
              className="field__input"
              value={selectedId}
              onChange={(event) => setSelectedId(event.target.value)}
            >
              {publications.map((item) => (
                <option key={item.publication_id} value={item.publication_id}>
                  {item.title}
                </option>
              ))}
            </select>
          </div>

          {total > publications.length ? (
            <p className="doc-picker__hint">
              Showing the {publications.length} most recent of {total} publications —
              refine your search to narrow down.
            </p>
          ) : null}
        </section>
      ) : null}

      {selected ? (
        <PublicationDocuments
          publicationId={selected.publication_id}
          heading="Documents for this publication"
          emptyMessage="No documents uploaded for this publication."
        />
      ) : null}
    </div>
  )
}
