import { Link } from 'react-router-dom'

function NotFoundPage() {
  return (
    <section className="page-panel">
      <div className="page-header">
        <p className="eyebrow page-eyebrow">Page</p>
        <h1>Page not found</h1>
      </div>

      <div className="state-panel error-state">
        <h3>We couldn’t find that page.</h3>
        <p>The route you requested does not exist or may no longer be available.</p>
        <div className="project-confirmation-actions">
          <Link to="/" className="secondary-button">
            Go to Dashboard
          </Link>
          <Link to="/projects" className="primary-button">
            Go to Projects
          </Link>
        </div>
      </div>
    </section>
  )
}

export default NotFoundPage
