// Single source of truth for the common faculty-profile fields shared by the
// public registration form and the admin "Add Faculty" form.

export const DEPARTMENT_PROGRAMS = ['MCA', 'BCA', 'MBA', 'BBA']

export const DESIGNATION_OPTIONS = [
  'Professor',
  'Associate Professor',
  'Assistant Professor',
  'Lecturer',
  'Visiting Faculty',
]

export const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

// Validates the five common fields (name, email, employee_id, department,
// designation).  ``employee_id`` is optional so it is only trimmed by the
// caller.  Returns an object of field-name -> message; empty when valid.
export function validateFacultyProfile({ name, email, department, designation } = {}) {
  const errors = {}
  if (!String(name || '').trim()) errors.name = 'Full name is required.'
  if (!String(email || '').trim()) errors.email = 'Email address is required.'
  else if (!EMAIL_PATTERN.test(String(email).trim())) errors.email = 'Enter a valid email address.'
  if (!department) errors.department = 'Select a department.'
  if (!designation) errors.designation = 'Select a designation.'
  return errors
}
