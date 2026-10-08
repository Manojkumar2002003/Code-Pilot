import { Link, useLocation } from 'react-router-dom'

function ProjectsPage() {
  const location = useLocation()
  const successMessage = (location.state as { successMessage?: string } | null)?.successMessage ?? null

  return (
    <section className="page-panel">
      <div className="page-header">
        <div>
          <p className="eyebrow page-eyebrow">Projects</p>
          <h1>Your projects</h1>
        </div>
      </div>

      {successMessage ? (
        <div className="success-banner" role="status" aria-live="polite">
          {successMessage}
        </div>
      ) : null}

      <div className="info-card empty-state-card">
        <h3>Projects will appear here</h3>
        <p>Project creation is available in the next step, while the full list experience is planned for the next sprint.</p>
        <Link to="/projects/new" className="action-button enabled">
          Create Project
        </Link>
      </div>
    </section>
  )
}

export default ProjectsPage
