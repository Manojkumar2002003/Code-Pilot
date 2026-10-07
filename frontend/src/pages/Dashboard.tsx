function DashboardPage() {
  return (
    <section className="page-panel">
      <div className="page-header">
        <div>
          <p className="eyebrow page-eyebrow">Dashboard</p>
          <h1>Welcome to CodePilot</h1>
        </div>
      </div>

      <div className="hero-card">
        <h2>AI Software Engineering Platform</h2>
        <p>
          CodePilot is the foundation for collaborative AI-driven development workflows.
        </p>
      </div>

      <div className="stats-grid" aria-label="Dashboard metrics">
        <div className="stat-card">
          <span className="stat-label">Projects</span>
          <strong>0</strong>
        </div>
        <div className="stat-card">
          <span className="stat-label">Active Executions</span>
          <strong>0</strong>
        </div>
        <div className="stat-card">
          <span className="stat-label">Completed Runs</span>
          <strong>0</strong>
        </div>
      </div>

      <div className="info-card">
        <h3>Getting Started</h3>
        <p>Create your first project to begin.</p>
      </div>
    </section>
  )
}

export default DashboardPage
