import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import LoadingScreen from '../components/LoadingScreen'
import PublicationForm from '../components/PublicationForm'
import { getPublication, updatePublication } from '../services/publicationService'
import { getPublicationError } from '../utils/errors'

export default function EditPublication() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [publication, setPublication] = useState(null)
  const [status, setStatus] = useState('loading')
  const [errorMessage, setErrorMessage] = useState('')

  useEffect(() => {
    let cancelled = false
    setStatus('loading')
    getPublication(id)
      .then((response) => {
        if (cancelled) return
        setPublication(response.data)
        setStatus('ready')
      })
      .catch((error) => {
        if (cancelled) return
        setErrorMessage(getPublicationError(error))
        setStatus('error')
      })
    return () => {
      cancelled = true
    }
  }, [id])

  async function handleSubmit(payload) {
    await updatePublication(id, payload)
    navigate(`/publications/${id}`, {
      replace: true,
      state: { notice: 'Publication updated.' },
    })
  }

  if (status === 'loading') {
    return <LoadingScreen message="Loading publication…" />
  }

  if (status === 'error') {
    return (
      <div className="page">
        <div className="page__header">
          <h1 className="page__title">Edit Publication</h1>
          <Link className="btn btn--ghost" to="/publications">
            Back to Publications
          </Link>
        </div>
        <div className="empty-state">
          <p className="empty-state__title">Unable to open this publication</p>
          <p className="empty-state__text">{errorMessage}</p>
          <Link className="btn btn--primary" to="/publications">
            Back to Publications
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="page">
      <div className="page__header">
        <div>
          <h1 className="page__title">Edit Publication</h1>
          <p className="page__subtitle">
            Verification status, awarded points and source are managed by the system
            and cannot be edited here.
          </p>
        </div>
        <Link className="btn btn--ghost" to={`/publications/${id}`}>
          Cancel
        </Link>
      </div>

      <section className="panel" aria-label="Edit publication form">
        <PublicationForm
          key={id}
          publication={publication}
          submitLabel="Save changes"
          onSubmit={handleSubmit}
        />
      </section>
    </div>
  )
}
