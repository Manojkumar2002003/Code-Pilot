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
  {
    label: 'Requirements',
    description: 'Store and organize the functional and non-functional requirements for this project.',
    status: 'Coming soon',
    route: 'requirements',
  },
  {
    label: 'Architecture',
    description: 'Document the system components and their relationships.',
    status: 'Coming soon',
    route: 'architecture',
  },
  {
    label: 'Tasks',
    description: 'Organize the implementation work associated with the project.',
    status: 'Coming soon',
    route: 'tasks',
  },
  {
    label: 'Activity',
    description: 'View project changes and future agent execution history.',
    status: 'Coming soon',
    route: 'activity',
  },
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

  const projectDescription = project.description?.trim() || 'No description provided.'

  return (
    <div className="workspace-overview">
      <div className="workspace-overview-header">
        <div className="workspace-header-title">
          <p className="eyebrow page-eyebrow">Project overview</p>
          <h1>{project.name}</h1>
        </div>

        <div className="project-action-row workspace-overview-actions">
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
      </div>

      {deleteError ? (
        <div className="form-error" role="alert">
          {deleteError}
        </div>
      ) : null}

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
        <div className="project-details-header-block workspace-overview-topline">
          <div className="workspace-overview-status-row">
            <span className={`project-badge project-badge-${project.status}`}>
              {project.status}
            </span>
          </div>
        </div>

        <div className="project-details-section">
          <h3>Description</h3>
          <p>{projectDescription}</p>
        </div>

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

      <section className="workspace-summary-section" aria-label="Workspace summary">
        <div className="workspace-summary-header">
          <p className="eyebrow page-eyebrow">Workspace areas</p>
          <h2>Project workspace</h2>
        </div>

        <div className="workspace-summary-grid">
          {workspaceSummaryCards.map((card) => (
            <Link key={card.label} to={`/projects/${project.id}/${card.route}`} className="workspace-summary-card-link">
              <article className="workspace-summary-card">
                <div className="workspace-summary-card-header">
                  <span className="workspace-summary-label">{card.label}</span>
                  <span className="workspace-summary-status">{card.status}</span>
                </div>
                <p>{card.description}</p>
              </article>
            </Link>
          ))}
        </div>
      </section>
    </div>
  )
}

export default ProjectWorkspaceOverviewPage
