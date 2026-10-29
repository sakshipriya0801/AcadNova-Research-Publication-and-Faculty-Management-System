import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import LoadingScreen from '../components/LoadingScreen'
import { useAuth } from '../hooks/useAuth'
import { listDepartments } from '../services/departmentService'
import { getMyProfile, updateMyProfile } from '../services/facultyService'
import { getErrorMessage } from '../utils/errors'
import { formatDate } from '../utils/publication'
import {
  departmentName,
  isActiveLabel,
  joinList,
  splitList,
} from '../utils/admin'

const EMPTY_FORM = {
  name: '',
  designation: '',
  department_id: '',
  orcid_id: '',
  scopus_author_id: '',
  web_of_science_researcher_id: '',
  pubmed_id: '',
  profile_photo_url: '',
  research_interests: '',
}

function InfoRow({ label, value }) {
  return (
    <div className="profile-info__row">
      <dt className="profile-info__label">{label}</dt>
      <dd className="profile-info__value">{value || '—'}</dd>
    </div>
  )
}

export default function ProfilePage() {
  const { refreshUser } = useAuth()
  const [profile, setProfile] = useState(null)
  const [departments, setDepartments] = useState([])
  const [status, setStatus] = useState('loading')
  const [errorMessage, setErrorMessage] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  const [editing, setEditing] = useState(false)
  const [values, setValues] = useState(EMPTY_FORM)
  const [fieldErrors, setFieldErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState('')

  const load = useCallback(() => {
    setStatus('loading')
    Promise.all([
      getMyProfile(),
      listDepartments().catch(() => ({ data: [] })),
    ])
      .then(([profileResponse, departmentsResponse]) => {
        setProfile(profileResponse.data)
        setDepartments(departmentsResponse.data || [])
        setStatus('ready')
      })
      .catch((error) => {
        setErrorMessage(getErrorMessage(error, 'Unable to load your profile.'))
        setStatus('error')
      })
  }, [reloadKey])

  useEffect(() => {
    load()
  }, [load])

  const openEdit = () => {
    setValues({
      name: profile?.name || '',
      designation: profile?.designation || '',
      department_id: profile?.department_id || '',
      orcid_id: profile?.orcid_id || '',
      scopus_author_id: profile?.scopus_author_id || '',
      web_of_science_researcher_id: profile?.web_of_science_researcher_id || '',
      pubmed_id: profile?.pubmed_id || '',
      profile_photo_url: profile?.profile_photo_url || '',
      research_interests: joinList(profile?.research_interests),
    })
    setFieldErrors({})
    setFormError('')
    setEditing(true)
  }

  const save = async () => {
    const errors = {}
    if (!values.name.trim()) errors.name = 'Name is required.'
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    setSaving(true)
    setFormError('')
    try {
      const { data } = await updateMyProfile({
        name: values.name.trim(),
        designation: values.designation.trim() || null,
        department_id: values.department_id || null,
        orcid_id: values.orcid_id.trim() || null,
        scopus_author_id: values.scopus_author_id.trim() || null,
        web_of_science_researcher_id:
          values.web_of_science_researcher_id.trim() || null,
        pubmed_id: values.pubmed_id.trim() || null,
        profile_photo_url: values.profile_photo_url.trim() || null,
        research_interests: splitList(values.research_interests),
      })
      setProfile(data)
      setEditing(false)
      setNotice('Profile updated.')
      await refreshUser()
    } catch (error) {
      setFormError(getErrorMessage(error, 'Unable to save your profile.'))
    } finally {
      setSaving(false)
    }
  }

  if (status === 'loading') {
    return <LoadingScreen message="Loading your profile…" />
  }

  if (status === 'error') {
    const notFound = errorMessage === 'The requested resource was not found.'
    return (
      <div className="page profile-page">
        <div className="page__header">
          <div>
            <h1 className="page__title">My Profile</h1>
          </div>
        </div>
        <div className="empty-state">
          <p className="empty-state__title">
            {notFound ? 'No faculty profile linked to this account' : 'Unable to load your profile'}
          </p>
          <p className="empty-state__text">
            {notFound
              ? 'Administrator accounts do not carry a faculty profile. Faculty members can edit their details here.'
              : errorMessage}
          </p>
          <Link className="btn btn--primary" to="/dashboard">
            Back to Dashboard
          </Link>
        </div>
      </div>
    )
  }

  const isActive = profile?.is_active !== false

  return (
    <div className="page profile-page">
      <div className="page__header">
        <div>
          <h1 className="page__title">My Profile</h1>
          <p className="page__subtitle">
            Your faculty details as stored by the institution. Email and
            employee ID are maintained by the administration.
          </p>
        </div>
        <div className="page__header-actions">
          {!editing ? (
            <button type="button" className="btn btn--primary" onClick={openEdit}>
              Edit Profile
            </button>
          ) : null}
        </div>
      </div>

      {notice ? (
        <div className="alert alert--success" role="status">
          <span>{notice}</span>
        </div>
      ) : null}

      <div className="profile-layout">
        <section className="profile-card" aria-labelledby="profile-details-title">
          <div className="profile-card__header">
            <span className="profile-card__avatar" aria-hidden="true">
              {(profile?.name || '?')
                .split(/\s+/)
                .map((part) => part[0])
                .filter(Boolean)
                .slice(0, 2)
                .join('')
                .toUpperCase()}
            </span>
            <div>
              <h2 className="profile-card__title" id="profile-details-title">
                {profile?.name}
              </h2>
              <p className="profile-card__meta">
                {profile?.designation || 'No designation set'}
                {' · '}
                <span
                  className={`admin-badge ${
                    isActive ? 'admin-badge--active' : 'admin-badge--inactive'
                  }`}
                >
                  {isActiveLabel(isActive)}
                </span>
              </p>
            </div>
          </div>

          <dl className="profile-info">
            <InfoRow label="Email" value={profile?.email} />
            <InfoRow label="Employee ID" value={profile?.employee_id} />
            <InfoRow
              label="Department"
              value={departmentName(departments, profile?.department_id)}
            />
            <InfoRow label="ORCID" value={profile?.orcid_id} />
            <InfoRow label="Scopus author ID" value={profile?.scopus_author_id} />
            <InfoRow
              label="Web of Science researcher ID"
              value={profile?.web_of_science_researcher_id}
            />
            <InfoRow label="PubMed ID" value={profile?.pubmed_id} />
            <InfoRow
              label="Research interests"
              value={joinList(profile?.research_interests)}
            />
            <InfoRow label="Member since" value={formatDate(profile?.created_at)} />
          </dl>
        </section>

        {editing ? (
          <section className="admin-form profile-form" aria-labelledby="profile-edit-title">
            <p className="admin-form__title" id="profile-edit-title">
              Edit profile
            </p>
            <div className="admin-form__grid">
              <div className="field field--full">
                <label className="field__label" htmlFor="profile-name">
                  Name
                </label>
                <input
                  id="profile-name"
                  className="field__input"
                  type="text"
                  value={values.name}
                  aria-invalid={Boolean(fieldErrors.name)}
                  aria-describedby={fieldErrors.name ? 'profile-name-error' : undefined}
                  onChange={(event) =>
                    setValues({ ...values, name: event.target.value })
                  }
                />
                {fieldErrors.name ? (
                  <p className="field__error" id="profile-name-error">
                    {fieldErrors.name}
                  </p>
                ) : null}
              </div>
              <div className="field">
                <label className="field__label" htmlFor="profile-designation">
                  Designation
                </label>
                <input
                  id="profile-designation"
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
                <label className="field__label" htmlFor="profile-department">
                  Department
                </label>
                <select
                  id="profile-department"
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
                <label className="field__label" htmlFor="profile-orcid">
                  ORCID
                </label>
                <input
                  id="profile-orcid"
                  className="field__input"
                  type="text"
                  value={values.orcid_id}
                  onChange={(event) =>
                    setValues({ ...values, orcid_id: event.target.value })
                  }
                />
              </div>
              <div className="field">
                <label className="field__label" htmlFor="profile-scopus">
                  Scopus author ID
                </label>
                <input
                  id="profile-scopus"
                  className="field__input"
                  type="text"
                  value={values.scopus_author_id}
                  onChange={(event) =>
                    setValues({ ...values, scopus_author_id: event.target.value })
                  }
                />
              </div>
              <div className="field">
                <label className="field__label" htmlFor="profile-wos">
                  Web of Science researcher ID
                </label>
                <input
                  id="profile-wos"
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
                <label className="field__label" htmlFor="profile-pubmed">
                  PubMed ID
                </label>
                <input
                  id="profile-pubmed"
                  className="field__input"
                  type="text"
                  value={values.pubmed_id}
                  onChange={(event) =>
                    setValues({ ...values, pubmed_id: event.target.value })
                  }
                />
              </div>
              <div className="field field--full">
                <label className="field__label" htmlFor="profile-interests">
                  Research interests
                </label>
                <input
                  id="profile-interests"
                  className="field__input"
                  type="text"
                  placeholder="Comma separated, e.g. machine learning, networks"
                  value={values.research_interests}
                  onChange={(event) =>
                    setValues({
                      ...values,
                      research_interests: event.target.value,
                    })
                  }
                />
              </div>
              <div className="field field--full">
                <label className="field__label" htmlFor="profile-photo">
                  Profile photo URL
                </label>
                <input
                  id="profile-photo"
                  className="field__input"
                  type="url"
                  value={values.profile_photo_url}
                  onChange={(event) =>
                    setValues({ ...values, profile_photo_url: event.target.value })
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
                onClick={save}
              >
                {saving ? 'Saving…' : 'Save Changes'}
              </button>
              <button
                type="button"
                className="btn btn--ghost"
                disabled={saving}
                onClick={() => setEditing(false)}
              >
                Cancel
              </button>
            </div>
          </section>
        ) : null}
      </div>
    </div>
  )
}
