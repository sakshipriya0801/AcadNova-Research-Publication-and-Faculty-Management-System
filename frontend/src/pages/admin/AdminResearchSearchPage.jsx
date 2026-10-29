import ResearchSearchPanel from '../../components/ResearchSearchPanel'

export default function AdminResearchSearchPage() {
  return (
    <div className="page admin-page">
      <div className="page__header">
        <div>
          <h1 className="page__title">Research Search</h1>
          <p className="page__subtitle">
            Search publications across faculty profiles and external sources. Internal
            records link to the review queue; external records can be imported.
          </p>
        </div>
      </div>
      <ResearchSearchPanel />
    </div>
  )
}
