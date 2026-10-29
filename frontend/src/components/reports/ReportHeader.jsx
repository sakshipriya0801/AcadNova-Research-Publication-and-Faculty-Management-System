export default function ReportHeader({ subtitle, actions }) {
  return (
    <div className="page__header">
      <div>
        <h1 className="page__title">Research Reports</h1>
        <p className="page__subtitle">{subtitle}</p>
      </div>
      {actions ? <div className="report-header__actions no-print">{actions}</div> : null}
    </div>
  )
}
