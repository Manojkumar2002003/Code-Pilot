import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import ErrorState from '../components/common/ErrorState'
import LoadingState from '../components/common/LoadingState'
import { ApiError, getProject, type Project } from '../services/api'

function formatProjectDate(value: string): string {
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return 'Unknown date'
  }

  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(parsed)
}

function ProjectDetailsPage() {
  const { projectId } = useParams()
  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notFound, setNotFound] = useState(false)

  const loadProject = useCallback(async () => {
    if (!projectId) {
      setNotFound(true)
      setError(null)
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)
    setNotFound(false)

    try {
      const data = await getProject(projectId)
      setProject(data)
    } catch (caughtError) {
      if (caughtError instanceof ApiError && caughtError.status === 404) {
        setNotFound(true)
        return
      }

      if (caughtError instanceof ApiError) {
        setError(caughtError.message)
        return
      }

      setError('Unable to load the project. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    void loadProject()
  }, [loadProject])

  if (loading) {
    return <LoadingState message="Loading project..." />
  }

  if (notFound) {
    return (
      <section className="page-panel">
        <div className="page-header">
          <p className="eyebrow page-eyebrow">Project</p>
          <h1>Project not found</h1>
        </div>

        <div className="state-panel error-state">
          <h3>Project not found</h3>
          <p>This project may have been deleted or the URL may be incorrect.</p>
          <Link to="/projects" className="secondary-button">
            ← Back to Projects
          </Link>
        </div>
      </section>
    )
  }

  if (error || !project) {
    return (
      <section className="page-panel">
        <div className="page-header">
          <p className="eyebrow page-eyebrow">Project</p>
          <h1>Project details</h1>
        </div>

        <ErrorState title="Unable to load project" message={error ?? 'Unable to load the project.'} onRetry={loadProject} />
      </section>
    )
  }

  const projectDescription = project.description?.trim()

  return (
    <section className="page-panel project-details-page">
      <div className="page-header project-details-header">
        <Link to="/projects" className="secondary-button project-nav-button">
          ← Back to Projects
        </Link>
      </div>

      <article className="project-details-card">
        <div className="project-details-header-block">
          <p className="eyebrow page-eyebrow">Project</p>
          <h1>{project.name}</h1>
          <span className={`project-badge project-badge-${project.status}`}>
            {project.status}
          </span>
        </div>

        {projectDescription ? (
          <div className="project-details-section">
            <h3>Description</h3>
            <p>{projectDescription}</p>
          </div>
        ) : (
          <div className="project-details-section muted-section">
            <h3>Description</h3>
            <p>No description provided.</p>
          </div>
        )}

        <div className="project-details-meta-grid">
          <div className="project-details-meta-item">
            <span className="meta-label">Project ID</span>
            <strong>{project.id}</strong>
          </div>
          <div className="project-details-meta-item">
            <span className="meta-label">Status</span>
            <strong>{project.status}</strong>
          </div>
          <div className="project-details-meta-item">
            <span className="meta-label">Created</span>
            <strong>{formatProjectDate(project.created_at)}</strong>
          </div>
          <div className="project-details-meta-item">
            <span className="meta-label">Updated</span>
            <strong>{formatProjectDate(project.updated_at)}</strong>
          </div>
        </div>
      </article>
    </section>
  )
}

export default ProjectDetailsPage
