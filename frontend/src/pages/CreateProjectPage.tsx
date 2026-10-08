import { type FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { ApiError, createProject, type ProjectCreateRequest } from '../services/api'

function CreateProjectPage() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [validationError, setValidationError] = useState('')
  const [apiError, setApiError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const trimmedName = name.trim()
    const trimmedDescription = description.trim()

    if (!trimmedName) {
      setValidationError('Project name is required.')
      setApiError('')
      return
    }

    setValidationError('')
    setApiError('')
    setSubmitting(true)

    const payload: ProjectCreateRequest = {
      name: trimmedName,
      description: trimmedDescription || null,
    }

    try {
      const createdProject = await createProject(payload)
      navigate('/projects', {
        state: {
          successMessage: `Project "${createdProject.name}" created successfully.`,
        },
      })
    } catch (error) {
      if (error instanceof ApiError) {
        setApiError(error.message)
        return
      }

      setApiError('Unable to create the project. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="page-panel">
      <div className="page-header">
        <p className="eyebrow page-eyebrow">Projects</p>
        <h1>Create project</h1>
      </div>

      <div className="project-form-card">
        <form className="project-form" onSubmit={handleSubmit} noValidate>
          {apiError ? (
            <div className="form-error" role="alert">
              {apiError}
            </div>
          ) : null}

          <div className="field-group">
            <label htmlFor="project-name">Project name</label>
            <input
              id="project-name"
              name="project-name"
              type="text"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Enter a project name"
              aria-invalid={Boolean(validationError)}
              aria-describedby={validationError ? 'project-name-error' : undefined}
              maxLength={100}
            />
            {validationError ? (
              <small id="project-name-error" className="field-error">
                {validationError}
              </small>
            ) : null}
          </div>

          <div className="field-group">
            <label htmlFor="project-description">Description</label>
            <textarea
              id="project-description"
              name="project-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              rows={5}
              placeholder="Optional project summary"
              maxLength={2000}
            />
            <div className="field-meta">
              <span>Optional</span>
              <span>{description.length}/2000</span>
            </div>
          </div>

          <div className="form-actions">
            <Link to="/projects" className="secondary-button" aria-label="Cancel project creation">
              Cancel
            </Link>
            <button
              type="submit"
              className="primary-button"
              disabled={submitting}
              aria-live="polite"
            >
              {submitting ? 'Creating...' : 'Create Project'}
            </button>
          </div>
        </form>
      </div>
    </section>
  )
}

export default CreateProjectPage
