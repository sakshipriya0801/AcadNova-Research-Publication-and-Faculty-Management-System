import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AcadNovaLogo from '../components/AcadNovaLogo'
import { useAuth } from '../hooks/useAuth'
import { getErrorMessage } from '../utils/errors'

function validate({ password, confirm }) {
  const errors = {}
  if (!password) errors.password = 'New password is required.'
  else if (password.length < 8) errors.password = 'Use at least 8 characters.'
  else if (!/[A-Za-z]/.test(password)) errors.password = 'Include at least one letter.'
  else if (!/[0-9]/.test(password)) errors.password = 'Include at least one number.'
  if (!confirm) errors.confirm = 'Please confirm your new password.'
  else if (confirm !== password) errors.confirm = 'Passwords do not match.'
  return errors
}

function passwordStrength(password) {
  if (!password) return { level: 0, label: '' }
  let score = 0
  if (password.length >= 8) score += 1
  if (/[A-Za-z]/.test(password) && /[0-9]/.test(password)) score += 1
  if (/[^A-Za-z0-9]/.test(password) || password.length >= 12) score += 1
  const labels = ['', 'Weak', 'Fair', 'Strong']
  const classes = ['', 'pw-strength--weak', 'pw-strength--fair', 'pw-strength--strong']
  return { level: score, label: labels[score], className: classes[score] }
}

export default function ChangePasswordPage() {
  const { changePassword, logout, user } = useAuth()
  const navigate = useNavigate()

  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    const nextErrors = validate({ password, confirm })
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return

    setSubmitting(true)
    setFormError('')
    try {
      await changePassword(password, confirm)
      navigate('/dashboard', { replace: true })
    } catch (error) {
      setFormError(getErrorMessage(error, 'Unable to change your password. Please try again.'))
    } finally {
      setSubmitting(false)
    }
  }

  const strength = passwordStrength(password)

  return (
    <div className="cp-page">
      <div className="auth-card">
        <div className="cp-brand">
          <AcadNovaLogo variant="full" size="lg" showTagline />
        </div>

        <p className="auth-form__eyebrow">Security</p>
        <h1 className="auth-form__title">Create a new password</h1>
        <p className="auth-form__subtitle">
          You are using a temporary password issued by an administrator. Set a
          permanent password to continue to your dashboard.
        </p>

        {formError ? (
          <p className="alert alert--danger" role="alert">
            {formError}
          </p>
        ) : null}

        <form onSubmit={handleSubmit} noValidate>
          <div className="field">
            <label className="field__label" htmlFor="cp-password">
              New password
            </label>
            <div className="field__input-group">
              <input
                id="cp-password"
                className="field__input"
                type={showPassword ? 'text' : 'password'}
                autoComplete="new-password"
                value={password}
                onChange={(event) => {
                  setPassword(event.target.value)
                  setErrors((current) => ({ ...current, password: undefined }))
                }}
                aria-invalid={Boolean(errors.password)}
                aria-describedby={errors.password ? 'cp-password-error' : 'cp-password-hint'}
                disabled={submitting}
              />
              <button
                type="button"
                className="field__toggle"
                onClick={() => setShowPassword((shown) => !shown)}
                aria-pressed={showPassword}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? 'Hide' : 'Show'}
              </button>
            </div>
            {password ? (
              <div className={`pw-strength ${strength.className || ''}`} aria-hidden="true">
                <span className="pw-strength__track">
                  <span className="pw-strength__seg" />
                  <span className="pw-strength__seg" />
                  <span className="pw-strength__seg" />
                </span>
                <span className="pw-strength__label">{strength.label}</span>
              </div>
            ) : null}
            {errors.password ? (
              <p className="field__error" id="cp-password-error">
                {errors.password}
              </p>
            ) : (
              <p className="field__hint" id="cp-password-hint">
                At least 8 characters, including a letter and a number.
              </p>
            )}
          </div>

          <div className="field">
            <label className="field__label" htmlFor="cp-confirm">
              Confirm new password
            </label>
            <div className="field__input-group">
              <input
                id="cp-confirm"
                className="field__input"
                type={showConfirm ? 'text' : 'password'}
                autoComplete="new-password"
                value={confirm}
                onChange={(event) => {
                  setConfirm(event.target.value)
                  setErrors((current) => ({ ...current, confirm: undefined }))
                }}
                aria-invalid={Boolean(errors.confirm)}
                aria-describedby={errors.confirm ? 'cp-confirm-error' : undefined}
                disabled={submitting}
              />
              <button
                type="button"
                className="field__toggle"
                onClick={() => setShowConfirm((shown) => !shown)}
                aria-pressed={showConfirm}
                aria-label={showConfirm ? 'Hide password' : 'Show password'}
              >
                {showConfirm ? 'Hide' : 'Show'}
              </button>
            </div>
            {errors.confirm ? (
              <p className="field__error" id="cp-confirm-error">
                {errors.confirm}
              </p>
            ) : null}
          </div>

          <button type="submit" className="btn btn--primary btn--block" disabled={submitting}>
            {submitting ? 'Saving…' : 'Save new password'}
          </button>
        </form>

        <p className="auth-form__alt">
          Signed in as {user?.email || 'faculty'}.{' '}
          <button
            type="button"
            className="btn btn--inline"
            onClick={() => {
              logout()
              navigate('/login', { replace: true })
            }}
          >
            Sign out
          </button>
        </p>
      </div>
    </div>
  )
}
