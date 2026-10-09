import { useState } from 'react'
import { Link, useNavigate, useOutletContext } from 'react-router-dom'

import { ApiError, deleteProject } from '../services/api'
import type { WorkspaceOutletContext } from '../components/workspace/ProjectWorkspaceLayout'

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

const workspaceSummaryCards = [
  { label: 'Requirements', state: 'Not started' },
  { label: 'Architecture', state: 'Coming soon' },
  { label: 'Tasks', state: 'Not available yet' },
  { label: 'Activity', state: 'Coming soon' },
]

function ProjectWorkspaceOverviewPage() {
  const { project } = useOutletContext<WorkspaceOutletContext>()
  const navigate = useNavigate()
  const [deleteRequested, setDeleteRequested] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const handleDelete = async () => {
    setDeleteError(null)
    setDeleting(true)

    try {
      await deleteProject(project.id)
      navigate('/projects', {
        state: {
          successMessage: `Project "${project.name}" deleted successfully.`,
        },
      })
    } catch (caughtError) {
      if (caughtError instanceof ApiError && caughtError.status === 404) {
        setDeleteRequested(false)
        setDeleteError('This project was already removed.')
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

  const projectDescription = project.description?.trim()

  return (
    <div className="workspace-overview">
      <div className="workspace-summary-grid">
        {workspaceSummaryCards.map((card) => (
          <article key={card.label} className="workspace-summary-card">
            <span className="workspace-summary-label">{card.label}</span>
            <strong>{card.state}</strong>
          </article>
        ))}
      </div>

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

      <article className="project-details-card workspace-details-card">
        <div className="project-details-header-block">
          <p className="eyebrow page-eyebrow">Overview</p>
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
    </div>
  )
}

export default ProjectWorkspaceOverviewPage
