import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import ConfirmDialog from '../../components/ConfirmDialog'
import LoadingScreen from '../../components/LoadingScreen'
import {
  createDepartment,
  deactivateDepartment,
  deleteDepartment,
  listDepartments,
  updateDepartment,
} from '../../services/adminService'
import {
  ADMIN_EMPTY,
  ADMIN_PERMISSION_TEXT,
  ADMIN_PERMISSION_TITLE,
  getAdminError,
  isActiveLabel,
} from '../../utils/admin'

const EMPTY_FORM = { name: '', code: '', description: '' }

export default function AdminDepartmentsPage() {
  const { user } = useAuth()
  const [departments, setDepartments] = useState([])
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
    listDepartments()
      .then((response) => {
        const list = response.data || []
        setDepartments(list)
        setStatus(list.length === 0 ? 'empty' : 'ready')
      })
      .catch((error) => {
        setErrorMessage(getAdminError(error, 'Unable to load departments.'))
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

  const openEdit = (department) => {
    setValues({
      name: department.name || '',
      code: department.code || '',
      description: department.description || '',
    })
    setFieldErrors({})
    setFormError('')
    setForm({ mode: 'edit', id: department.department_id })
  }

  const validate = () => {
    const errors = {}
    if (!values.name.trim()) errors.name = 'Name is required.'
    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  const saveForm = async () => {
    if (!validate()) return
    setSaving(true)
    setFormError('')
    const payload = {
      name: values.name.trim(),
      code: values.code.trim() || null,
      description: values.description.trim() || null,
    }
    try {
      if (form.mode === 'create') {
        await createDepartment(payload)
        setNotice('Department created.')
      } else {
        await updateDepartment(form.id, payload)
        setNotice('Department updated.')
      }
      setForm(null)
      refetch()
    } catch (error) {
      setFormError(getAdminError(error, 'Unable to save the department.'))
    } finally {
      setSaving(false)
    }
  }

  const requestToggle = (department) => {
    if (department.is_active) {
      setConfirmError('')
      setConfirm({
        title: 'Deactivate department',
        message: `Deactivate ${department.name}? Faculty assigned to it keep their records, but the department will no longer be offered for new assignments.`,
        confirmLabel: 'Deactivate',
        variant: 'danger',
        run: async () => {
          await deactivateDepartment(department.department_id)
          setNotice(`Department ${department.name} deactivated.`)
          refetch()
        },
      })
      return
    }
    setConfirmError('')
    setConfirm({
      title: 'Activate department',
      message: `Activate ${department.name} so it can be assigned again?`,
      confirmLabel: 'Activate',
      variant: 'primary',
      run: async () => {
        await updateDepartment(department.department_id, { is_active: true })
        setNotice(`Department ${department.name} activated.`)
        refetch()
      },
    })
  }

  const requestDelete = (department) => {
    setConfirmError('')
    setConfirm({
      title: 'Delete department',
      message: `Delete the department ${department.name}? This cannot be undone.`,
      confirmLabel: 'Delete',
      variant: 'danger',
      run: async () => {
        await deleteDepartment(department.department_id)
        setNotice(`Department ${department.name} deleted.`)
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
            <h1 className="page__title">Departments</h1>
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
    return <LoadingScreen message="Loading departments…" />
  }

  return (
    <div className="page admin-page">
      <div className="page__header">
        <div>
          <h1 className="page__title">Departments</h1>
          <p className="page__subtitle">
            Maintain the departments faculty belong to.
          </p>
        </div>
        <div className="page__header-actions">
          <button type="button" className="btn btn--primary" onClick={openCreate}>
            Add Department
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
          <p className="empty-state__title">Unable to load departments</p>
          <p className="empty-state__text">{errorMessage}</p>
          <button type="button" className="btn btn--ghost" onClick={refetch}>
            Try Again
          </button>
        </div>
      ) : null}

      {status === 'empty' && !form ? (
        <div className="empty-state">
          <p className="empty-state__title">{ADMIN_EMPTY.departments}</p>
          <p className="empty-state__text">
            Create the first department so faculty can be organised.
          </p>
          <button type="button" className="btn btn--primary" onClick={openCreate}>
            Add Department
          </button>
        </div>
      ) : null}

      {form ? (
        <div className="admin-form">
          <p className="admin-form__title">
            {form.mode === 'create' ? 'Add department' : 'Edit department'}
          </p>
          <div className="admin-form__grid">
            <div className="field">
              <label className="field__label" htmlFor="dept-name">
                Name
              </label>
              <input
                id="dept-name"
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
              <label className="field__label" htmlFor="dept-code">
                Code
              </label>
              <input
                id="dept-code"
                className="field__input"
                type="text"
                value={values.code}
                onChange={(event) =>
                  setValues({ ...values, code: event.target.value })
                }
              />
            </div>
            <div className="field field--full">
              <label className="field__label" htmlFor="dept-description">
                Description
              </label>
              <textarea
                id="dept-description"
                className="field__input"
                rows={3}
                value={values.description}
                onChange={(event) =>
                  setValues({ ...values, description: event.target.value })
                }
              />
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

      {status === 'ready' || (form && departments.length > 0) ? (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Name</th>
                <th scope="col">Code</th>
                <th scope="col">Description</th>
                <th scope="col">Status</th>
                <th scope="col">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {departments.map((department) => (
                <tr key={department.department_id}>
                  <td>{department.name}</td>
                  <td>{department.code || '—'}</td>
                  <td>{department.description || '—'}</td>
                  <td>
                    <span
                      className={`admin-badge ${
                        department.is_active
                          ? 'admin-badge--active'
                          : 'admin-badge--inactive'
                      }`}
                    >
                      {isActiveLabel(department.is_active)}
                    </span>
                  </td>
                  <td>
                    <div className="admin-actions">
                      <button
                        type="button"
                        className="btn btn--ghost btn--small"
                        onClick={() => openEdit(department)}
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        className={
                          department.is_active
                            ? 'btn btn--danger-outline btn--small'
                            : 'btn btn--ghost btn--small'
                        }
                        onClick={() => requestToggle(department)}
                      >
                        {department.is_active ? 'Deactivate' : 'Activate'}
                      </button>
                      <button
                        type="button"
                        className="btn btn--danger-outline btn--small"
                        onClick={() => requestDelete(department)}
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
