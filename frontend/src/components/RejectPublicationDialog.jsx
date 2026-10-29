import { useEffect, useRef, useState } from 'react'
import { REASON_REQUIRED_MESSAGE, validateReason } from '../utils/verification'

export default function RejectPublicationDialog({
  open,
  message = 'Provide a reason for rejecting this publication. The faculty member will see this reason.',
  busy = false,
  error = '',
  onConfirm,
  onCancel,
}) {
  const [reason, setReason] = useState('')
  const [localError, setLocalError] = useState('')
  const textareaRef = useRef(null)
  const dialogRef = useRef(null)

  useEffect(() => {
    if (!open) return undefined
    setReason('')
    setLocalError('')
    textareaRef.current?.focus()

    function onKeyDown(event) {
      if (event.key === 'Escape' && !busy) {
        event.stopPropagation()
        onCancel()
        return
      }
      if (event.key === 'Tab' && dialogRef.current) {
        const focusable = dialogRef.current.querySelectorAll(
          'button:not([disabled]), textarea:not([disabled])',
        )
        if (focusable.length === 0) return
        const first = focusable[0]
        const last = focusable[focusable.length - 1]
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault()
          last.focus()
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault()
          first.focus()
        }
      }
    }

    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [open, busy, onCancel])

  if (!open) return null

  function handleConfirm() {
    const trimmed = validateReason(reason)
    if (!trimmed) {
      setLocalError(REASON_REQUIRED_MESSAGE)
      return
    }
    setLocalError('')
    onConfirm(trimmed)
  }

  const displayedError = localError || error

  return (
    <div className="dialog-backdrop" onMouseDown={busy ? undefined : onCancel}>
      <div
        className="dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="reject-dialog-title"
        aria-describedby="reject-dialog-message"
        ref={dialogRef}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <h2 className="dialog__title" id="reject-dialog-title">
          Reject publication
        </h2>
        <p className="dialog__message" id="reject-dialog-message">
          {message}
        </p>
        <div className="field">
          <label className="field__label" htmlFor="reject-reason">
            Reason <span aria-hidden="true">*</span>
          </label>
          <textarea
            id="reject-reason"
            className="field__input field__input--textarea review-reject__textarea"
            rows={4}
            value={reason}
            disabled={busy}
            aria-required="true"
            aria-invalid={displayedError ? 'true' : undefined}
            onChange={(event) => {
              setReason(event.target.value)
              if (localError) setLocalError('')
            }}
          />
        </div>
        {displayedError ? (
          <p className="alert alert--danger" role="alert">
            {displayedError}
          </p>
        ) : null}
        <div className="dialog__actions">
          <button
            type="button"
            className="btn btn--ghost"
            onClick={onCancel}
            disabled={busy}
          >
            Cancel
          </button>
          <button
            type="button"
            className="btn btn--danger"
            onClick={handleConfirm}
            disabled={busy}
          >
            {busy ? 'Rejecting…' : 'Reject publication'}
          </button>
        </div>
      </div>
    </div>
  )
}
