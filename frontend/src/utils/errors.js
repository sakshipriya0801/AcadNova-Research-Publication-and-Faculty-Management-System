const SAFE_DETAIL = /^[\w\s.,'’!?:()\-–—%]+$/

function extractDetail(error) {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail.trim()
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') return item
        return typeof item?.msg === 'string' ? item.msg : ''
      })
      .filter(Boolean)
      .join(' ')
      .trim()
  }
  return null
}

function isSafe(detail) {
  return Boolean(detail) && detail.length <= 200 && SAFE_DETAIL.test(detail)
}

export function getErrorMessage(
  error,
  fallback = 'Something went wrong. Please try again.',
) {
  if (!error?.response) return 'Unable to connect to the server.'

  const status = error.response.status
  if (status === 401) return 'Your session has expired. Please sign in again.'
  if (status === 403) return 'You do not have permission to perform this action.'
  if (status === 404) return 'The requested resource was not found.'
  if (status === 503) return 'The service is temporarily unavailable. Please try again later.'
  if (status >= 500) return 'Something went wrong. Please try again.'

  const detail = extractDetail(error)
  if (isSafe(detail)) return detail
  return fallback
}

export function getLoginError(error) {
  const fallback = 'Unable to sign in. Please check your credentials and try again.'
  if (!error?.response) return 'Unable to connect to the server.'
  if (error.response.status === 401) return fallback
  if (error.response.status === 403) {
    const detail = extractDetail(error)
    if (isSafe(detail)) return detail
    return fallback
  }
  return getErrorMessage(error, fallback)
}

export function getRegisterError(error) {
  const fallback = 'Unable to create the account. Please review your details and try again.'
  if (!error?.response) return 'Unable to connect to the server.'
  return getErrorMessage(error, fallback)
}

export function getPublicationError(error) {
  if (!error?.response) return 'Unable to connect to the server.'
  const status = error.response.status
  if (status === 403) return "You don't have permission to modify this publication."
  if (status === 404) return 'Publication not found.'
  return getErrorMessage(error, 'Something went wrong. Please try again.')
}

export function getRagQueryError(error) {
  if (!error?.response) return 'Unable to connect to the server.'
  const status = error.response.status
  if (status === 401) return 'Your session has expired. Please sign in again.'
  if (status === 403) return 'You do not have permission to access these documents.'
  if (status === 404) return 'Requested document or publication was not found.'
  if (status === 400 || status === 422) return 'Please enter a valid research question.'
  if (status === 503) return 'Research AI is temporarily unavailable.'
  if (status >= 500) return 'Research AI is temporarily unavailable.'
  return 'Something went wrong while analyzing your research.'
}
