import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import ConfirmDialog from '../../components/ConfirmDialog'
import LoadingScreen from '../../components/LoadingScreen'
import {
  createFaculty,
  listDepartments,
  listFaculty,
  setFacultyStatus,
  updateFaculty,
} from '../../services/adminService'
import {
  ADMIN_EMPTY,
  ADMIN_PERMISSION_TEXT,
  ADMIN_PERMISSION_TITLE,
  DEPARTMENT_PROGRAMS,
  DESIGNATION_OPTIONS,
  departmentProgramLabel,
  getAdminError,
  isActiveLabel,
  joinList,
  splitList,
} from '../../utils/admin'
import { validateFacultyProfile } from '../../utils/facultyOptions'

const PAGE_SIZE = 25
const EMPTY_FORM = {
  name: '',
  email: '',
  employee_id: '',
  department_id: '',
  designation: '',
  orcid_id: '',
  scopus_author_id: '',
  web_of_science_researcher_id: '',
  pubmed_id: '',
  research_interests: '',
}

export default function AdminFacultyPage() {
  const { user } = useAuth()
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [departmentFilter, setDepartmentFilter] = useState('')
  const [designationFilter, setDesignationFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)
  const [reloadKey, setReloadKey] = useState(0)

  const [data, setData] = useState(null)
  const [status, setStatus] = useState('loading')
  const [errorMessage, setErrorMessage] = useState('')
  const [notice, setNotice] = useState('')
  const [departments, setDepartments] = useState([])

  const [form, setForm] = useState(null)
  const [values, setValues] = useState(EMPTY_FORM)
  const [fieldErrors, setFieldErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  const [showCreate, setShowCreate] = useState(false)
  const [createValues, setCreateValues] = useState({
    name: '',
    email: '',
    employee_id: '',
    department_id: '',
    designation: '',
    password: '',
  })
  const [createErrors, setCreateErrors] = useState({})
  const [createError, setCreateError] = useState('')
  const [createSaving, setCreateSaving] = useState(false)
  const [generatedPassword, setGeneratedPassword] = useState('')
  const [copied, setCopied] = useState(false)

  const [confirm, setConfirm] = useState(null)
  const [confirmBusy, setConfirmBusy] = useState(false)
  const [confirmError, setConfirmError] = useState('')

  const isAdmin = user?.role === 'admin'
  const items = data?.items || []
  const total = data?.total ?? 0
  const totalPages = data?.total_pages ?? 1

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim())
      setPage(1)
    }, 400)
    return () => clearTimeout(timer)
  }, [searchInput])

  useEffect(() => {
    setPage(1)
  }, [departmentFilter, designationFilter, statusFilter])

  useEffect(() => {
    if (!isAdmin) return undefined
    let cancelled = false
    listDepartments()
      .then((response) => {
        if (!cancelled) setDepartments(response.data || [])
      })
      .catch(() => {
        if (!cancelled) setDepartments([])
      })
    return () => {
      cancelled = true
    }
  }, [isAdmin, reloadKey])

  const load = useCallback(() => {
    if (!isAdmin) return
    setStatus('loading')
    const params = { page, page_size: PAGE_SIZE }
    if (search) params.search = search
    if (departmentFilter) params.department_id = departmentFilter
    if (designationFilter) params.designation = designationFilter
    if (statusFilter) params.is_active = statusFilter
    listFaculty(params)
      .then((response) => {
        setData(response.data)
        setStatus('ready')
      })
      .catch((error) => {
        setErrorMessage(getAdminError(error, 'Unable to load faculty.'))
        setStatus('error')
      })
  }, [
    isAdmin,
    reloadKey,
    page,
    search,
    departmentFilter,
    designationFilter,
    statusFilter,
  ])

  useEffect(() => {
    load()
  }, [load])

  const refetch = () => setReloadKey((key) => key + 1)

  const openEdit = (faculty) => {
    setValues({
      name: faculty.name || '',
      email: faculty.email || '',
      employee_id: faculty.employee_id || '',
      department_id: faculty.department_id || '',
      designation: faculty.designation || '',
      orcid_id: faculty.orcid_id || '',
      scopus_author_id: faculty.scopus_author_id || '',
      web_of_science_researcher_id: faculty.web_of_science_researcher_id || '',
      pubmed_id: faculty.pubmed_id || '',
      research_interests: joinList(faculty.research_interests),
    })
    setFieldErrors({})
    setFormError('')
    setForm({ mode: 'edit', id: faculty.faculty_id, faculty })
  }

  const validate = () => {
    const errors = {}
    if (!values.name.trim()) errors.name = 'Name is required.'
    if (!values.email.trim()) errors.email = 'Email is required.'
    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  const saveForm = async () => {
    if (!validate()) return
    setSaving(true)
    setFormError('')
    const payload = {
      name: values.name.trim(),
      email: values.email.trim(),
      employee_id: values.employee_id.trim() || null,
      department_id: values.department_id || null,
      designation: values.designation.trim() || null,
      orcid_id: values.orcid_id.trim() || null,
      scopus_author_id: values.scopus_author_id.trim() || null,
      web_of_science_researcher_id:
        values.web_of_science_researcher_id.trim() || null,
      pubmed_id: values.pubmed_id.trim() || null,
      research_interests: splitList(values.research_interests),
    }
    try {
      await updateFaculty(form.id, payload)
      setNotice('Faculty profile updated.')
      setForm(null)
      refetch()
    } catch (error) {
      setFormError(getAdminError(error, 'Unable to save the faculty profile.'))
    } finally {
      setSaving(false)
    }
  }

  const openCreate = () => {
    setShowCreate(true)
    setCreateValues({
      name: '',
      email: '',
      employee_id: '',
      department_id: '',
      designation: '',
      password: '',
    })
    setCreateErrors({})
    setCreateError('')
  }

  const setCreateField = (field) => (event) => {
    setCreateValues((current) => ({ ...current, [field]: event.target.value }))
    setCreateErrors((current) => ({ ...current, [field]: undefined }))
  }

  const validateCreate = () => {
    const common = validateFacultyProfile({
      name: createValues.name,
      email: createValues.email,
      department: createValues.department_id,
      designation: createValues.designation,
    })
    const errors = { ...common }
    if (common.department) {
      errors.department_id = common.department
      delete errors.department
    }
    const pw = createValues.password
    if (pw) {
      if (pw.length < 8) errors.password = 'Use at least 8 characters.'
      else if (!/[A-Za-z]/.test(pw)) errors.password = 'Include at least one letter.'
      else if (!/[0-9]/.test(pw)) errors.password = 'Include at least one number.'
    }
    setCreateErrors(errors)
    return Object.keys(errors).length === 0
  }

  const submitCreate = async () => {
    if (!validateCreate()) return
    setCreateSaving(true)
    setCreateError('')
    try {
      const response = await createFaculty({
        name: createValues.name.trim(),
        email: createValues.email.trim(),
        employee_id: createValues.employee_id.trim() || null,
        department_id: createValues.department_id,
        designation: createValues.designation,
        password: createValues.password || null,
      })
      setShowCreate(false)
      if (response.data?.generated_password) {
        setGeneratedPassword(response.data.generated_password)
        setCopied(false)
      } else {
        setNotice('Faculty account created.')
      }
      refetch()
    } catch (error) {
      setCreateError(getAdminError(error, 'Unable to create the faculty account.'))
    } finally {
      setCreateSaving(false)
    }
  }

  const copyGeneratedPassword = async () => {
    try {
      await navigator.clipboard.writeText(generatedPassword)
      setCopied(true)
    } catch {
      setCopied(false)
    }
  }

  const requestToggle = (faculty) => {
    if (faculty.is_active) {
      setConfirmError('')
      setConfirm({
        title: 'Deactivate faculty',
        message: `Deactivate ${faculty.name}? Their publications and points remain, but the account will be marked inactive.`,
        confirmLabel: 'Deactivate',
        variant: 'danger',
        run: async () => {
          await setFacultyStatus(faculty.faculty_id, false)
          setNotice(`${faculty.name} deactivated.`)
          refetch()
        },
      })
      return
    }
    setConfirmError('')
    setConfirm({
      title: 'Activate faculty',
      message: `Activate ${faculty.name}?`,
      confirmLabel: 'Activate',
      variant: 'primary',
      run: async () => {
        await setFacultyStatus(faculty.faculty_id, true)
        setNotice(`${faculty.name} activated.`)
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

  const resetFilters = () => {
    setSearchInput('')
    setSearch('')
    setDepartmentFilter('')
    setDesignationFilter('')
    setStatusFilter('')
    setPage(1)
  }

  const hasFilters = Boolean(
    searchInput || departmentFilter || designationFilter || statusFilter,
  )

  if (!isAdmin) {
    return (
      <div className="page admin-page">
        <div className="page__header">
          <div>
            <h1 className="page__title">Faculty</h1>
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
    return <LoadingScreen message="Loading faculty…" />
  }

  return (
    <div className="page admin-page">
      <div className="page__header">
        <div>
          <h1 className="page__title">Faculty</h1>
          <p className="page__subtitle">
            Search faculty profiles, update details and manage active status.
          </p>
        </div>
        <div className="page__header-actions">
          <button type="button" className="btn btn--primary" onClick={openCreate}>
            + Add Faculty
          </button>
        </div>
      </div>

      {showCreate ? (
        <section className="panel" aria-label="Add faculty">
          <h2 className="panel__title">Add Faculty</h2>
          {createError ? (
            <p className="alert alert--danger" role="alert">
              {createError}
            </p>
          ) : null}
          <div className="admin-form__grid">
            <div className="field">
              <label className="field__label" htmlFor="cf-name">
                Full Name
              </label>
              <input
                id="cf-name"
                className="field__input"
                type="text"
                value={createValues.name}
                onChange={setCreateField('name')}
                aria-invalid={Boolean(createErrors.name)}
                disabled={createSaving}
              />
              {createErrors.name ? (
                <p className="field__error">{createErrors.name}</p>
              ) : null}
            </div>
            <div className="field">
              <label className="field__label" htmlFor="cf-email">
                Email Address
              </label>
              <input
                id="cf-email"
                className="field__input"
                type="email"
                value={createValues.email}
                onChange={setCreateField('email')}
                aria-invalid={Boolean(createErrors.email)}
                disabled={createSaving}
              />
              {createErrors.email ? (
                <p className="field__error">{createErrors.email}</p>
              ) : null}
            </div>
            <div className="field">
              <label className="field__label" htmlFor="cf-empid">
                Employee ID (optional)
              </label>
              <input
                id="cf-empid"
                className="field__input"
                type="text"
                value={createValues.employee_id}
                onChange={setCreateField('employee_id')}
                disabled={createSaving}
              />
            </div>
            <div className="field">
              <label className="field__label" htmlFor="cf-dept">
                Department
              </label>
              <select
                id="cf-dept"
                className="field__input"
                value={createValues.department_id}
                onChange={setCreateField('department_id')}
                aria-invalid={Boolean(createErrors.department_id)}
                disabled={createSaving}
              >
                <option value="">Select department</option>
                {DEPARTMENT_PROGRAMS.map((program) => (
                  <option key={program} value={program}>
                    {program}
                  </option>
                ))}
              </select>
              {createErrors.department_id ? (
                <p className="field__error">{createErrors.department_id}</p>
              ) : null}
            </div>
            <div className="field">
              <label className="field__label" htmlFor="cf-designation">
                Designation
              </label>
              <select
                id="cf-designation"
                className="field__input"
                value={createValues.designation}
                onChange={setCreateField('designation')}
                aria-invalid={Boolean(createErrors.designation)}
                disabled={createSaving}
              >
                <option value="">Select designation</option>
                {DESIGNATION_OPTIONS.map((designation) => (
                  <option key={designation} value={designation}>
                    {designation}
                  </option>
                ))}
              </select>
              {createErrors.designation ? (
                <p className="field__error">{createErrors.designation}</p>
              ) : null}
            </div>
            <div className="field">
              <label className="field__label" htmlFor="cf-password">
                Temporary password
              </label>
              <input
                id="cf-password"
                className="field__input"
                type="password"
                autoComplete="new-password"
                value={createValues.password}
                onChange={setCreateField('password')}
                aria-invalid={Boolean(createErrors.password)}
                disabled={createSaving}
              />
              {createErrors.password ? (
                <p className="field__error">{createErrors.password}</p>
              ) : (
                <p className="field__hint">
                  Leave blank to generate a secure temporary password automatically.
                </p>
              )}
            </div>
          </div>
          <div className="admin-form__actions">
            <button
              type="button"
              className="btn btn--ghost"
              onClick={() => setShowCreate(false)}
              disabled={createSaving}
            >
              Cancel
            </button>
            <button
              type="button"
              className="btn btn--primary"
              onClick={submitCreate}
              disabled={createSaving}
            >
              {createSaving ? 'Creating…' : 'Create Faculty'}
            </button>
          </div>
        </section>
      ) : null}

      {notice ? (
        <div className="alert alert--success admin-success" role="status">
          <span>{notice}</span>
        </div>
      ) : null}

      <div className="admin-page__toolbar">
        <div className="admin-page__toolbar-grow field">
          <label className="field__label" htmlFor="faculty-search">
            Search
          </label>
          <input
            id="faculty-search"
            className="field__input"
            type="search"
            placeholder="Name, email or employee ID"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
          />
        </div>
        <div className="admin-page__toolbar-field field">
          <label className="field__label" htmlFor="faculty-department">
            Department
          </label>
          <select
            id="faculty-department"
            className="field__input"
            value={departmentFilter}
            onChange={(event) => setDepartmentFilter(event.target.value)}
          >
            <option value="">All departments</option>
            {DEPARTMENT_PROGRAMS.map((program) => (
              <option key={program} value={program}>
                {program}
              </option>
            ))}
          </select>
        </div>
        <div className="admin-page__toolbar-field field">
          <label className="field__label" htmlFor="faculty-designation">
            Designation
          </label>
          <select
            id="faculty-designation"
            className="field__input"
            value={designationFilter}
            onChange={(event) => setDesignationFilter(event.target.value)}
          >
            <option value="">All designations</option>
            {DESIGNATION_OPTIONS.map((designation) => (
              <option key={designation} value={designation}>
                {designation}
              </option>
            ))}
          </select>
        </div>
        <div className="admin-page__toolbar-field field">
          <label className="field__label" htmlFor="faculty-status">
            Status
          </label>
          <select
            id="faculty-status"
            className="field__input"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
          >
            <option value="">All</option>
            <option value="true">Active</option>
            <option value="false">Inactive</option>
          </select>
        </div>
        {hasFilters ? (
          <div className="admin-page__toolbar-actions">
            <button
              type="button"
              className="btn btn--ghost"
              onClick={resetFilters}
            >
              Clear Filters
            </button>
          </div>
        ) : null}
      </div>

      {status === 'error' ? (
        <div className="empty-state">
          <p className="empty-state__title">Unable to load faculty</p>
          <p className="empty-state__text">{errorMessage}</p>
          <button type="button" className="btn btn--ghost" onClick={refetch}>
            Try Again
          </button>
        </div>
      ) : null}

      {status === 'ready' && items.length === 0 ? (
        <div className="empty-state">
          <p className="empty-state__title">{ADMIN_EMPTY.faculty}</p>
          <p className="empty-state__text">
            {hasFilters
              ? 'No faculty match the current filters.'
              : 'Faculty accounts appear here once registered.'}
          </p>
          {hasFilters ? (
            <button type="button" className="btn btn--ghost" onClick={resetFilters}>
              Clear Filters
            </button>
          ) : null}
        </div>
      ) : null}

      {form ? (
        <div className="admin-form">
          <p className="admin-form__title">Edit faculty profile</p>
          <div className="admin-form__grid">
            <div className="field">
              <label className="field__label" htmlFor="fac-name">
                Name
              </label>
              <input
                id="fac-name"
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
              <label className="field__label" htmlFor="fac-email">
                Email
              </label>
              <input
                id="fac-email"
                className="field__input"
                type="email"
                value={values.email}
                onChange={(event) =>
                  setValues({ ...values, email: event.target.value })
                }
              />
              {fieldErrors.email ? (
                <p className="field__error">{fieldErrors.email}</p>
              ) : null}
            </div>
            <div className="field">
              <label className="field__label" htmlFor="fac-employee-id">
                Employee ID
              </label>
              <input
                id="fac-employee-id"
                className="field__input"
                type="text"
                value={values.employee_id}
                onChange={(event) =>
                  setValues({ ...values, employee_id: event.target.value })
                }
              />
            </div>
            <div className="field">
              <label className="field__label" htmlFor="fac-department">
                Department
              </label>
              <select
                id="fac-department"
                className="field__input"
                value={values.department_id}
                onChange={(event) =>
                  setValues({ ...values, department_id: event.target.value })
                }
              >
                <option value="">No department</option>
                {departments.map((department) => (
                  <option
                    key={department.department_id}
                    value={department.department_id}
                  >
                    {department.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label className="field__label" htmlFor="fac-designation">
                Designation
              </label>
              <input
                id="fac-designation"
                className="field__input"
                type="text"
                placeholder="e.g. Assistant Professor"
                value={values.designation}
                onChange={(event) =>
                  setValues({ ...values, designation: event.target.value })
                }
              />
            </div>
            <div className="field">
              <label className="field__label" htmlFor="fac-orcid">
                ORCID
              </label>
              <input
                id="fac-orcid"
                className="field__input"
                type="text"
                value={values.orcid_id}
                onChange={(event) =>
                  setValues({ ...values, orcid_id: event.target.value })
                }
              />
            </div>
            <div className="field">
              <label className="field__label" htmlFor="fac-scopus">
                Scopus author ID
              </label>
              <input
                id="fac-scopus"
                className="field__input"
                type="text"
                value={values.scopus_author_id}
                onChange={(event) =>
                  setValues({ ...values, scopus_author_id: event.target.value })
                }
              />
            </div>
            <div className="field">
              <label className="field__label" htmlFor="fac-wos">
                Web of Science researcher ID
              </label>
              <input
                id="fac-wos"
                className="field__input"
                type="text"
                value={values.web_of_science_researcher_id}
                onChange={(event) =>
                  setValues({
                    ...values,
                    web_of_science_researcher_id: event.target.value,
                  })
                }
              />
            </div>
            <div className="field">
              <label className="field__label" htmlFor="fac-pubmed">
                PubMed ID
              </label>
              <input
                id="fac-pubmed"
                className="field__input"
                type="text"
                value={values.pubmed_id}
                onChange={(event) =>
                  setValues({ ...values, pubmed_id: event.target.value })
                }
              />
            </div>
            <div className="field field--full">
              <label className="field__label" htmlFor="fac-interests">
                Research interests
              </label>
              <input
                id="fac-interests"
                className="field__input"
                type="text"
                placeholder="Comma separated, e.g. machine learning, networks"
                value={values.research_interests}
                onChange={(event) =>
                  setValues({ ...values, research_interests: event.target.value })
                }
              />
              <p className="admin-form__hint">
                Passwords are never edited from this screen.
              </p>
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

      {status === 'ready' && items.length > 0 ? (
        <>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">Name</th>
                  <th scope="col">Email</th>
                  <th scope="col">Department</th>
                  <th scope="col">Designation</th>
                  <th scope="col">Status</th>
                  <th scope="col">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {items.map((faculty) => (
                  <tr key={faculty.faculty_id}>
                    <td>{faculty.name}</td>
                    <td>{faculty.email}</td>
                    <td>{departmentProgramLabel(faculty.department_id)}</td>
                    <td>{faculty.designation || '—'}</td>
                    <td>
                      <span
                        className={`admin-badge ${
                          faculty.is_active
                            ? 'admin-badge--active'
                            : 'admin-badge--inactive'
                        }`}
                      >
                        {isActiveLabel(faculty.is_active)}
                      </span>
                    </td>
                    <td>
                      <div className="admin-actions">
                        <button
                          type="button"
                          className="btn btn--ghost btn--small"
                          onClick={() => openEdit(faculty)}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          className={
                            faculty.is_active
                              ? 'btn btn--danger-outline btn--small'
                              : 'btn btn--ghost btn--small'
                          }
                          onClick={() => requestToggle(faculty)}
                        >
                          {faculty.is_active ? 'Deactivate' : 'Activate'}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="admin-pager">
            <span>
              Showing {items.length} of {total} faculty · Page {page} of{' '}
              {totalPages}
            </span>
            <div className="admin-pager__controls">
              <button
                type="button"
                className="btn btn--ghost btn--small"
                disabled={page <= 1}
                onClick={() => setPage((value) => Math.max(1, value - 1))}
              >
                Previous
              </button>
              <button
                type="button"
                className="btn btn--ghost btn--small"
                disabled={page >= totalPages}
                onClick={() => setPage((value) => value + 1)}
              >
                Next
              </button>
            </div>
          </div>
        </>
      ) : null}

      {generatedPassword ? (
        <div className="dialog-backdrop" role="presentation">
          <div
            className="dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="gen-password-title"
          >
            <h2 className="dialog__title" id="gen-password-title">
              Faculty account created
            </h2>
            <p className="dialog__message">
              A secure temporary password was generated. Share it privately with
              the faculty member and ask them to change it after their first
              sign-in. It will not be shown again.
            </p>
            <div className="field">
              <label className="field__label" htmlFor="gen-password">
                Temporary password
              </label>
              <div className="field__input-group">
                <input
                  id="gen-password"
                  className="field__input"
                  type="text"
                  readOnly
                  value={generatedPassword}
                  onFocus={(event) => event.target.select()}
                />
                <button
                  type="button"
                  className="field__toggle"
                  onClick={copyGeneratedPassword}
                >
                  {copied ? 'Copied' : 'Copy password'}
                </button>
              </div>
            </div>
            <div className="dialog__actions">
              <button
                type="button"
                className="btn btn--primary"
                onClick={() => setGeneratedPassword('')}
              >
                Done
              </button>
            </div>
          </div>
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
