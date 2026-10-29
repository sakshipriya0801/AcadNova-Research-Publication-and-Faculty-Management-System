import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import ConfirmDialog from '../../components/ConfirmDialog'
import LoadingScreen from '../../components/LoadingScreen'
import {
  createAcademicYear,
  deleteAcademicYear,
  listAcademicYears,
  setCurrentAcademicYear,
  updateAcademicYear,
} from '../../services/adminService'
import {
  ADMIN_EMPTY,
  ADMIN_PERMISSION_TEXT,
  ADMIN_PERMISSION_TITLE,
  formatDateValue,
  getAdminError,
} from '../../utils/admin'

const EMPTY_FORM = { name: '', start_date: '', end_date: '' }

export default function AdminAcademicYearsPage() {
  const { user } = useAuth()
  const [years, setYears] = useState([])
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
    listAcademicYears()
      .then((response) => {
        const list = response.data || []
        setYears(list)
        setStatus(list.length === 0 ? 'empty' : 'ready')
      })
      .catch((error) => {
        setErrorMessage(getAdminError(error, 'Unable to load academic years.'))
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

  const openEdit = (year) => {
    setValues({
      name: year.name || '',
      start_date: year.start_date ? String(year.start_date).slice(0, 10) : '',
      end_date: year.end_date ? String(year.end_date).slice(0, 10) : '',
    })
    setFieldErrors({})
    setFormError('')
    setForm({ mode: 'edit', id: year.academic_year_id })
  }

  const validate = () => {
    const errors = {}
    if (!values.name.trim()) errors.name = 'Name is required.'
    if (!values.start_date) errors.start_date = 'Start date is required.'
    if (!values.end_date) errors.end_date = 'End date is required.'
    if (
      values.start_date &&
      values.end_date &&
      values.start_date >= values.end_date
    ) {
      errors.end_date = 'End date must be after the start date.'
    }
    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  const saveForm = async () => {
    if (!validate()) return
    setSaving(true)
    setFormError('')
    const payload = {
      name: values.name.trim(),
      start_date: values.start_date,
      end_date: values.end_date,
    }
    try {
      if (form.mode === 'create') {
        await createAcademicYear(payload)
        setNotice('Academic year created.')
      } else {
        await updateAcademicYear(form.id, payload)
        setNotice('Academic year updated.')
      }
      setForm(null)
      refetch()
    } catch (error) {
      setFormError(getAdminError(error, 'Unable to save the academic year.'))
    } finally {
      setSaving(false)
    }
  }

  const requestSetCurrent = (year) => {
    setConfirmError('')
    setConfirm({
      title: 'Set current academic year',
      message: `Make ${year.name} the current academic year? Points and reports will prefer this year.`,
      confirmLabel: 'Set Current',
      variant: 'primary',
      run: async () => {
        await setCurrentAcademicYear(year.academic_year_id)
        setNotice(`${year.name} is now the current academic year.`)
        refetch()
      },
    })
  }

  const requestDelete = (year) => {
    setConfirmError('')
    setConfirm({
      title: 'Delete academic year',
      message: `Delete the academic year ${year.name}? This cannot be undone.`,
      confirmLabel: 'Delete',
      variant: 'danger',
      run: async () => {
        await deleteAcademicYear(year.academic_year_id)
        setNotice(`Academic year ${year.name} deleted.`)
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
            <h1 className="page__title">Academic Years</h1>
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
    return <LoadingScreen message="Loading academic years…" />
  }

  return (
    <div className="page admin-page">
      <div className="page__header">
        <div>
          <h1 className="page__title">Academic Years</h1>
          <p className="page__subtitle">
            Manage academic years and select the current year used across
            points and reports.
          </p>
        </div>
        <div className="page__header-actions">
          <button type="button" className="btn btn--primary" onClick={openCreate}>
            Add Academic Year
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
          <p className="empty-state__title">Unable to load academic years</p>
          <p className="empty-state__text">{errorMessage}</p>
          <button type="button" className="btn btn--ghost" onClick={refetch}>
            Try Again
          </button>
        </div>
      ) : null}

      {status === 'empty' && !form ? (
        <div className="empty-state">
          <p className="empty-state__title">{ADMIN_EMPTY.academicYears}</p>
          <p className="empty-state__text">
            Create the first academic year to enable points tracking.
          </p>
          <button type="button" className="btn btn--primary" onClick={openCreate}>
            Add Academic Year
          </button>
        </div>
      ) : null}

      {form ? (
        <div className="admin-form">
          <p className="admin-form__title">
            {form.mode === 'create' ? 'Add academic year' : 'Edit academic year'}
          </p>
          <div className="admin-form__grid">
            <div className="field">
              <label className="field__label" htmlFor="year-name">
                Name
              </label>
              <input
                id="year-name"
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
              <label className="field__label" htmlFor="year-start">
                Start date
              </label>
              <input
                id="year-start"
                className="field__input"
                type="date"
                value={values.start_date}
                onChange={(event) =>
                  setValues({ ...values, start_date: event.target.value })
                }
              />
              {fieldErrors.start_date ? (
                <p className="field__error">{fieldErrors.start_date}</p>
              ) : null}
            </div>
            <div className="field">
              <label className="field__label" htmlFor="year-end">
                End date
              </label>
              <input
                id="year-end"
                className="field__input"
                type="date"
                value={values.end_date}
                onChange={(event) =>
                  setValues({ ...values, end_date: event.target.value })
                }
              />
              {fieldErrors.end_date ? (
                <p className="field__error">{fieldErrors.end_date}</p>
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

      {status === 'ready' || (form && years.length > 0) ? (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Name</th>
                <th scope="col">Start</th>
                <th scope="col">End</th>
                <th scope="col">Current</th>
                <th scope="col">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {years.map((year) => (
                <tr key={year.academic_year_id}>
                  <td>{year.name}</td>
                  <td>{formatDateValue(year.start_date)}</td>
                  <td>{formatDateValue(year.end_date)}</td>
                  <td>
                    {year.is_current ? (
                      <span className="admin-badge admin-badge--current">
                        Current
                      </span>
                    ) : (
                      <span className="admin-ellipsis">—</span>
                    )}
                  </td>
                  <td>
                    <div className="admin-actions">
                      {!year.is_current ? (
                        <button
                          type="button"
                          className="btn btn--ghost btn--small"
                          onClick={() => requestSetCurrent(year)}
                        >
                          Set Current
                        </button>
                      ) : null}
                      <button
                        type="button"
                        className="btn btn--ghost btn--small"
                        onClick={() => openEdit(year)}
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        className="btn btn--danger-outline btn--small"
                        onClick={() => requestDelete(year)}
                      >
                        Delete
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
