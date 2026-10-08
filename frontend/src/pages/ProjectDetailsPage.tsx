import { useCallback, useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'

import ErrorState from '../components/common/ErrorState'
import LoadingState from '../components/common/LoadingState'
import { ApiError, deleteProject, getProject, type Project } from '../services/api'

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
  const navigate = useNavigate()
  const location = useLocation()
  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [deleteRequested, setDeleteRequested] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const successMessage = (location.state as { successMessage?: string } | null)?.successMessage ?? null

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
    setDeleteError(null)

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

  const handleDelete = async () => {
    if (!projectId || !project) {
      return
    }

    setDeleteError(null)
    setDeleting(true)

    try {
      await deleteProject(projectId)
      navigate('/projects', {
        state: {
          successMessage: `Project "${project.name}" deleted successfully.`,
        },
      })
    } catch (caughtError) {
      if (caughtError instanceof ApiError && caughtError.status === 404) {
        setNotFound(true)
        setDeleteRequested(false)
        return
      }

      if (caughtError instanceof ApiError) {
        setDeleteError(caughtError.message)
        return
      }

      setDeleteError('Unable to delete the project. Please try again.')
    } finally {
      setDeleting(false)
    }
  }

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

      {successMessage ? <div className="success-banner">{successMessage}</div> : null}
      {deleteError ? (
        <div className="form-error" role="alert">
          {deleteError}
        </div>
      ) : null}

      <div className="project-action-row">
        <Link to={`/projects/${project.id}/edit`} className="primary-button">
          Edit Project
        </Link>
        <button
          type="button"
          className="danger-button"
          onClick={() => setDeleteRequested(true)}
          aria-label={`Delete ${project.name}`}
        >
          Delete Project
        </button>
      </div>

      {deleteRequested ? (
        <div className="state-panel delete-confirmation">
          <h3>Delete project?</h3>
          <p>
            Are you sure you want to delete <strong>{project.name}</strong>? This action cannot be undone.
          </p>

          <div className="project-confirmation-actions">
            <button type="button" className="secondary-button" onClick={() => setDeleteRequested(false)}>
              Cancel
            </button>
            <button type="button" className="danger-button" onClick={handleDelete} disabled={deleting}>
              {deleting ? 'Deleting...' : 'Delete Project'}
            </button>
          </div>
        </div>
      ) : null}

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
