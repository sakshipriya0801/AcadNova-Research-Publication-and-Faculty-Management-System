import { useEffect, useRef } from 'react'

export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Delete',
  cancelLabel = 'Cancel',
  confirmVariant = 'danger',
  busy = false,
  error = '',
  onConfirm,
  onCancel,
}) {
  const cancelRef = useRef(null)
  const dialogRef = useRef(null)

  useEffect(() => {
    if (!open) return undefined
    cancelRef.current?.focus()

    function onKeyDown(event) {
      if (event.key === 'Escape' && !busy) {
        event.stopPropagation()
        onCancel()
        return
      }
      if (event.key === 'Tab' && dialogRef.current) {
        const focusable = dialogRef.current.querySelectorAll('button:not([disabled])')
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

  return (
    <div className="dialog-backdrop" onMouseDown={busy ? undefined : onCancel}>
      <div
        className="dialog"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-message"
        ref={dialogRef}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <h2 className="dialog__title" id="confirm-dialog-title">
          {title}
        </h2>
        <p className="dialog__message" id="confirm-dialog-message">
          {message}
        </p>
        {error ? (
          <p className="alert alert--danger" role="alert">
            {error}
          </p>
        ) : null}
        <div className="dialog__actions">
          <button
            type="button"
            className="btn btn--ghost"
            onClick={onCancel}
            disabled={busy}
            ref={cancelRef}
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            className={`btn btn--${confirmVariant === 'primary' ? 'primary' : 'danger'}`}
            onClick={onConfirm}
            disabled={busy}
          >
            {busy ? 'Working…' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
