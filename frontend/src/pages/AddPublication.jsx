import { Link, useNavigate } from 'react-router-dom'
import PublicationForm from '../components/PublicationForm'
import { createPublication } from '../services/publicationService'

export default function AddPublication() {
  const navigate = useNavigate()

  async function handleSubmit(payload) {
    await createPublication(payload)
    navigate('/publications', {
      replace: true,
      state: { notice: 'Publication added. It is pending verification.' },
    })
  }

  return (
    <div className="page">
      <div className="page__header">
        <div>
          <h1 className="page__title">Add Publication</h1>
          <p className="page__subtitle">
            New publications are saved as Pending until an administrator verifies them.
          </p>
        </div>
        <Link className="btn btn--ghost" to="/publications">
          Back to Publications
        </Link>
      </div>

      <section className="panel" aria-label="Add publication form">
        <PublicationForm submitLabel="Add Publication" onSubmit={handleSubmit} />
      </section>
    </div>
  )
}
