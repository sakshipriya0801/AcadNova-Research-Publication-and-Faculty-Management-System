import { useState } from 'react'
import { getPublicationError } from '../utils/errors'
import { PUBLICATION_TYPES } from '../utils/publication'

function TextField({ id, label, hint, error, ...input }) {
  return (
    <div className="field">
      <label className="field__label" htmlFor={id}>
        {label}
      </label>
      <input
        {...input}
        id={id}
        className="field__input"
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined}
      />
      {hint && !error ? (
        <p className="field__hint" id={`${id}-hint`}>
          {hint}
        </p>
      ) : null}
      {error ? (
        <p className="field__error" id={`${id}-error`}>
          {error}
        </p>
      ) : null}
    </div>
  )
}

function TextAreaField({ id, label, hint, error, rows = 4, ...input }) {
  return (
    <div className="field">
      <label className="field__label" htmlFor={id}>
        {label}
      </label>
      <textarea
        {...input}
        id={id}
        rows={rows}
        className="field__input field__input--textarea"
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined}
      />
      {hint && !error ? (
        <p className="field__hint" id={`${id}-hint`}>
          {hint}
        </p>
      ) : null}
      {error ? (
        <p className="field__error" id={`${id}-error`}>
          {error}
        </p>
      ) : null}
    </div>
  )
}

function SelectField({ id, label, hint, error, children, ...input }) {
  return (
    <div className="field">
      <label className="field__label" htmlFor={id}>
        {label}
      </label>
      <select
        {...input}
        id={id}
        className="field__input"
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined}
      >
        {children}
      </select>
      {hint && !error ? (
        <p className="field__hint" id={`${id}-hint`}>
          {hint}
        </p>
      ) : null}
      {error ? (
        <p className="field__error" id={`${id}-error`}>
          {error}
        </p>
      ) : null}
    </div>
  )
}

const EMPTY_VALUES = {
  title: '',
  publication_type: '',
  sub_type: '',
  publication_date: '',
  authorsText: '',
  faculty_author_position: '',
  is_corresponding_author: false,
  journal_name: '',
  conference_name: '',
  publisher: '',
  doi: '',
  issn: '',
  isbn: '',
  volume: '',
  issue: '',
  pages: '',
  collaboration_type: '',
  external_institution: '',
  indexingText: '',
  keywordsText: '',
  abstract: '',
  source_url: '',
  pdf_url: '',
}

function toValues(publication) {
  if (!publication) return EMPTY_VALUES
  return {
    title: publication.title || '',
    publication_type: publication.publication_type || '',
    sub_type: publication.sub_type || '',
    publication_date: String(publication.publication_date || '').slice(0, 10),
    authorsText: (publication.authors || []).join('\n'),
    faculty_author_position: publication.faculty_author_position ?? '',
    is_corresponding_author: Boolean(publication.is_corresponding_author),
    journal_name: publication.journal_name || '',
    conference_name: publication.conference_name || '',
    publisher: publication.publisher || '',
    doi: publication.doi || '',
    issn: publication.issn || '',
    isbn: publication.isbn || '',
    volume: publication.volume || '',
    issue: publication.issue || '',
    pages: publication.pages || '',
    collaboration_type: publication.collaboration_type || '',
    external_institution: publication.external_institution || '',
    indexingText: (publication.indexing || []).join(', '),
    keywordsText: (publication.keywords || []).join(', '),
    abstract: publication.abstract || '',
    source_url: publication.source_url || '',
    pdf_url: publication.pdf_url || '',
  }
}

function splitAuthors(text) {
  return String(text)
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
}

function splitList(text) {
  return String(text)
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

function orNull(value) {
  const trimmed = String(value).trim()
  return trimmed ? trimmed : null
}

function buildPayload(values) {
  return {
    title: values.title.trim(),
    publication_type: values.publication_type,
    publication_date: values.publication_date,
    authors: splitAuthors(values.authorsText),
    faculty_author_position:
      values.faculty_author_position === ''
        ? null
        : Number(values.faculty_author_position),
    is_corresponding_author: Boolean(values.is_corresponding_author),
    sub_type: orNull(values.sub_type),
    journal_name: orNull(values.journal_name),
    conference_name: orNull(values.conference_name),
    publisher: orNull(values.publisher),
    doi: orNull(values.doi),
    issn: orNull(values.issn),
    isbn: orNull(values.isbn),
    volume: orNull(values.volume),
    issue: orNull(values.issue),
    pages: orNull(values.pages),
    collaboration_type: orNull(values.collaboration_type),
    external_institution: orNull(values.external_institution),
    keywords: splitList(values.keywordsText),
    indexing: splitList(values.indexingText),
    abstract: orNull(values.abstract),
    source_url: orNull(values.source_url),
    pdf_url: orNull(values.pdf_url),
  }
}

function validate(values) {
  const errors = {}
  const title = values.title.trim()
  if (!title) errors.title = 'Title is required.'
  else if (title.length > 1000) errors.title = 'Title must be 1000 characters or fewer.'

  if (!values.publication_type) errors.publication_type = 'Publication type is required.'

  if (!values.publication_date) {
    errors.publication_date = 'Publication date is required.'
  } else if (!/^\d{4}-\d{2}-\d{2}$/.test(values.publication_date)) {
    errors.publication_date = 'Enter a valid publication date.'
  }

  const authors = splitAuthors(values.authorsText)
  if (authors.length === 0) errors.authorsText = 'Add at least one author.'

  if (values.faculty_author_position !== '') {
    const position = Number(values.faculty_author_position)
    if (!Number.isInteger(position) || position < 1) {
      errors.faculty_author_position = 'Author position must be 1 or more.'
    } else if (authors.length > 0 && position > authors.length) {
      errors.faculty_author_position = `Position cannot exceed the number of authors (${authors.length}).`
    }
  }

  const doi = values.doi.trim()
  if (doi && (/\s/.test(doi) || doi.length > 200)) {
    errors.doi = 'Enter a valid DOI (no spaces).'
  }

  for (const key of ['source_url', 'pdf_url']) {
    const url = values[key].trim()
    if (url && !/^https?:\/\/\S+$/i.test(url)) {
      errors[key] = 'Enter a valid URL starting with http:// or https://'
    }
  }

  return errors
}

export default function PublicationForm({
  publication = null,
  submitLabel = 'Save',
  onSubmit,
}) {
  const [values, setValues] = useState(() => toValues(publication))
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  function updateField(field) {
    return (event) => {
      const value =
        event.target.type === 'checkbox' ? event.target.checked : event.target.value
      setValues((current) => ({ ...current, [field]: value }))
      setErrors((current) => ({ ...current, [field]: undefined }))
    }
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (submitting) return

    const nextErrors = validate(values)
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return

    setSubmitting(true)
    setFormError('')
    try {
      await onSubmit(buildPayload(values))
    } catch (error) {
      setFormError(getPublicationError(error))
      setSubmitting(false)
      return
    }
    setSubmitting(false)
  }

  return (
    <form className="pub-form" onSubmit={handleSubmit} noValidate>
      {formError ? (
        <p className="alert alert--danger" role="alert">
          {formError}
        </p>
      ) : null}

      <fieldset className="pub-form__section" disabled={submitting}>
        <legend className="pub-form__legend">Basics</legend>
        <div className="pub-form__grid pub-form__grid--wide">
          <TextField
            id="pub-title"
            label="Title"
            hint="Full title of the publication."
            error={errors.title}
            type="text"
            value={values.title}
            onChange={updateField('title')}
            maxLength={1000}
          />
          <SelectField
            id="pub-type"
            label="Publication type"
            error={errors.publication_type}
            value={values.publication_type}
            onChange={updateField('publication_type')}
          >
            <option value="">Select a publication type</option>
            {PUBLICATION_TYPES.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </SelectField>
          <TextField
            id="pub-subtype"
            label="Sub type"
            error={errors.sub_type}
            type="text"
            value={values.sub_type}
            onChange={updateField('sub_type')}
          />
          <TextField
            id="pub-date"
            label="Publication date"
            error={errors.publication_date}
            type="date"
            value={values.publication_date}
            onChange={updateField('publication_date')}
          />
        </div>
      </fieldset>

      <fieldset className="pub-form__section" disabled={submitting}>
        <legend className="pub-form__legend">Authors</legend>
        <TextAreaField
          id="pub-authors"
          label="Authors"
          hint="One author per line, in the order they appear."
          error={errors.authorsText}
          rows={4}
          value={values.authorsText}
          onChange={updateField('authorsText')}
        />
        <div className="pub-form__grid">
          <TextField
            id="pub-position"
            label="Your author position"
            hint="Optional. For example 1 for first author."
            error={errors.faculty_author_position}
            type="number"
            min="1"
            value={values.faculty_author_position}
            onChange={updateField('faculty_author_position')}
          />
          <div className="field pub-form__checkbox-field">
            <label className="pub-form__checkbox" htmlFor="pub-corresponding">
              <input
                id="pub-corresponding"
                type="checkbox"
                checked={values.is_corresponding_author}
                onChange={updateField('is_corresponding_author')}
                disabled={submitting}
              />
              <span>Corresponding author</span>
            </label>
          </div>
        </div>
      </fieldset>

      <fieldset className="pub-form__section" disabled={submitting}>
        <legend className="pub-form__legend">Journal / Conference details</legend>
        <div className="pub-form__grid">
          <TextField
            id="pub-journal"
            label="Journal name"
            error={errors.journal_name}
            type="text"
            value={values.journal_name}
            onChange={updateField('journal_name')}
          />
          <TextField
            id="pub-conference"
            label="Conference name"
            error={errors.conference_name}
            type="text"
            value={values.conference_name}
            onChange={updateField('conference_name')}
          />
          <TextField
            id="pub-publisher"
            label="Publisher"
            error={errors.publisher}
            type="text"
            value={values.publisher}
            onChange={updateField('publisher')}
          />
          <TextField
            id="pub-doi"
            label="DOI"
            hint="Optional. A DOI or a doi.org link."
            error={errors.doi}
            type="text"
            value={values.doi}
            onChange={updateField('doi')}
          />
          <TextField
            id="pub-volume"
            label="Volume"
            error={errors.volume}
            type="text"
            value={values.volume}
            onChange={updateField('volume')}
          />
          <TextField
            id="pub-issue"
            label="Issue"
            error={errors.issue}
            type="text"
            value={values.issue}
            onChange={updateField('issue')}
          />
          <TextField
            id="pub-pages"
            label="Pages"
            error={errors.pages}
            type="text"
            value={values.pages}
            onChange={updateField('pages')}
          />
          <TextField
            id="pub-issn"
            label="ISSN"
            error={errors.issn}
            type="text"
            value={values.issn}
            onChange={updateField('issn')}
          />
          <TextField
            id="pub-isbn"
            label="ISBN"
            error={errors.isbn}
            type="text"
            value={values.isbn}
            onChange={updateField('isbn')}
          />
        </div>
      </fieldset>

      <fieldset className="pub-form__section" disabled={submitting}>
        <legend className="pub-form__legend">Classification</legend>
        <div className="pub-form__grid">
          <TextField
            id="pub-collaboration"
            label="Collaboration type"
            error={errors.collaboration_type}
            type="text"
            value={values.collaboration_type}
            onChange={updateField('collaboration_type')}
          />
          <TextField
            id="pub-external"
            label="External institution"
            error={errors.external_institution}
            type="text"
            value={values.external_institution}
            onChange={updateField('external_institution')}
          />
          <TextField
            id="pub-indexing"
            label="Indexing"
            hint="Comma separated, e.g. Scopus, Web of Science"
            error={errors.indexing}
            type="text"
            value={values.indexingText}
            onChange={updateField('indexingText')}
          />
          <TextField
            id="pub-keywords"
            label="Keywords"
            hint="Comma separated."
            error={errors.keywords}
            type="text"
            value={values.keywordsText}
            onChange={updateField('keywordsText')}
          />
        </div>
      </fieldset>

      <fieldset className="pub-form__section" disabled={submitting}>
        <legend className="pub-form__legend">Summary &amp; links</legend>
        <TextAreaField
          id="pub-abstract"
          label="Abstract"
          error={errors.abstract}
          rows={5}
          value={values.abstract}
          onChange={updateField('abstract')}
        />
        <div className="pub-form__grid">
          <TextField
            id="pub-source-url"
            label="Publication URL"
            error={errors.source_url}
            type="url"
            placeholder="https://"
            value={values.source_url}
            onChange={updateField('source_url')}
          />
          <TextField
            id="pub-pdf-url"
            label="PDF URL"
            error={errors.pdf_url}
            type="url"
            placeholder="https://"
            value={values.pdf_url}
            onChange={updateField('pdf_url')}
          />
        </div>
      </fieldset>

      <div className="pub-form__actions">
        <button type="submit" className="btn btn--primary" disabled={submitting}>
          {submitting ? 'Saving…' : submitLabel}
        </button>
      </div>
    </form>
  )
}
