import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { getRegisterError } from '../utils/errors'
import {
  DEPARTMENT_PROGRAMS,
  DESIGNATION_OPTIONS,
  validateFacultyProfile,
} from '../utils/facultyOptions'

function validatePassword({ password, confirmPassword }) {
  const errors = {}
  if (!password) errors.password = 'Password is required.'
  else if (password.length < 8) errors.password = 'Use at least 8 characters.'
  else if (!/[A-Za-z]/.test(password)) errors.password = 'Include at least one letter.'
  else if (!/[0-9]/.test(password)) errors.password = 'Include at least one number.'

  if (!confirmPassword) errors.confirmPassword = 'Please confirm your password.'
  else if (confirmPassword !== password) errors.confirmPassword = 'Passwords do not match.'
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

export default function Register() {
  const { register, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState({
    name: '',
    email: '',
    employee_id: '',
    department: '',
    designation: '',
    password: '',
    confirmPassword: '',
  })
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  if (isAuthenticated) return <Navigate to="/dashboard" replace />

  function updateField(field) {
    return (event) => {
      setForm((current) => ({ ...current, [field]: event.target.value }))
      setErrors((current) => ({ ...current, [field]: undefined }))
    }
  }

  async function handleSubmit(event) {
    event.preventDefault()
    const nextErrors = {
      ...validateFacultyProfile({
        name: form.name,
        email: form.email,
        department: form.department,
        designation: form.designation,
      }),
      ...validatePassword({ password: form.password, confirmPassword: form.confirmPassword }),
    }
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return

    setSubmitting(true)
    setFormError('')
    try {
      const account = await register({
        name: form.name.trim(),
        email: form.email.trim(),
        employee_id: form.employee_id.trim() || null,
        department_id: form.department,
        designation: form.designation,
        password: form.password,
      })
      const pending = account?.approval_status === 'pending'
      navigate('/login', {
        replace: true,
        state: {
          message: pending
            ? 'Your account has been created and is awaiting administrator approval.'
            : 'Your account has been created. Please sign in.',
        },
      })
    } catch (error) {
      setFormError(getRegisterError(error))
    } finally {
      setSubmitting(false)
    }
  }

  const strength = passwordStrength(form.password)

  return (
    <div className="auth-form">
      <p className="auth-form__eyebrow">Faculty Registration</p>
      <h1 className="auth-form__title">Create your account</h1>
      <p className="auth-form__subtitle">
        Set up your personal research performance account.
      </p>

      {formError ? (
        <p className="alert alert--danger" role="alert">
          {formError}
        </p>
      ) : null}

      <form onSubmit={handleSubmit} noValidate>
        <div className="field">
          <label className="field__label" htmlFor="register-name">
            Full Name
          </label>
          <input
            id="register-name"
            className="field__input"
            type="text"
            autoComplete="name"
            placeholder="e.g. Dr. A. Sharma"
            value={form.name}
            onChange={updateField('name')}
            aria-invalid={Boolean(errors.name)}
            aria-describedby={errors.name ? 'register-name-error' : undefined}
            disabled={submitting}
          />
          {errors.name ? (
            <p className="field__error" id="register-name-error">
              {errors.name}
            </p>
          ) : null}
        </div>

        <div className="field">
          <label className="field__label" htmlFor="register-email">
            Email Address
          </label>
          <input
            id="register-email"
            className="field__input"
            type="email"
            autoComplete="email"
            placeholder="name@institution.edu"
            value={form.email}
            onChange={updateField('email')}
            aria-invalid={Boolean(errors.email)}
            aria-describedby={errors.email ? 'register-email-error' : undefined}
            disabled={submitting}
          />
          {errors.email ? (
            <p className="field__error" id="register-email-error">
              {errors.email}
            </p>
          ) : null}
        </div>

        <div className="field">
          <label className="field__label" htmlFor="register-employee">
            Employee ID (optional)
          </label>
          <input
            id="register-employee"
            className="field__input"
            type="text"
            autoComplete="off"
            value={form.employee_id}
            onChange={updateField('employee_id')}
            disabled={submitting}
          />
        </div>

        <div className="field">
          <label className="field__label" htmlFor="register-department">
            Department
          </label>
          <select
            id="register-department"
            className="field__input"
            value={form.department}
            onChange={updateField('department')}
            aria-invalid={Boolean(errors.department)}
            aria-describedby={errors.department ? 'register-department-error' : undefined}
            disabled={submitting}
          >
            <option value="">Select department</option>
            {DEPARTMENT_PROGRAMS.map((program) => (
              <option key={program} value={program}>
                {program}
              </option>
            ))}
          </select>
          {errors.department ? (
            <p className="field__error" id="register-department-error">
              {errors.department}
            </p>
          ) : null}
        </div>

        <div className="field">
          <label className="field__label" htmlFor="register-designation">
            Designation
          </label>
          <select
            id="register-designation"
            className="field__input"
            value={form.designation}
            onChange={updateField('designation')}
            aria-invalid={Boolean(errors.designation)}
            aria-describedby={errors.designation ? 'register-designation-error' : undefined}
            disabled={submitting}
          >
            <option value="">Select designation</option>
            {DESIGNATION_OPTIONS.map((designation) => (
              <option key={designation} value={designation}>
                {designation}
              </option>
            ))}
          </select>
          {errors.designation ? (
            <p className="field__error" id="register-designation-error">
              {errors.designation}
            </p>
          ) : null}
        </div>

        <div className="field">
          <label className="field__label" htmlFor="register-password">
            Password
          </label>
          <div className="field__input-group">
            <input
              id="register-password"
              className="field__input"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              value={form.password}
              onChange={updateField('password')}
              aria-invalid={Boolean(errors.password)}
              aria-describedby={
                errors.password ? 'register-password-error' : 'register-password-hint'
              }
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
            <p className="field__error" id="register-password-error">
              {errors.password}
            </p>
          ) : (
            <p className="field__hint" id="register-password-hint">
              At least 8 characters, including a letter and a number.
            </p>
          )}
        </div>

        <div className="field">
          <label className="field__label" htmlFor="register-confirm">
            Confirm password
          </label>
          <div className="field__input-group">
            <input
              id="register-confirm"
              className="field__input"
              type={showConfirm ? 'text' : 'password'}
              autoComplete="new-password"
              value={form.confirmPassword}
              onChange={updateField('confirmPassword')}
              aria-invalid={Boolean(errors.confirmPassword)}
              aria-describedby={
                errors.confirmPassword ? 'register-confirm-error' : undefined
              }
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
            <p className="field__error" id="register-confirm-error">
              {errors.confirmPassword}
            </p>
          ) : null}
        </div>

        <button type="submit" className="btn btn--primary btn--block" disabled={submitting}>
          {submitting ? 'Creating account…' : 'Create account'}
        </button>
      </form>

      <p className="auth-form__alt">
        Already have an account? <Link to="/login">Sign in</Link>
      </p>
    </div>
  )
}
