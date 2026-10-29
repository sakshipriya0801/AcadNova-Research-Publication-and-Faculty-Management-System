import { useCallback, useEffect, useState } from 'react'
import { flushSync } from 'react-dom'
import LoadingScreen from '../components/LoadingScreen'
import FacultySummaryReport from '../components/reports/FacultySummaryReport'
import PointsReport from '../components/reports/PointsReport'
import PublicationReport from '../components/reports/PublicationReport'
import ReportFilters from '../components/reports/ReportFilters'
import ReportHeader from '../components/reports/ReportHeader'
import VerificationReport from '../components/reports/VerificationReport'
import { listAcademicYears } from '../services/academicYearService'
import { listDepartments } from '../services/departmentService'
import { getMyProfile } from '../services/facultyService'
import {
  academicYearOptions,
  preferredAcademicYearId,
} from '../utils/points'
import {
  REPORT_TYPES,
  getReportError,
  reportTypeLabel,
} from '../utils/reports'

const SUBTITLE =
  'View and generate research publication, verification, and annual performance reports.'

export default function ReportsPage() {
  const [years, setYears] = useState([])
  const [profile, setProfile] = useState(null)
  const [departments, setDepartments] = useState([])
  const [status, setStatus] = useState('loading')
  const [errorMessage, setErrorMessage] = useState('')
  const [reloadKey, setReloadKey] = useState(0)
  const [yearId, setYearId] = useState(null)
  const [reportType, setReportType] = useState(REPORT_TYPES[0].id)
  const [printStamp, setPrintStamp] = useState('')

  useEffect(() => {
    let cancelled = false
    setStatus('loading')
    Promise.all([listAcademicYears(), getMyProfile(), listDepartments()])
      .then(([yearsResponse, profileResponse, departmentsResponse]) => {
        if (cancelled) return
        const list = Array.isArray(yearsResponse.data) ? yearsResponse.data : []
        setYears(list)
        setProfile(profileResponse.data)
        setDepartments(
          Array.isArray(departmentsResponse.data) ? departmentsResponse.data : [],
        )
        setErrorMessage('')
        setStatus(list.length === 0 ? 'empty' : 'ready')
        setYearId((current) => {
          const valid = current && list.some((year) => year.academic_year_id === current)
          return valid ? current : preferredAcademicYearId(list)
        })
      })
      .catch((error) => {
        if (cancelled) return
        setErrorMessage(getReportError(error))
        setStatus('error')
      })
    return () => {
      cancelled = true
    }
  }, [reloadKey])

  const handlePrint = useCallback(() => {
    flushSync(() => setPrintStamp(new Date().toLocaleString()))
    window.print()
  }, [])

  if (status === 'loading') {
    return <LoadingScreen message="Loading reports…" />
  }

  if (status === 'error') {
    return (
      <div className="page reports-page">
        <ReportHeader subtitle={SUBTITLE} />
        <div className="empty-state">
          <p className="empty-state__title">Unable to load reports</p>
          <p className="empty-state__text">{errorMessage}</p>
          <button
            type="button"
            className="btn btn--primary"
            onClick={() => setReloadKey((key) => key + 1)}
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  if (status === 'empty') {
    return (
      <div className="page reports-page">
        <ReportHeader subtitle={SUBTITLE} />
        <div className="empty-state">
          <p className="empty-state__title">No academic year is available.</p>
          <p className="empty-state__text">
            Reports are grouped by academic year. Ask an administrator to
            create an academic year, then try again.
          </p>
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => setReloadKey((key) => key + 1)}
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  const selectedYear = years.find((year) => year.academic_year_id === yearId)
  const yearName = selectedYear ? selectedYear.name : ''
  const facultyName = profile ? profile.name : ''

  return (
    <div className="page reports-page">
      <ReportHeader
        subtitle={SUBTITLE}
        actions={
          <button type="button" className="btn btn--primary" onClick={handlePrint}>
            Print Report
          </button>
        }
      />

      <p className="print-only report-print-meta">
        {reportTypeLabel(reportType)} · {yearName} · {facultyName}
        {printStamp ? ` · Generated ${printStamp}` : ''}
      </p>

      <ReportFilters
        reportTypes={REPORT_TYPES}
        reportType={reportType}
        onReportTypeChange={setReportType}
        years={years}
        yearId={yearId}
        onYearChange={(value) => setYearId(value)}
      />

      {reportType === 'publications' ? (
        <PublicationReport
          key={`publications-${yearId}`}
          yearId={yearId}
          yearName={yearName}
        />
      ) : null}

      {reportType === 'points' ? (
        <PointsReport
          key={`points-${yearId}`}
          yearId={yearId}
          yearName={yearName}
          facultyName={facultyName}
        />
      ) : null}

      {reportType === 'verification' ? (
        <VerificationReport
          key={`verification-${yearId}`}
          yearId={yearId}
          yearName={yearName}
        />
      ) : null}

      {reportType === 'summary' ? (
        <FacultySummaryReport
          key={`summary-${yearId}`}
          yearId={yearId}
          yearName={yearName}
          profile={profile}
          departments={departments}
        />
      ) : null}
    </div>
  )
}
