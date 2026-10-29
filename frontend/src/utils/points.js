import { getErrorMessage } from './errors'

// Fixed keys of the backend PointsSummaryResponse.category_points schema.
export const CATEGORY_LABELS = [
  { key: 'research_publication', label: 'Research publication' },
  { key: 'book', label: 'Book' },
  { key: 'conference', label: 'Conference' },
  { key: 'patent', label: 'Patent' },
  { key: 'copyright', label: 'Copyright' },
  { key: 'project', label: 'Project' },
  { key: 'other', label: 'Other' },
]

export function getPointsError(
  error,
  fallback = 'Unable to load points. Please try again.',
) {
  if (!error || !error.response) return 'Unable to connect to the server.'
  const status = error.response.status
  if (status === 401) return 'Your session has expired. Please sign in again.'
  if (status === 403) return 'You do not have permission to view points.'
  if (status === 404) return 'Academic year not found.'
  return getErrorMessage(error, fallback)
}

export function categoryEntries(categoryPoints) {
  return CATEGORY_LABELS.map(({ key, label }) => ({
    key,
    label,
    points: Number(categoryPoints?.[key]) || 0,
  }))
}

export function academicYearOptions(years) {
  if (!Array.isArray(years)) return []
  return years.map((year) => ({
    id: year.academic_year_id,
    label: year.is_current ? `${year.name} (Current)` : year.name,
    isCurrent: Boolean(year.is_current),
  }))
}

export function preferredAcademicYearId(years) {
  if (!Array.isArray(years) || years.length === 0) return null
  const current = years.find((year) => year.is_current)
  return (current || years[0]).academic_year_id || null
}

export function formatDesignation(value) {
  if (!value || typeof value !== 'string') return null
  return value
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

// Presentation-only progress percentage. Never used to award or verify points.
export function progressPercent(totalPoints, requiredPoints) {
  const total = Number(totalPoints)
  const required = Number(requiredPoints)
  if (!Number.isFinite(total) || !Number.isFinite(required) || required <= 0) {
    return null
  }
  const percent = (total / required) * 100
  return Math.max(0, Math.min(100, Math.round(percent)))
}

export function eligibilityStatus(eligibility) {
  if (!eligibility) {
    return {
      kind: 'unknown',
      label: 'No points data available',
      message: 'Points data is unavailable for this academic year.',
    }
  }
  const required = eligibility.required_points
  const designation = formatDesignation(eligibility.designation)
  if (required === null || required === undefined) {
    return {
      kind: 'unknown',
      label: 'No points data available',
      message:
        eligibility.reason ||
        'No points data is available for your designation.',
    }
  }
  if (eligibility.eligible) {
    return {
      kind: 'eligible',
      label: 'Eligible',
      message: designation
        ? `You meet the required points for ${designation}.`
        : 'You meet the required points.',
    }
  }
  const remaining = eligibility.remaining_points
  return {
    kind: 'not-yet',
    label: 'Not Yet Eligible',
    message:
      remaining !== null && remaining !== undefined
        ? `${remaining} point${remaining === 1 ? '' : 's'} remaining${
            designation ? ` for ${designation}` : ''
          }.`
        : designation
          ? `Required points not yet met for ${designation}.`
          : 'Required points not yet met.',
  }
}
