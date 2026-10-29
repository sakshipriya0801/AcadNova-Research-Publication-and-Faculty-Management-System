import { useState } from 'react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { registerAdmin } from '../../services/authService'
import { getErrorMessage } from '../../utils/errors'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function validate({ name, email, password, confirmPassword }) {
  const next = {}
  if (!name.trim()) next.name = 'Name is required.'
  if (!email.trim()) next.email = 'Email is required.'
  else if (!EMAIL_PATTERN.test(email.trim())) next.email = 'Enter a valid email address.'
  if (!password) next.password = 'Password is required.'
  else if (password.length < 8) next.password = 'Use at least 8 characters.'
  else if (!/[A-Za-z]/.test(password)) next.password = 'Include at least one letter.'
  else if (!/[0-9]/.test(password)) next.password = 'Include at least one number.'
  if (!confirmPassword) next.confirmPassword = 'Please confirm your password.'
  else if (confirmPassword !== password) next.confirmPassword = 'Passwords do not match.'
  return next
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

export default function AdminRegisterPage() {
  const { isAuthenticated, user } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = (searchParams.get('token') || '').trim()

  const [form, setForm] = useState({ name: '', email: '', password: '', confirmPassword: '' })
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  if (isAuthenticated) {
    return (
      <Navigate
        to={user?.role === 'admin' ? '/admin/dashboard' : '/dashboard'}
        replace
      />
    )
  }

  function updateField(field) {
    return (event) => {
      setForm((current) => ({ ...current, [field]: event.target.value }))
      setErrors((current) => ({ ...current, [field]: undefined }))
    }
  }

  async function handleSubmit(event) {
    event.preventDefault()
    const nextErrors = validate(form)
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return

    setSubmitting(true)
    setFormError('')
    try {
      await registerAdmin({
        token,
        name: form.name.trim(),
        email: form.email.trim(),
        password: form.password,
      })
      navigate('/login?role=admin', {
        replace: true,
        state: {
          message: 'Administrator account created. Please sign in with your new credentials.',
        },
      })
    } catch (error) {
      setFormError(getErrorMessage(error, 'Unable to complete administrator registration.'))
    } finally {
      setSubmitting(false)
    }
  }

  const strength = passwordStrength(form.password)

  if (!token) {
    return (
      <div className="auth-form">
        <p className="auth-form__eyebrow">Administrator Portal</p>
        <h1 className="auth-form__title">Invitation required</h1>
        <p className="auth-form__subtitle">
          Administrator registration is invitation-only. An existing administrator
          must generate an invitation link for you. Public administrator
          registration is not available.
        </p>
        <Link className="btn btn--primary btn--block" to="/login?role=admin">
          Back to Admin Login
        </Link>
      </div>
    )
  }

  return (
    <div className="auth-form">
      <p className="auth-form__eyebrow">Administrator Portal</p>
      <h1 className="auth-form__title">Create administrator account</h1>
      <p className="auth-form__subtitle">
        You were invited to join the management portal. Complete your details to
        activate your administrator account.
      </p>

      {formError ? (
        <p className="alert alert--danger" role="alert">
          {formError}
        </p>
      ) : null}

      <form onSubmit={handleSubmit} noValidate>
        <div className="field">
          <label className="field__label" htmlFor="ar-name">
            Full name
          </label>
          <input
            id="ar-name"
            className="field__input"
            type="text"
            autoComplete="name"
            value={form.name}
            onChange={updateField('name')}
            aria-invalid={Boolean(errors.name)}
            aria-describedby={errors.name ? 'ar-name-error' : undefined}
            disabled={submitting}
          />
          {errors.name ? (
            <p className="field__error" id="ar-name-error">
              {errors.name}
            </p>
          ) : null}
        </div>

        <div className="field">
          <label className="field__label" htmlFor="ar-email">
            Invited email address
          </label>
          <input
            id="ar-email"
            className="field__input"
            type="email"
            autoComplete="email"
            value={form.email}
            onChange={updateField('email')}
            aria-invalid={Boolean(errors.email)}
            aria-describedby={errors.email ? 'ar-email-error' : undefined}
            disabled={submitting}
          />
          {errors.email ? (
            <p className="field__error" id="ar-email-error">
              {errors.email}
            </p>
          ) : (
            <p className="field__hint">
              Must match the email address your invitation was issued to.
            </p>
          )}
        </div>

        <div className="field">
          <label className="field__label" htmlFor="ar-password">
            Password
          </label>
          <div className="field__input-group">
            <input
              id="ar-password"
              className="field__input"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              value={form.password}
              onChange={updateField('password')}
              aria-invalid={Boolean(errors.password)}
              aria-describedby={errors.password ? 'ar-password-error' : 'ar-password-hint'}
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
          {form.password ? (
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
            <p className="field__error" id="ar-password-error">
              {errors.password}
            </p>
          ) : (
            <p className="field__hint" id="ar-password-hint">
              At least 8 characters, including a letter and a number.
            </p>
          )}
        </div>

        <div className="field">
          <label className="field__label" htmlFor="ar-confirm">
            Confirm password
          </label>
          <div className="field__input-group">
            <input
              id="ar-confirm"
              className="field__input"
              type={showConfirm ? 'text' : 'password'}
              autoComplete="new-password"
              value={form.confirmPassword}
              onChange={updateField('confirmPassword')}
              aria-invalid={Boolean(errors.confirmPassword)}
              aria-describedby={errors.confirmPassword ? 'ar-confirm-error' : undefined}
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
          {errors.confirmPassword ? (
            <p className="field__error" id="ar-confirm-error">
              {errors.confirmPassword}
            </p>
          ) : null}
        </div>

        <button type="submit" className="btn btn--primary btn--block" disabled={submitting}>
          {submitting ? 'Creating account…' : 'Create administrator account'}
        </button>
      </form>

      <p className="auth-form__alt">
        <Link to="/login?role=admin">Back to Admin Login</Link>
      </p>
    </div>
  )
}
