function ProjectsPage() {
  return (
    <section className="page-panel">
      <div className="page-header">
        <div>
          <p className="eyebrow page-eyebrow">Projects</p>
          <h1>Your projects</h1>
        </div>
      </div>

      <div className="info-card empty-state-card">
        <h3>Projects will appear here</h3>
        <p>Project management and creation are planned for a future sprint.</p>
        <button type="button" className="action-button" disabled>
          Create Project
        </button>
      </div>
    </section>
  )
}

export default ProjectsPage
