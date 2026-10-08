import { type FormEvent, useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import ErrorState from '../components/common/ErrorState'
import LoadingState from '../components/common/LoadingState'
import { ApiError, getProject, type Project, type ProjectStatus, type ProjectUpdateRequest, updateProject } from '../services/api'

function EditProjectPage() {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const [project, setProject] = useState<Project | null>(null)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [status, setStatus] = useState<ProjectStatus>('active')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
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
      setName(data.name)
      setDescription(data.description ?? '')
      setStatus(data.status)
    } catch (caughtError) {
      if (caughtError instanceof ApiError && caughtError.status === 404) {
        setNotFound(true)
        return
      }

      if (caughtError instanceof ApiError) {
        setError(caughtError.message)
        return
      }

      setError('Unable to load the project for editing.')
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    void loadProject()
  }, [loadProject])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (!projectId) {
      setNotFound(true)
      return
    }

    const trimmedName = name.trim()
    const trimmedDescription = description.trim()

    if (!trimmedName) {
      setError('Project name is required.')
      return
    }

    setError(null)
    setSubmitting(true)

    const payload: ProjectUpdateRequest = {
      name: trimmedName,
      description: trimmedDescription || null,
      status,
    }

    try {
      const updatedProject = await updateProject(projectId, payload)
      navigate(`/projects/${projectId}`, {
        state: {
          successMessage: `Project "${updatedProject.name}" updated successfully.`,
        },
      })
    } catch (caughtError) {
      if (caughtError instanceof ApiError && caughtError.status === 404) {
        setNotFound(true)
        return
      }

      if (caughtError instanceof ApiError) {
        setError(caughtError.message)
        return
      }

      setError('Unable to update the project. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return <LoadingState message="Loading project..." />
  }

  if (notFound) {
    return (
      <section className="page-panel">
        <div className="page-header">
          <p className="eyebrow page-eyebrow">Projects</p>
          <h1>Project not found</h1>
        </div>

        <div className="state-panel error-state">
          <h3>Project not found</h3>
          <p>The project may have been deleted or is no longer available.</p>
          <Link to="/projects" className="secondary-button">
            ← Back to Projects
          </Link>
        </div>
      </section>
    )
  }

  if (!project) {
    return (
      <section className="page-panel">
        <div className="page-header">
          <p className="eyebrow page-eyebrow">Projects</p>
          <h1>Edit project</h1>
        </div>

        <ErrorState
          title="Unable to load project"
          message={error ?? 'Unable to load the project for editing.'}
          onRetry={loadProject}
        />
      </section>
    )
  }

  return (
    <section className="page-panel">
      <div className="page-header">
        <p className="eyebrow page-eyebrow">Projects</p>
        <h1>Edit project</h1>
      </div>

      <div className="project-form-card">
        <form className="project-form" onSubmit={handleSubmit} noValidate>
          {error ? (
            <div className="form-error" role="alert">
              {error}
            </div>
          ) : null}

          <div className="field-group">
            <label htmlFor="project-name">Project name</label>
            <input
              id="project-name"
              name="project-name"
              type="text"
              value={name}
              onChange={(event) => {
                setName(event.target.value)
                if (error) setError(null)
              }}
              placeholder="Enter a project name"
              maxLength={100}
            />
          </div>

          <div className="field-group">
            <label htmlFor="project-description">Description</label>
            <textarea
              id="project-description"
              name="project-description"
              value={description}
              onChange={(event) => {
                setDescription(event.target.value)
                if (error) setError(null)
              }}
              rows={5}
              placeholder="Optional project summary"
              maxLength={2000}
            />
            <div className="field-meta">
              <span>Optional</span>
              <span>{description.length}/2000</span>
            </div>
          </div>

          <div className="field-group">
            <label htmlFor="project-status">Status</label>
            <select
              id="project-status"
              name="project-status"
              value={status}
              onChange={(event) => setStatus(event.target.value as ProjectStatus)}
            >
              <option value="active">Active</option>
              <option value="archived">Archived</option>
            </select>
          </div>

          <div className="form-actions">
            <button type="button" className="secondary-button" onClick={() => navigate(`/projects/${projectId}`)}>
              Cancel
            </button>
            <button type="submit" className="primary-button" disabled={submitting} aria-live="polite">
              {submitting ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </section>
  )
}

export default EditProjectPage
