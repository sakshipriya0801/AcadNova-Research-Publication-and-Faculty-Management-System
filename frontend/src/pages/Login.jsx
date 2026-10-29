import { useEffect, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { getLoginError } from '../utils/errors'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function FacultyIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <path d="M3 9l9-5 9 5-9 5-9-5z" />
      <path d="M7 11.5V16c0 1.1 2.2 2 5 2s5-.9 5-2v-4.5" />
      <path d="M21 9v5" />
    </svg>
  )
}

function AdminIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <path d="M12 3l7 3v6c0 4.2-2.9 7.4-7 9-4.1-1.6-7-4.8-7-9V6l7-3z" />
      <path d="M9.5 12l1.8 1.8 3.4-3.6" />
    </svg>
  )
}

const COPY = {
  faculty: {
    title: 'Faculty sign in',
    subtitle: 'Access your publications, points and performance records.',
    eyebrow: 'Faculty Portal',
    button: 'Sign in to Faculty Portal',
  },
  admin: {
    title: 'Administrator sign in',
    subtitle: 'Manage faculty, publications, verification and institutional rules.',
    eyebrow: 'Administrator Portal',
    button: 'Sign in to Admin Console',
  },
}

export default function Login() {
  const { login, logout, isAuthenticated, user } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams, setSearchParams] = useSearchParams()

  const initialRole = searchParams.get('role') === 'admin' ? 'admin' : 'faculty'
  const [mode, setMode] = useState(initialRole)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [notice, setNotice] = useState(location.state?.message || '')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (searchParams.get('role') === 'admin') setMode('admin')
  }, [searchParams])

  if (isAuthenticated) {
    return (
      <Navigate
        to={user?.role === 'admin' ? '/admin/dashboard' : '/dashboard'}
        replace
      />
    )
  }

  function selectRole(next) {
    setMode(next)
    setErrors({})
    setFormError('')
    setSearchParams(next === 'admin' ? { role: 'admin' } : {}, { replace: true })
  }

  function validate() {
    const next = {}
    const trimmed = email.trim()
    if (!trimmed) next.email = 'Email is required.'
    else if (!EMAIL_PATTERN.test(trimmed)) next.email = 'Enter a valid email address.'
    if (!password) next.password = 'Password is required.'
    return next
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setNotice('')
    const nextErrors = validate()
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return

    setSubmitting(true)
    setFormError('')
    try {
      const currentUser = await login(email.trim(), password)
      if (mode === 'admin') {
        if (currentUser?.role !== 'admin') {
          logout()
          setFormError(
            'This portal is for administrators only. Please use the Faculty login.',
          )
          return
        }
        const from = location.state?.from?.pathname
        navigate(
          from && from.startsWith('/admin') ? from : '/admin/dashboard',
          { replace: true },
        )
        return
      }
      // Faculty option: role-aware redirect.
      if (currentUser?.role === 'admin') {
        navigate('/admin/dashboard', { replace: true })
        return
      }
      const home = currentUser?.must_change_password
        ? '/change-password'
        : '/dashboard'
      const from = location.state?.from?.pathname
      navigate(from && from !== '/login' ? from : home, { replace: true })
    } catch (error) {
      setFormError(getLoginError(error))
    } finally {
      setSubmitting(false)
    }
  }

  const copy = COPY[mode]

  return (
    <div className="auth-form">
      <div className="role-tabs" role="group" aria-label="Choose login type">
        <button
          type="button"
          className={`role-tab${mode === 'faculty' ? ' role-tab--active' : ''}`}
          aria-pressed={mode === 'faculty'}
          onClick={() => selectRole('faculty')}
        >
          <span className="role-tab__icon">
            <FacultyIcon />
          </span>
          Faculty Login
        </button>
        <button
          type="button"
          className={`role-tab${mode === 'admin' ? ' role-tab--active' : ''}`}
          aria-pressed={mode === 'admin'}
          onClick={() => selectRole('admin')}
        >
          <span className="role-tab__icon">
            <AdminIcon />
          </span>
          Admin Login
        </button>
      </div>

      <p className="auth-form__eyebrow">{copy.eyebrow}</p>
      <h1 className="auth-form__title">{copy.title}</h1>
      <p className="auth-form__subtitle">{copy.subtitle}</p>

      {notice ? (
        <p className="alert alert--success" role="status">
          {notice}
        </p>
      ) : null}
      {formError ? (
        <p className="alert alert--danger" role="alert">
          {formError}
        </p>
      ) : null}

      <form onSubmit={handleSubmit} noValidate>
        <div className="field">
          <label className="field__label" htmlFor="login-email">
            {mode === 'admin' ? 'Administrator email' : 'Email'}
          </label>
          <input
            id="login-email"
            className="field__input"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            aria-invalid={Boolean(errors.email)}
            aria-describedby={errors.email ? 'login-email-error' : undefined}
            disabled={submitting}
          />
          {errors.email ? (
            <p className="field__error" id="login-email-error">
              {errors.email}
            </p>
          ) : null}
        </div>

        <div className="field">
          <label className="field__label" htmlFor="login-password">
            Password
          </label>
          <div className="field__input-group">
            <input
              id="login-password"
              className="field__input"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              aria-invalid={Boolean(errors.password)}
              aria-describedby={errors.password ? 'login-password-error' : undefined}
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
          {errors.password ? (
            <p className="field__error" id="login-password-error">
              {errors.password}
            </p>
          ) : null}
        </div>

        <button type="submit" className="btn btn--primary btn--block" disabled={submitting}>
          {submitting ? 'Signing in…' : copy.button}
        </button>
      </form>

      {mode === 'faculty' ? (
        <p className="auth-form__alt">
          New faculty member? <Link to="/register">Create an account</Link>
        </p>
      ) : (
        <p className="auth-form__alt">
          Have an invitation?{' '}
          <Link to="/admin/register">Register as Administrator</Link>
        </p>
      )}
    </div>
  )
}
