import { useCallback, useEffect, useId, useRef, useState } from 'react'
import {
  getAdminVerificationHistory,
  getVerificationHistory,
} from '../services/verificationService'
import {
  formatRecordDate,
  getVerificationError,
  recordActionLabel,
  recordActionSymbol,
  recordTransition,
} from '../utils/verification'

export default function VerificationHistory({
  publicationId,
  variant = 'faculty',
  heading = 'Verification history',
  emptyMessage = 'No verification activity yet.',
  onLoaded,
}) {
  const headingId = useId()
  const [records, setRecords] = useState([])
  const [status, setStatus] = useState('loading')
  const [errorMessage, setErrorMessage] = useState('')
  const onLoadedRef = useRef(onLoaded)

  useEffect(() => {
    onLoadedRef.current = onLoaded
  }, [onLoaded])

  const load = useCallback(() => {
    setStatus('loading')
    const fetcher =
      variant === 'admin' ? getAdminVerificationHistory : getVerificationHistory
    return fetcher(publicationId)
      .then((response) => {
        const items = response.data || []
        setRecords(items)
        setErrorMessage('')
        setStatus('ready')
        if (onLoadedRef.current) onLoadedRef.current(items)
      })
      .catch((error) => {
        setErrorMessage(
          getVerificationError(
            error,
            'Unable to load verification history.',
          ),
        )
        setStatus('error')
      })
  }, [publicationId, variant])

  useEffect(() => {
    load()
  }, [load])

  return (
    <section className="panel" aria-labelledby={headingId}>
      <h2 className="panel__title" id={headingId}>
        {heading}
      </h2>

      {status === 'loading' ? (
        <p className="panel__empty" role="status">
          Loading verification history…
        </p>
      ) : null}

      {status === 'error' ? (
        <div className="vhistory__error">
          <p className="alert alert--danger" role="alert">
            {errorMessage}
          </p>
          <button type="button" className="btn btn--ghost" onClick={load}>
            Try Again
          </button>
        </div>
      ) : null}

      {status === 'ready' && records.length === 0 ? (
        <p className="panel__empty">{emptyMessage}</p>
      ) : null}

      {status === 'ready' && records.length > 0 ? (
        <ol className="vhistory">
          {records.map((record) => (
            <li className="vhistory__item" key={record.id}>
              <div className="vhistory__head">
                <span
                  className={`vhistory__action vhistory__action--${
                    record.action || 'other'
                  }`}
                >
                  <span aria-hidden="true">{recordActionSymbol(record)}</span>{' '}
                  {recordActionLabel(record)}
                </span>
                <span className="vhistory__date">
                  {formatRecordDate(record.created_at)}
                </span>
              </div>
              <p className="vhistory__transition">
                {recordTransition(record)}
              </p>
              {record.reason ? (
                <p className="vhistory__reason">Reason: {record.reason}</p>
              ) : null}
              {record.notes ? (
                <p className="vhistory__notes">Notes: {record.notes}</p>
              ) : null}
            </li>
          ))}
        </ol>
      ) : null}
    </section>
  )
}
