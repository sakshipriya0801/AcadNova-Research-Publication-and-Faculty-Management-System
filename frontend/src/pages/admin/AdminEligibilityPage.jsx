import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import ConfirmDialog from '../../components/ConfirmDialog'
import LoadingScreen from '../../components/LoadingScreen'
import {
  createEligibilityRule,
  listEligibilityRules,
  setEligibilityRuleStatus,
  updateEligibilityRule,
} from '../../services/adminService'
import { formatDesignation } from '../../utils/points'
import {
  ADMIN_EMPTY,
  ADMIN_PERMISSION_TEXT,
  ADMIN_PERMISSION_TITLE,
  getAdminError,
  isActiveLabel,
  rangeLabel,
} from '../../utils/admin'

const EMPTY_FORM = {
  designation: '',
  minimum_points: '0',
  effective_from: '',
  effective_to: '',
}

export default function AdminEligibilityPage() {
  const { user } = useAuth()
  const [rules, setRules] = useState([])
  const [status, setStatus] = useState('loading')
  const [errorMessage, setErrorMessage] = useState('')
  const [notice, setNotice] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  const [form, setForm] = useState(null)
  const [values, setValues] = useState(EMPTY_FORM)
  const [fieldErrors, setFieldErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  const [confirm, setConfirm] = useState(null)
  const [confirmBusy, setConfirmBusy] = useState(false)
  const [confirmError, setConfirmError] = useState('')

  const isAdmin = user?.role === 'admin'

  const load = useCallback(() => {
    if (!isAdmin) return
    setStatus('loading')
    listEligibilityRules()
      .then((response) => {
        const list = response.data || []
        setRules(list)
        setStatus(list.length === 0 ? 'empty' : 'ready')
      })
      .catch((error) => {
        setErrorMessage(
          getAdminError(error, 'Unable to load eligibility configurations.'),
        )
        setStatus('error')
      })
  }, [isAdmin, reloadKey])

  useEffect(() => {
    load()
  }, [load])

  const refetch = () => setReloadKey((key) => key + 1)

  const openCreate = () => {
    setValues(EMPTY_FORM)
    setFieldErrors({})
    setFormError('')
    setForm({ mode: 'create' })
  }

  const openEdit = (rule) => {
    setValues({
      designation: rule.designation || '',
      minimum_points: String(rule.minimum_points ?? 0),
      effective_from: rule.effective_from
        ? String(rule.effective_from).slice(0, 10)
        : '',
      effective_to: rule.effective_to
        ? String(rule.effective_to).slice(0, 10)
        : '',
    })
    setFieldErrors({})
    setFormError('')
    setForm({ mode: 'edit', id: rule.eligibility_rule_id, rule })
  }

  const validate = () => {
    const errors = {}
    if (!values.designation.trim()) errors.designation = 'Designation is required.'
    if (!/^\d+$/.test(String(values.minimum_points).trim())) {
      errors.minimum_points = 'Minimum points must be zero or a positive whole number.'
    }
    if (
      values.effective_from &&
      values.effective_to &&
      values.effective_from >= values.effective_to
    ) {
      errors.effective_to = 'Effective to must be after effective from.'
    }
    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  const buildPayload = () => ({
    designation: values.designation.trim(),
    minimum_points: Number(values.minimum_points),
    effective_from: values.effective_from || null,
    effective_to: values.effective_to || null,
  })

  const performSave = async () => {
    const payload = buildPayload()
    try {
      if (form.mode === 'create') {
        await createEligibilityRule(payload)
        setNotice('Eligibility configuration created.')
      } else {
        await updateEligibilityRule(form.id, payload)
        setNotice('Eligibility configuration updated.')
      }
      setForm(null)
      refetch()
    } catch (error) {
      setFormError(
        getAdminError(error, 'Unable to save the eligibility configuration.'),
      )
    }
  }

  const saveForm = async () => {
    if (!validate()) return
    setSaving(true)
    setFormError('')
    const wasActive = form.rule ? Boolean(form.rule.is_active) : false
    const pointsChanged =
      form.rule &&
      String(form.rule.minimum_points ?? '') !==
        String(values.minimum_points).trim()
    if (wasActive && pointsChanged) {
      setSaving(false)
      setConfirmError('')
      setConfirm({
        title: 'Change points on an active configuration',
        message: `${formatDesignation(form.rule.designation)} eligibility is active. Changing the minimum affects future eligibility checks. Continue?`,
        confirmLabel: 'Save Changes',
        variant: 'danger',
        run: performSave,
      })
      return
    }
    try {
      await performSave()
    } finally {
      setSaving(false)
    }
  }

  const requestToggle = (rule) => {
    if (rule.is_active) {
      setConfirmError('')
      setConfirm({
        title: 'Deactivate eligibility configuration',
        message: `Deactivate ${formatDesignation(rule.designation)} eligibility? Faculty eligibility checks will no longer use this configuration.`,
        confirmLabel: 'Deactivate',
        variant: 'danger',
        run: async () => {
          await setEligibilityRuleStatus(rule.eligibility_rule_id, false)
          setNotice(
            `${formatDesignation(rule.designation)} eligibility deactivated.`,
          )
          refetch()
        },
      })
      return
    }
    setConfirmError('')
    setConfirm({
      title: 'Activate eligibility configuration',
      message: `Activate ${formatDesignation(rule.designation)} eligibility?`,
      confirmLabel: 'Activate',
      variant: 'primary',
      run: async () => {
        await setEligibilityRuleStatus(rule.eligibility_rule_id, true)
        setNotice(
          `${formatDesignation(rule.designation)} eligibility activated.`,
        )
        refetch()
      },
    })
  }

  const runConfirm = async () => {
    if (!confirm) return
    setConfirmBusy(true)
    setConfirmError('')
    try {
      await confirm.run()
      setConfirm(null)
    } catch (error) {
      setConfirmError(getAdminError(error, 'The action could not be completed.'))
    } finally {
      setConfirmBusy(false)
    }
  }

  if (!isAdmin) {
    return (
      <div className="page admin-page">
        <div className="page__header">
          <div>
            <h1 className="page__title">Eligibility</h1>
          </div>
        </div>
        <div className="empty-state">
          <p className="empty-state__title">{ADMIN_PERMISSION_TITLE}</p>
          <p className="empty-state__text">{ADMIN_PERMISSION_TEXT}</p>
          <Link className="btn btn--primary" to="/dashboard">
            Back to Dashboard
          </Link>
        </div>
      </div>
    )
  }

  if (status === 'loading') {
    return <LoadingScreen message="Loading eligibility configurations…" />
  }

  return (
    <div className="page admin-page">
      <div className="page__header">
        <div>
          <h1 className="page__title">Eligibility</h1>
          <p className="page__subtitle">
            Minimum points each designation needs for promotion eligibility.
          </p>
        </div>
        <div className="page__header-actions">
          <button type="button" className="btn btn--primary" onClick={openCreate}>
            Add Configuration
          </button>
        </div>
      </div>

      {notice ? (
        <div className="alert alert--success admin-success" role="status">
          <span>{notice}</span>
        </div>
      ) : null}

      {status === 'error' ? (
        <div className="empty-state">
          <p className="empty-state__title">
            Unable to load eligibility configurations
          </p>
          <p className="empty-state__text">{errorMessage}</p>
          <button type="button" className="btn btn--ghost" onClick={refetch}>
            Try Again
          </button>
        </div>
      ) : null}

      {status === 'empty' && !form ? (
        <div className="empty-state">
          <p className="empty-state__title">{ADMIN_EMPTY.eligibility}</p>
          <p className="empty-state__text">
            Add configurations so faculty can see promotion requirements.
          </p>
          <button type="button" className="btn btn--primary" onClick={openCreate}>
            Add Configuration
          </button>
        </div>
      ) : null}

      {form ? (
        <div className="admin-form">
          <p className="admin-form__title">
            {form.mode === 'create'
              ? 'Add eligibility configuration'
              : 'Edit eligibility configuration'}
          </p>
          {form.rule && form.rule.is_active ? (
            <div className="admin-warning" role="note">
              This configuration is active and affects eligibility results.
            </div>
          ) : null}
          <div className="admin-form__grid">
            <div className="field">
              <label className="field__label" htmlFor="elig-designation">
                Designation
              </label>
              <input
                id="elig-designation"
                className="field__input"
                type="text"
                placeholder="e.g. Assistant Professor"
                value={values.designation}
                onChange={(event) =>
                  setValues({ ...values, designation: event.target.value })
                }
              />
              {fieldErrors.designation ? (
                <p className="field__error">{fieldErrors.designation}</p>
              ) : null}
            </div>
            <div className="field">
              <label className="field__label" htmlFor="elig-points">
                Minimum points
              </label>
              <input
                id="elig-points"
                className="field__input"
                type="number"
                min="0"
                step="1"
                value={values.minimum_points}
                onChange={(event) =>
                  setValues({ ...values, minimum_points: event.target.value })
                }
              />
              {fieldErrors.minimum_points ? (
                <p className="field__error">{fieldErrors.minimum_points}</p>
              ) : null}
            </div>
            <div className="field">
              <label className="field__label" htmlFor="elig-from">
                Effective from
              </label>
              <input
                id="elig-from"
                className="field__input"
                type="date"
                value={values.effective_from}
                onChange={(event) =>
                  setValues({ ...values, effective_from: event.target.value })
                }
              />
            </div>
            <div className="field">
              <label className="field__label" htmlFor="elig-to">
                Effective to
              </label>
              <input
                id="elig-to"
                className="field__input"
                type="date"
                value={values.effective_to}
                onChange={(event) =>
                  setValues({ ...values, effective_to: event.target.value })
                }
              />
              {fieldErrors.effective_to ? (
                <p className="field__error">{fieldErrors.effective_to}</p>
              ) : null}
            </div>
          </div>
          {formError ? (
            <div className="alert alert--danger admin-form__error" role="alert">
              {formError}
            </div>
          ) : null}
          <div className="admin-form__actions">
            <button
              type="button"
              className="btn btn--primary"
              disabled={saving}
              onClick={saveForm}
            >
              {saving ? 'Saving…' : 'Save'}
            </button>
            <button
              type="button"
              className="btn btn--ghost"
              disabled={saving}
              onClick={() => setForm(null)}
            >
              Cancel
            </button>
          </div>
        </div>
      ) : null}

      {status === 'ready' || (form && rules.length > 0) ? (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Designation</th>
                <th scope="col">Minimum points</th>
                <th scope="col">Effective period</th>
                <th scope="col">Status</th>
                <th scope="col">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {rules.map((rule) => (
                <tr key={rule.eligibility_rule_id}>
                  <td>{formatDesignation(rule.designation)}</td>
                  <td>{rule.minimum_points}</td>
                  <td>{rangeLabel(rule.effective_from, rule.effective_to)}</td>
                  <td>
                    <span
                      className={`admin-badge ${
                        rule.is_active
                          ? 'admin-badge--active'
                          : 'admin-badge--inactive'
                      }`}
                    >
                      {isActiveLabel(rule.is_active)}
                    </span>
                  </td>
                  <td>
                    <div className="admin-actions">
                      <button
                        type="button"
                        className="btn btn--ghost btn--small"
                        onClick={() => openEdit(rule)}
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        className={
                          rule.is_active
                            ? 'btn btn--danger-outline btn--small'
                            : 'btn btn--ghost btn--small'
                        }
                        onClick={() => requestToggle(rule)}
                      >
                        {rule.is_active ? 'Deactivate' : 'Activate'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      <ConfirmDialog
        open={Boolean(confirm)}
        title={confirm?.title || ''}
        message={confirm?.message || ''}
        confirmLabel={confirm?.confirmLabel || 'Confirm'}
        confirmVariant={confirm?.variant || 'danger'}
        busy={confirmBusy}
        error={confirmError}
        onConfirm={runConfirm}
        onCancel={() => {
          if (!confirmBusy) setConfirm(null)
        }}
      />
    </div>
  )
}
