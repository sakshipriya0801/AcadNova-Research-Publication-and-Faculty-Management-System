import { useCallback, useEffect, useState } from 'react'
import ConfirmDialog from '../../components/ConfirmDialog'
import LoadingScreen from '../../components/LoadingScreen'
import { useAuth } from '../../hooks/useAuth'
import {
  createAdminAccount,
  createInvitation,
  listAdminAccounts,
  listInvitations,
  revokeInvitation,
} from '../../services/adminService'
import { getAdminError } from '../../utils/admin'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function validate({ name, email, password }) {
  const errors = {}
  if (!email.trim()) errors.email = 'Email is required.'
  else if (!EMAIL_PATTERN.test(email.trim())) errors.email = 'Enter a valid email address.'
  if (!password) errors.password = 'A temporary password is required.'
  else if (password.length < 8) errors.password = 'Use at least 8 characters.'
  else if (!/[A-Za-z]/.test(password)) errors.password = 'Include at least one letter.'
  else if (!/[0-9]/.test(password)) errors.password = 'Include at least one number.'
  return { errors, name }
}

function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

const INVITATION_STATUS_LABELS = {
  pending: 'Pending',
  used: 'Used',
  revoked: 'Revoked',
  expired: 'Expired',
}

function InvitationsPanel() {
  const [invitations, setInvitations] = useState([])
  const [listState, setListState] = useState('loading')
  const [listError, setListError] = useState('')

  const [email, setEmail] = useState('')
  const [expiryHours, setExpiryHours] = useState('72')
  const [formError, setFormError] = useState('')
  const [success, setSuccess] = useState('')
  const [inviteLink, setInviteLink] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [copied, setCopied] = useState(false)

  const load = useCallback(() => {
    setListState('loading')
    setListError('')
    listInvitations()
      .then((response) => {
        setInvitations(response.data?.items || [])
        setListState('ready')
      })
      .catch((error) => {
        setListError(getAdminError(error))
        setListState('error')
      })
  }, [])

  useEffect(() => {
    load()
  }, [load])

  function handleGenerate(event) {
    event.preventDefault()
    setSuccess('')
    setFormError('')
    setCopied(false)
    const trimmed = email.trim()
    if (!trimmed || !EMAIL_PATTERN.test(trimmed)) {
      setFormError('Enter a valid email address for the invitation.')
      return
    }
    setSubmitting(true)
    createInvitation({ email: trimmed, expires_in_hours: Number(expiryHours) || 72 })
      .then((response) => {
        const token = response.data.token
        const link = `${window.location.origin}/admin/register?token=${token}`
        setInviteLink(link)
        setSuccess(`Invitation created for ${response.data.email}.`)
        setEmail('')
        load()
      })
      .catch((error) => setFormError(getAdminError(error)))
      .finally(() => setSubmitting(false))
  }

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(inviteLink)
      setCopied(true)
    } catch {
      setCopied(false)
    }
  }

  function handleRevoke(invitation) {
    setListError('')
    revokeInvitation(invitation.invitation_id)
      .then(() => load())
      .catch((error) => setListError(getAdminError(error)))
  }

  return (
    <section className="panel" aria-label="Administrator invitations">
      <h2 className="panel__title">Invitations</h2>
      <p className="admin-form__hint">
        Generate a single-use invitation link for a new administrator. The link
        expires and can only be used once.
      </p>

      {success ? (
        <p className="alert alert--success" role="status">
          {success}
        </p>
      ) : null}
      {formError ? (
        <p className="alert alert--danger" role="alert">
          {formError}
        </p>
      ) : null}

      <form className="admin-form" onSubmit={handleGenerate} noValidate>
        <div className="admin-form__grid">
          <div className="field">
            <label className="field__label" htmlFor="inv-email">
              Invitee email
            </label>
            <input
              id="inv-email"
              className="field__input"
              type="email"
              autoComplete="off"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              disabled={submitting}
            />
          </div>
          <div className="field">
            <label className="field__label" htmlFor="inv-expiry">
              Expires in (hours)
            </label>
            <input
              id="inv-expiry"
              className="field__input"
              type="number"
              min="1"
              max="168"
              value={expiryHours}
              onChange={(event) => setExpiryHours(event.target.value)}
              disabled={submitting}
            />
          </div>
        </div>
        <div className="admin-form__actions">
          <button type="submit" className="btn btn--primary" disabled={submitting}>
            {submitting ? 'Generating…' : 'Generate invitation'}
          </button>
        </div>
      </form>

      {inviteLink ? (
        <div className="field">
          <label className="field__label" htmlFor="inv-link">
            Invitation link (share with the invitee)
          </label>
          <div className="field__input-group">
            <input
              id="inv-link"
              className="field__input"
              type="text"
              readOnly
              value={inviteLink}
              onFocus={(event) => event.target.select()}
            />
            <button type="button" className="field__toggle" onClick={handleCopy}>
              {copied ? 'Copied' : 'Copy link'}
            </button>
          </div>
        </div>
      ) : null}

      {listState === 'loading' ? (
        <LoadingScreen message="Loading invitations…" />
      ) : null}

      {listState === 'error' ? (
        <p className="alert alert--danger" role="alert">
          {listError}
        </p>
      ) : null}

      {listState === 'ready' && invitations.length === 0 ? (
        <p className="panel__empty">No invitations have been created yet.</p>
      ) : null}

      {invitations.length > 0 ? (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Email</th>
                <th scope="col">Status</th>
                <th scope="col">Expires</th>
                <th scope="col">Created</th>
                <th scope="col">Actions</th>
              </tr>
            </thead>
            <tbody>
              {invitations.map((invitation) => (
                <tr key={invitation.invitation_id}>
                  <td>{invitation.email}</td>
                  <td>
                    <span
                      className={`admin-status admin-status--${
                        invitation.status === 'pending' ? 'pending' : 'rejected'
                      }`}
                    >
                      {INVITATION_STATUS_LABELS[invitation.status] || invitation.status}
                    </span>
                  </td>
                  <td>{formatDate(invitation.expires_at)}</td>
                  <td>{formatDate(invitation.created_at)}</td>
                  <td>
                    {invitation.status === 'pending' ? (
                      <button
                        type="button"
                        className="btn btn--small btn--danger-outline"
                        onClick={() => handleRevoke(invitation)}
                      >
                        Revoke
                      </button>
                    ) : (
                      <span className="admin-form__hint">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  )
}

export default function AdminAccountsPage() {
  const { user } = useAuth()
  const [accounts, setAccounts] = useState([])
  const [listState, setListState] = useState('loading')
  const [listError, setListError] = useState('')

  const [form, setForm] = useState({ name: '', email: '', password: '' })
  const [errors, setErrors] = useState({})
  const [showPassword, setShowPassword] = useState(false)
  const [formError, setFormError] = useState('')
  const [success, setSuccess] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)

  const load = useCallback(() => {
    setListState('loading')
    setListError('')
    listAdminAccounts()
      .then((response) => {
        setAccounts(response.data?.items || [])
        setListState('ready')
      })
      .catch((error) => {
        setListError(getAdminError(error))
        setListState('error')
      })
  }, [])

  useEffect(() => {
    load()
  }, [load])

  function updateField(field) {
    return (event) => {
      setForm((current) => ({ ...current, [field]: event.target.value }))
      setErrors((current) => ({ ...current, [field]: undefined }))
    }
  }

  function requestCreate(event) {
    event.preventDefault()
    setSuccess('')
    setFormError('')
    const { errors: nextErrors } = validate(form)
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return
    setConfirmOpen(true)
  }

  function confirmCreate() {
    if (submitting) return
    setSubmitting(true)
    setFormError('')
    createAdminAccount({
      name: form.name.trim() || undefined,
      email: form.email.trim(),
      password: form.password,
    })
      .then((response) => {
        setConfirmOpen(false)
        setSuccess(`Administrator ${response.data.email} was created.`)
        setForm({ name: '', email: '', password: '' })
        load()
      })
      .catch((error) => {
        setConfirmOpen(false)
        setFormError(getAdminError(error))
      })
      .finally(() => setSubmitting(false))
  }

  return (
    <div className="page admin-page">
      <div className="page__header">
        <div>
          <h1 className="page__title">Admin Accounts</h1>
          <p className="page__subtitle">
            Manage administrator access to the management portal.
          </p>
        </div>
      </div>

      <div className="alert alert--warning" role="note">
        Administrator accounts are provisioned here by an existing administrator.
        There is no public admin registration. New administrators sign in at the
        unified login page using the <strong>Admin Login</strong> tab with the
        temporary password set below, and should change it with the institution.
      </div>

      <section className="panel" aria-label="Create administrator">
        <h2 className="panel__title">Create an administrator</h2>

        {success ? (
          <p className="alert alert--success" role="status">
            {success}
          </p>
        ) : null}
        {formError ? (
          <p className="alert alert--danger" role="alert">
            {formError}
          </p>
        ) : null}

        <form className="admin-form" onSubmit={requestCreate} noValidate>
          <div className="admin-form__grid">
            <div className="field">
              <label className="field__label" htmlFor="admin-name">
                Full name (optional)
              </label>
              <input
                id="admin-name"
                className="field__input"
                type="text"
                autoComplete="name"
                value={form.name}
                onChange={updateField('name')}
                disabled={submitting}
              />
            </div>

            <div className="field">
              <label className="field__label" htmlFor="admin-email">
                Email
              </label>
              <input
                id="admin-email"
                className="field__input"
                type="email"
                autoComplete="off"
                value={form.email}
                onChange={updateField('email')}
                aria-invalid={Boolean(errors.email)}
                aria-describedby={errors.email ? 'admin-email-error' : undefined}
                disabled={submitting}
              />
              {errors.email ? (
                <p className="field__error" id="admin-email-error">
                  {errors.email}
                </p>
              ) : null}
            </div>

            <div className="field field--full">
              <label className="field__label" htmlFor="admin-password">
                Temporary password
              </label>
              <div className="field__input-group">
                <input
                  id="admin-password"
                  className="field__input"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  value={form.password}
                  onChange={updateField('password')}
                  aria-invalid={Boolean(errors.password)}
                  aria-describedby={errors.password ? 'admin-password-error' : 'admin-password-hint'}
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
                <p className="field__error" id="admin-password-error">
                  {errors.password}
                </p>
              ) : (
                <p className="field__hint" id="admin-password-hint">
                  At least 8 characters, including a letter and a number. The
                  password is hashed before storage and never shown again.
                </p>
              )}
            </div>
          </div>

          <div className="admin-form__actions">
            <button type="submit" className="btn btn--primary" disabled={submitting}>
              {submitting ? 'Creating…' : 'Create administrator'}
            </button>
          </div>
        </form>
      </section>

      <section className="panel" aria-label="Administrator accounts">
        <h2 className="panel__title">Administrator accounts</h2>

        {listState === 'loading' ? (
          <LoadingScreen message="Loading administrators…" />
        ) : null}

        {listState === 'error' ? (
          <p className="alert alert--danger" role="alert">
            {listError}
          </p>
        ) : null}

        {listState === 'ready' && accounts.length === 0 ? (
          <p className="panel__empty">No administrator accounts found.</p>
        ) : null}

        {accounts.length > 0 ? (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">Email</th>
                  <th scope="col">Name</th>
                  <th scope="col">Status</th>
                  <th scope="col">Created</th>
                </tr>
              </thead>
              <tbody>
                {accounts.map((account) => (
                  <tr key={account.user_id}>
                    <td>
                      {account.email}
                      {account.user_id === user?.user_id ? (
                        <span className="admin-badge admin-badge--current"> You</span>
                      ) : null}
                    </td>
                    <td>{account.name || '—'}</td>
                    <td>
                      <span
                        className={`admin-badge admin-badge--${
                          account.is_active ? 'active' : 'inactive'
                        }`}
                      >
                        {account.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td>{formatDate(account.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <InvitationsPanel />

      <ConfirmDialog
        open={confirmOpen}
        title="Create administrator"
        message={`Create an administrator account for ${form.email.trim()}?`}
        confirmLabel="Create"
        confirmVariant="primary"
        busy={submitting}
        error={formError}
        onConfirm={confirmCreate}
        onCancel={() => {
          if (!submitting) setConfirmOpen(false)
        }}
      />
    </div>
  )
}
