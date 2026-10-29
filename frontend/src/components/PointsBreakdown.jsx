import { Link } from 'react-router-dom'
import { formatDate, typeLabel } from '../utils/publication'
import { categoryEntries } from '../utils/points'

export default function PointsBreakdown({
  status,
  errorMessage,
  categoryPoints,
  items,
  yearName,
  onRetry,
}) {
  const categories = categoryEntries(categoryPoints)
  const rows = Array.isArray(items) ? items : []

  return (
    <>
      <section className="panel" aria-labelledby="points-categories-heading">
        <h2 className="panel__title" id="points-categories-heading">
          Category breakdown
        </h2>
        <p className="panel__empty panel__empty--flush">
          Point totals by category for {yearName}, as awarded by the backend
          points engine.
        </p>
        <ul className="points-categories">
          {categories.map((category) => (
            <li className="points-categories__item" key={category.key}>
              <span className="points-categories__label">{category.label}</span>
              <span className="points-categories__value">{category.points}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="panel" aria-labelledby="points-table-heading">
        <div className="points-table__head">
          <h2 className="panel__title" id="points-table-heading">
            Publication points
          </h2>
          <p className="points-table__subtitle">{yearName}</p>
        </div>

        {status === 'loading' ? (
          <p className="panel__empty" role="status">
            Loading points…
          </p>
        ) : null}

        {status === 'error' ? (
          <div className="points-table__error">
            <p className="alert alert--danger" role="alert">
              {errorMessage}
            </p>
            <button type="button" className="btn btn--ghost" onClick={onRetry}>
              Try Again
            </button>
          </div>
        ) : null}

        {status === 'ready' && rows.length === 0 ? (
          <p className="panel__empty">
            No points have been recorded for this academic year.
          </p>
        ) : null}

        {status === 'ready' && rows.length > 0 ? (
          <>
            <div className="table-wrap">
              <table className="table points-table">
                <caption className="visually-hidden">
                  Verified publications and their points for {yearName}
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Publication</th>
                    <th scope="col">Type</th>
                    <th scope="col">Date</th>
                    <th scope="col">Rule</th>
                    <th scope="col" className="points-table__points-col">
                      Points
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((item) => (
                    <tr key={item.publication_id}>
                      <td className="table__title">
                        <Link
                          className="pub-table__title-link"
                          to={`/publications/${item.publication_id}`}
                        >
                          {item.title || 'Untitled publication'}
                        </Link>
                        {item.points === 0 && item.reason ? (
                          <span className="points-table__note">
                            {item.reason}
                          </span>
                        ) : null}
                      </td>
                      <td>{typeLabel(item.publication_type)}</td>
                      <td>{formatDate(item.publication_date) || '—'}</td>
                      <td>{item.rule_name || item.rule_code || '—'}</td>
                      <td className="points-table__points">
                        {item.points ?? 0}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="points-table__note-block">
              Only verified publications contribute to awarded points.
              Pending and rejected publications are not listed until they are
              verified. Points are determined by institutional rules
              configured in the system.
            </p>
          </>
        ) : null}
      </section>
    </>
  )
}
