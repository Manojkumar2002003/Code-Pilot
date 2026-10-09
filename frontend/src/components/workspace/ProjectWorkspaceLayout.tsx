import { useCallback, useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useParams } from 'react-router-dom'

import ErrorState from '../common/ErrorState'
import LoadingState from '../common/LoadingState'
import { ApiError, getProject, type Project } from '../../services/api'

export type WorkspaceOutletContext = {
  project: Project
}

const workspaceSections = [
  { path: '', label: 'Overview', end: true },
  { path: 'requirements', label: 'Requirements' },
  { path: 'architecture', label: 'Architecture' },
  { path: 'tasks', label: 'Tasks' },
  { path: 'activity', label: 'Activity' },
]

function ProjectWorkspaceLayout() {
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

      setError('Unable to load this project workspace. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    void loadProject()
  }, [loadProject])

  if (loading) {
    return <LoadingState message="Loading project workspace..." />
  }

  if (notFound) {
    return (
      <section className="page-panel">
        <div className="page-header">
          <p className="eyebrow page-eyebrow">Project Workspace</p>
          <h1>Project not found</h1>
        </div>

        <div className="state-panel error-state">
          <h3>Project not found</h3>
          <p>The requested workspace no longer exists or the URL is invalid.</p>
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
          <p className="eyebrow page-eyebrow">Project Workspace</p>
          <h1>Workspace unavailable</h1>
        </div>

        <ErrorState
          title="Unable to load project workspace"
          message={error ?? 'Unable to load this project workspace.'}
          onRetry={loadProject}
        />
      </section>
    )
  }

  return (
    <section className="workspace-shell page-panel" aria-label={`${project.name} workspace`}>
      <div className="workspace-header">
        <div className="workspace-header-top">
          <Link to="/projects" className="secondary-button workspace-back-button">
            ← Back to Projects
          </Link>
        </div>

        <div className="workspace-header-title">
          <p className="eyebrow page-eyebrow">Project Workspace</p>
          <h1>{project.name}</h1>
        </div>
      </div>

      <nav className="workspace-tabs" aria-label="Project sections">
        {workspaceSections.map((section) => {
          const target = section.path ? `/projects/${project.id}/${section.path}` : `/projects/${project.id}`

          return (
            <NavLink
              key={section.path || 'overview'}
              to={target}
              end={section.path === ''}
              className={({ isActive }) =>
                `workspace-tab ${isActive ? 'workspace-tab-active' : ''}`
              }
            >
              {section.label}
            </NavLink>
          )
        })}
      </nav>

      <div className="workspace-content">
        <Outlet context={{ project }} />
      </div>
    </section>
  )
}

export default ProjectWorkspaceLayout
