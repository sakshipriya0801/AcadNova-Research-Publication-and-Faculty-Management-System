import { academicYearOptions } from '../../utils/points'

export default function ReportFilters({
  reportTypes,
  reportType,
  onReportTypeChange,
  years,
  yearId,
  onYearChange,
  children,
}) {
  return (
    <section className="report-filters no-print" aria-label="Report filters">
      <div className="report-filters__types" role="group" aria-label="Report type">
        {reportTypes.map((type) => {
          const active = type.id === reportType
          return (
            <button
              key={type.id}
              type="button"
              className={`report-filters__type${
                active ? ' report-filters__type--active' : ''
              }`}
              aria-pressed={active}
              onClick={() => onReportTypeChange(type.id)}
            >
              {type.label}
            </button>
          )
        })}
      </div>

      <div className="report-filters__row">
        <div className="field report-filters__year">
          <label className="field__label" htmlFor="report-academic-year">
            Academic year
          </label>
          <select
            id="report-academic-year"
            className="field__input"
            value={yearId || ''}
            onChange={(event) => onYearChange(event.target.value)}
          >
            {academicYearOptions(years).map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        {children}
      </div>
    </section>
  )
}
