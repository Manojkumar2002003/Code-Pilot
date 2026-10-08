import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import EmptyState from '../components/common/EmptyState'
import ErrorState from '../components/common/ErrorState'
import LoadingState from '../components/common/LoadingState'
import { ApiError, getProjects, type Project } from '../services/api'

function formatProjectDate(value: string): string {
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return 'Unknown date'
  }

  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(parsed)
}

function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadProjects = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await getProjects()
      setProjects(data)
    } catch (caughtError) {
      if (caughtError instanceof ApiError) {
        setError(caughtError.message)
        return
      }

      setError('Unable to load projects. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadProjects()
  }, [loadProjects])

  return (
    <section className="page-panel">
      <div className="page-header project-list-header">
        <div>
          <p className="eyebrow page-eyebrow">Projects</p>
          <h1>Your projects</h1>
        </div>

        <Link to="/projects/new" className="action-button enabled project-create-button">
          + Create Project
        </Link>
      </div>

      {loading ? (
        <LoadingState message="Loading projects..." />
      ) : error ? (
        <ErrorState title="Unable to load projects" message={error} onRetry={loadProjects} />
      ) : projects.length === 0 ? (
        <div className="empty-project-panel">
          <EmptyState
            title="No projects yet"
            description="Create your first CodePilot project to get started."
          />
          <div className="empty-project-action">
            <Link to="/projects/new" className="action-button enabled">
              Create Project
            </Link>
          </div>
        </div>
      ) : (
        <div className="project-list-grid">
          {projects.map((project) => (
            <article key={project.id} className="project-card" aria-label={`Project ${project.name}`}>
              <div className="project-card-header">
                <div>
                  <h3>{project.name}</h3>
                </div>
                <span className={`project-badge project-badge-${project.status}`}>
                  {project.status}
                </span>
              </div>

              <p className="project-description">
                {project.description?.trim() ? project.description.trim() : 'No description'}
              </p>

              <div className="project-meta">
                <span>Created {formatProjectDate(project.created_at)}</span>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}

export default ProjectsPage
