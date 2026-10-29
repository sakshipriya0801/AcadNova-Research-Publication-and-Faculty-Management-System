import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import ConfirmDialog from '../../components/ConfirmDialog'
import LoadingScreen from '../../components/LoadingScreen'
import {
  createRule,
  listRules,
  setRuleStatus,
  updateRule,
} from '../../services/adminService'
import { PUBLICATION_TYPES } from '../../utils/publication'
import {
  ADMIN_EMPTY,
  ADMIN_PERMISSION_TEXT,
  ADMIN_PERMISSION_TITLE,
  getAdminError,
  isActiveLabel,
  joinList,
  joinPositions,
  splitList,
  splitPositions,
  typeOrAny,
} from '../../utils/admin'

const EMPTY_FORM = {
  rule_code: '',
  name: '',
  publication_type: '',
  sub_type: '',
  indexing: '',
  author_positions: '',
  corresponding_author_required: false,
  collaboration_type: '',
  points: '0',
  max_claims_per_year: '',
  eligibility_designation: '',
  description: '',
  effective_from: '',
  effective_to: '',
}

export default function AdminRulesPage() {
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
    listRules()
      .then((response) => {
        const list = response.data || []
        setRules(list)
        setStatus(list.length === 0 ? 'empty' : 'ready')
      })
      .catch((error) => {
        setErrorMessage(getAdminError(error, 'Unable to load publication rules.'))
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
      rule_code: rule.rule_code || '',
      name: rule.name || '',
      publication_type: rule.publication_type || '',
      sub_type: rule.sub_type || '',
      indexing: joinList(rule.indexing),
      author_positions: joinPositions(rule.author_positions),
      corresponding_author_required: Boolean(rule.corresponding_author_required),
      collaboration_type: rule.collaboration_type || '',
      points: String(rule.points ?? 0),
      max_claims_per_year:
        rule.max_claims_per_year == null ? '' : String(rule.max_claims_per_year),
      eligibility_designation: joinList(rule.eligibility_designation),
      description: rule.description || '',
      effective_from: rule.effective_from
        ? String(rule.effective_from).slice(0, 10)
        : '',
      effective_to: rule.effective_to
        ? String(rule.effective_to).slice(0, 10)
        : '',
    })
    setFieldErrors({})
    setFormError('')
    setForm({ mode: 'edit', id: rule.rule_id, rule })
  }

  const validate = () => {
    const errors = {}
    if (!values.rule_code.trim()) errors.rule_code = 'Rule code is required.'
    if (!values.name.trim()) errors.name = 'Name is required.'
    if (!/^\d+$/.test(String(values.points).trim())) {
      errors.points = 'Points must be zero or a positive whole number.'
    }
    if (
      values.effective_from &&
      values.effective_to &&
      values.effective_from >= values.effective_to
    ) {
      errors.effective_to = 'Effective to must be after effective from.'
    }
    if (
      values.max_claims_per_year &&
      !/^\d+$/.test(String(values.max_claims_per_year).trim())
    ) {
      errors.max_claims_per_year = 'Max claims must be a positive whole number.'
    }
    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  const buildPayload = () => {
    const payload = {
      rule_code: values.rule_code.trim(),
      name: values.name.trim(),
      publication_type: values.publication_type || null,
      sub_type: values.sub_type.trim() || null,
      indexing: splitList(values.indexing),
      author_positions: splitPositions(values.author_positions),
      corresponding_author_required: Boolean(
        values.corresponding_author_required,
      ),
      collaboration_type: values.collaboration_type.trim() || null,
      points: Number(values.points),
      max_claims_per_year: values.max_claims_per_year
        ? Number(values.max_claims_per_year)
        : null,
      eligibility_designation: splitList(values.eligibility_designation),
      description: values.description.trim() || null,
      effective_from: values.effective_from || null,
      effective_to: values.effective_to || null,
    }
    if (form.mode === 'create') {
      payload.is_active = true
    }
    return payload
  }

  const performSave = async () => {
    const payload = buildPayload()
    try {
      if (form.mode === 'create') {
        await createRule(payload)
        setNotice('Publication rule created.')
      } else {
        await updateRule(form.id, payload)
        setNotice('Publication rule updated.')
      }
      setForm(null)
      refetch()
    } catch (error) {
      setFormError(getAdminError(error, 'Unable to save the publication rule.'))
    }
  }

  const saveForm = async () => {
    if (!validate()) return
    setSaving(true)
    setFormError('')
    const wasActive = form.rule ? Boolean(form.rule.is_active) : false
    const pointsChanged =
      form.rule && String(form.rule.points ?? '') !== String(values.points).trim()
    if (wasActive && pointsChanged) {
      setSaving(false)
      setConfirmError('')
      setConfirm({
        title: 'Change points on an active rule',
        message: `${form.rule.name} is active. Changing its points affects future points calculations for matching publications. Continue?`,
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
        title: 'Deactivate publication rule',
        message: `Deactivate ${rule.name}? It will no longer award points for new claims.`,
        confirmLabel: 'Deactivate',
        variant: 'danger',
        run: async () => {
          await setRuleStatus(rule.rule_id, false)
          setNotice(`Rule ${rule.name} deactivated.`)
          refetch()
        },
      })
      return
    }
    setConfirmError('')
    setConfirm({
      title: 'Activate publication rule',
      message: `Activate ${rule.name} so it can award points again?`,
      confirmLabel: 'Activate',
      variant: 'primary',
      run: async () => {
        await setRuleStatus(rule.rule_id, true)
        setNotice(`Rule ${rule.name} activated.`)
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
            <h1 className="page__title">Publication Rules</h1>
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
    return <LoadingScreen message="Loading publication rules…" />
  }

  return (
    <div className="page admin-page">
      <div className="page__header">
        <div>
          <h1 className="page__title">Publication Rules</h1>
          <p className="page__subtitle">
            Define how publications award points. Matching and scoring stay on
            the server.
          </p>
        </div>
        <div className="page__header-actions">
          <button type="button" className="btn btn--primary" onClick={openCreate}>
            Add Rule
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
          <p className="empty-state__title">Unable to load publication rules</p>
          <p className="empty-state__text">{errorMessage}</p>
          <button type="button" className="btn btn--ghost" onClick={refetch}>
            Try Again
          </button>
        </div>
      ) : null}

      {status === 'empty' && !form ? (
        <div className="empty-state">
          <p className="empty-state__title">{ADMIN_EMPTY.rules}</p>
          <p className="empty-state__text">
            Create the first rule so publications can award points.
          </p>
          <button type="button" className="btn btn--primary" onClick={openCreate}>
            Add Rule
          </button>
        </div>
      ) : null}

      {form ? (
        <div className="admin-form">
          <p className="admin-form__title">
            {form.mode === 'create' ? 'Add publication rule' : 'Edit rule'}
          </p>
          {form.rule && form.rule.is_active ? (
            <div className="admin-warning" role="note">
              This rule is active. Changes affect future points calculations.
            </div>
          ) : null}
          <div className="admin-form__grid">
            <div className="field">
              <label className="field__label" htmlFor="rule-code">
                Rule code
              </label>
              <input
                id="rule-code"
                className="field__input"
                type="text"
                placeholder="e.g. R-JOURNAL-SCOPUS-01"
                value={values.rule_code}
                onChange={(event) =>
                  setValues({ ...values, rule_code: event.target.value })
                }
              />
              {fieldErrors.rule_code ? (
                <p className="field__error">{fieldErrors.rule_code}</p>
              ) : null}
            </div>
            <div className="field">
              <label className="field__label" htmlFor="rule-name">
                Name
              </label>
              <input
                id="rule-name"
                className="field__input"
                type="text"
                value={values.name}
                onChange={(event) =>
                  setValues({ ...values, name: event.target.value })
                }
              />
              {fieldErrors.name ? (
                <p className="field__error">{fieldErrors.name}</p>
              ) : null}
            </div>
            <div className="field">
              <label className="field__label" htmlFor="rule-type">
                Publication type
              </label>
              <select
                id="rule-type"
                className="field__input"
                value={values.publication_type}
                onChange={(event) =>
                  setValues({ ...values, publication_type: event.target.value })
                }
              >
                <option value="">Any type</option>
                {PUBLICATION_TYPES.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label className="field__label" htmlFor="rule-subtype">
                Sub type
              </label>
              <input
                id="rule-subtype"
                className="field__input"
                type="text"
                value={values.sub_type}
                onChange={(event) =>
                  setValues({ ...values, sub_type: event.target.value })
                }
              />
            </div>
            <div className="field">
              <label className="field__label" htmlFor="rule-indexing">
                Indexing
              </label>
              <input
                id="rule-indexing"
                className="field__input"
                type="text"
                placeholder="Comma separated, e.g. Scopus, Web of Science"
                value={values.indexing}
                onChange={(event) =>
                  setValues({ ...values, indexing: event.target.value })
                }
              />
            </div>
            <div className="field">
              <label className="field__label" htmlFor="rule-positions">
                Author positions
              </label>
              <input
                id="rule-positions"
                className="field__input"
                type="text"
                placeholder="Comma separated, e.g. 1, 2"
                value={values.author_positions}
                onChange={(event) =>
                  setValues({ ...values, author_positions: event.target.value })
                }
              />
            </div>
            <div className="field">
              <label className="field__label" htmlFor="rule-points">
                Points
              </label>
              <input
                id="rule-points"
                className="field__input"
                type="number"
                min="0"
                step="1"
                value={values.points}
                onChange={(event) =>
                  setValues({ ...values, points: event.target.value })
                }
              />
              {fieldErrors.points ? (
                <p className="field__error">{fieldErrors.points}</p>
              ) : null}
            </div>
            <div className="field">
              <label className="field__label" htmlFor="rule-max-claims">
                Max claims per year
              </label>
              <input
                id="rule-max-claims"
                className="field__input"
                type="number"
                min="1"
                step="1"
                value={values.max_claims_per_year}
                onChange={(event) =>
                  setValues({ ...values, max_claims_per_year: event.target.value })
                }
              />
              {fieldErrors.max_claims_per_year ? (
                <p className="field__error">{fieldErrors.max_claims_per_year}</p>
              ) : null}
            </div>
            <div className="field">
              <label className="field__label" htmlFor="rule-collab">
                Collaboration type
              </label>
              <input
                id="rule-collab"
                className="field__input"
                type="text"
                value={values.collaboration_type}
                onChange={(event) =>
                  setValues({ ...values, collaboration_type: event.target.value })
                }
              />
            </div>
            <div className="field">
              <label className="field__label" htmlFor="rule-eligibility">
                Eligibility designations
              </label>
              <input
                id="rule-eligibility"
                className="field__input"
                type="text"
                placeholder="Comma separated, e.g. Assistant Professor"
                value={values.eligibility_designation}
                onChange={(event) =>
                  setValues({
                    ...values,
                    eligibility_designation: event.target.value,
                  })
                }
              />
            </div>
            <div className="field">
              <label className="field__label" htmlFor="rule-from">
                Effective from
              </label>
              <input
                id="rule-from"
                className="field__input"
                type="date"
                value={values.effective_from}
                onChange={(event) =>
                  setValues({ ...values, effective_from: event.target.value })
                }
              />
            </div>
            <div className="field">
              <label className="field__label" htmlFor="rule-to">
                Effective to
              </label>
              <input
                id="rule-to"
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
            <div className="field field--full">
              <label className="field__label" htmlFor="rule-description">
                Description
              </label>
              <textarea
                id="rule-description"
                className="field__input"
                rows={2}
                value={values.description}
                onChange={(event) =>
                  setValues({ ...values, description: event.target.value })
                }
              />
            </div>
            <div className="field field--full">
              <label className="admin-form__checkbox">
                <input
                  type="checkbox"
                  checked={values.corresponding_author_required}
                  onChange={(event) =>
                    setValues({
                      ...values,
                      corresponding_author_required: event.target.checked,
                    })
                  }
                />
                Corresponding author required
              </label>
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
                <th scope="col">Code</th>
                <th scope="col">Name</th>
                <th scope="col">Type</th>
                <th scope="col">Points</th>
                <th scope="col">Indexing</th>
                <th scope="col">Positions</th>
                <th scope="col">Status</th>
                <th scope="col">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {rules.map((rule) => (
                <tr key={rule.rule_id}>
                  <td>{rule.rule_code || '—'}</td>
                  <td>{rule.name}</td>
                  <td>{typeOrAny(rule.publication_type)}</td>
                  <td>{rule.points}</td>
                  <td>{joinList(rule.indexing) || '—'}</td>
                  <td>{joinPositions(rule.author_positions) || '—'}</td>
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

      <div className="admin-pager">
        <span>{rules.length} rule(s) configured</span>
      </div>

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
