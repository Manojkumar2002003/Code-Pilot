import { type FormEvent, useCallback, useEffect, useState } from 'react'
import { useOutletContext } from 'react-router-dom'

import EmptyState from '../components/common/EmptyState'
import ErrorState from '../components/common/ErrorState'
import LoadingState from '../components/common/LoadingState'
import type { WorkspaceOutletContext } from '../components/workspace/ProjectWorkspaceLayout'
import {
  ApiError,
  type Architecture,
  type ArchitectureCreateRequest,
  type ArchitectureUpdateRequest,
} from '../services/api'
import {
  createArchitecture,
  deleteArchitecture,
  getArchitecture,
  updateArchitecture,
} from '../services/architectureService'

function formatArchitectureDate(value: string): string {
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

function ArchitecturePage() {
  const { project } = useOutletContext<WorkspaceOutletContext>()

  const [architecture, setArchitecture] = useState<Architecture | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Form modal state
  const [formOpen, setFormOpen] = useState(false)
  const [isEditing, setIsEditing] = useState(false)

  // Form fields
  const [formName, setFormName] = useState('')
  const [formDescription, setFormDescription] = useState('')
  const [formContentJson, setFormContentJson] = useState('')

  // Form errors and loading
  const [formSubmitting, setFormSubmitting] = useState(false)
  const [formError, setFormError] = useState('')
  const [nameError, setNameError] = useState('')
  const [contentError, setContentError] = useState('')

  // Delete state
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const loadArchitecture = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await getArchitecture(project.id)
      setArchitecture(data)
    } catch (caughtError) {
      if (caughtError instanceof ApiError) {
        setError(caughtError.message)
        return
      }

      setError('Unable to load project architecture. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [project.id])

  useEffect(() => {
    void loadArchitecture()
  }, [loadArchitecture])

  const openCreateForm = () => {
    setIsEditing(false)
    setFormName('')
    setFormDescription('')
    setFormContentJson('')
    setFormError('')
    setNameError('')
    setContentError('')
    setFormOpen(true)
  }

  const openEditForm = () => {
    if (!architecture) return
    setIsEditing(true)
    setFormName(architecture.name)
    setFormDescription(architecture.description ?? '')
    setFormContentJson(
      architecture.content && Object.keys(architecture.content).length > 0
        ? JSON.stringify(architecture.content, null, 2)
        : '',
    )
    setFormError('')
    setNameError('')
    setContentError('')
    setFormOpen(true)
  }

  const closeForm = () => {
    setFormOpen(false)
    setIsEditing(false)
  }

  const parseContentJson = (): { valid: boolean; value?: Record<string, unknown> | null } => {
    const trimmed = formContentJson.trim()
    if (!trimmed) {
      return { valid: true, value: null }
    }

    try {
      const parsed = JSON.parse(trimmed)
      if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
        setContentError('Content must be a valid JSON object.')
        return { valid: false }
      }
      return { valid: true, value: parsed as Record<string, unknown> }
    } catch {
      setContentError('Content must be valid JSON.')
      return { valid: false }
    }
  }

  const validateForm = (): boolean => {
    let valid = true

    const trimmedName = formName.trim()
    if (!trimmedName) {
      setNameError('Architecture name is required.')
      valid = false
    } else if (trimmedName.length > 255) {
      setNameError('Architecture name must be 255 characters or fewer.')
      valid = false
    } else {
      setNameError('')
    }

    const { valid: contentValid } = parseContentJson()
    if (!contentValid) {
      valid = false
    } else {
      setContentError('')
    }

    return valid
  }

  const handleFormSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (!validateForm()) {
      return
    }

    const contentResult = parseContentJson()
    if (!contentResult.valid) {
      return
    }

    setFormError('')
    setFormSubmitting(true)

    const trimmedName = formName.trim()
    const trimmedDescription = formDescription.trim() || null
    const parsedContent = contentResult.value ?? null

    try {
      if (isEditing && architecture) {
        const payload: ArchitectureUpdateRequest = {}
        if (trimmedName !== architecture.name) payload.name = trimmedName
        if (trimmedDescription !== (architecture.description ?? null)) {
          payload.description = trimmedDescription
        }

        const existingContentStr = JSON.stringify(architecture.content ?? null)
        const newContentStr = JSON.stringify(parsedContent)
        if (existingContentStr !== newContentStr) {
          payload.content = parsedContent
        }

        if (Object.keys(payload).length === 0) {
          closeForm()
          return
        }

        await updateArchitecture(project.id, payload)
      } else {
        const payload: ArchitectureCreateRequest = {
          name: trimmedName,
          description: trimmedDescription,
          content: parsedContent,
        }
        await createArchitecture(project.id, payload)
      }

      closeForm()
      await loadArchitecture()
    } catch (caughtError) {
      if (caughtError instanceof ApiError) {
        setFormError(caughtError.message)
        return
      }

      setFormError(
        isEditing
          ? 'Unable to update the architecture. Please try again.'
          : 'Unable to create the architecture. Please try again.',
      )
    } finally {
      setFormSubmitting(false)
    }
  }

  const handleDeleteConfirm = async () => {
    setDeleteError(null)
    setDeleting(true)

    try {
      await deleteArchitecture(project.id)
      setArchitecture(null)
      setDeleteConfirmOpen(false)
    } catch (caughtError) {
      if (caughtError instanceof ApiError) {
        setDeleteError(caughtError.message)
        return
      }

      setDeleteError('Unable to delete the architecture. Please try again.')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="architecture-page">
      <div className="architecture-page-header">
        <div className="architecture-header-text">
          <p className="eyebrow page-eyebrow">Architecture</p>
          <h2>Project architecture</h2>
          <p className="architecture-subtitle">
            Define and document the high-level architecture and system design for{' '}
            <strong>{project.name}</strong>.
          </p>
        </div>

        {!loading && !error && architecture && (
          <div className="architecture-header-actions">
            <button
              type="button"
              className="secondary-button"
              onClick={openEditForm}
              aria-label="Edit architecture"
            >
              Edit Architecture
            </button>
            <button
              type="button"
              className="danger-button"
              onClick={() => {
                setDeleteError(null)
                setDeleteConfirmOpen(true)
              }}
              aria-label="Delete architecture"
            >
              Delete
            </button>
          </div>
        )}
      </div>

      {/* Delete confirmation panel */}
      {deleteConfirmOpen && architecture ? (
        <div className="state-panel delete-confirmation architecture-delete-confirmation">
          <h3>Delete architecture?</h3>
          <p>
            Are you sure you want to delete the architecture definition{' '}
            <strong>{architecture.name}</strong> for <strong>{project.name}</strong>? This action
            cannot be undone.
          </p>

          {deleteError ? (
            <div className="form-error" role="alert">
              {deleteError}
            </div>
          ) : null}

          <div className="project-confirmation-actions">
            <button
              type="button"
              className="secondary-button"
              onClick={() => {
                setDeleteConfirmOpen(false)
                setDeleteError(null)
              }}
            >
              Cancel
            </button>
            <button
              type="button"
              className="danger-button"
              onClick={handleDeleteConfirm}
              disabled={deleting}
            >
              {deleting ? 'Deleting...' : 'Delete Architecture'}
            </button>
          </div>
        </div>
      ) : null}

      {/* Form modal */}
      {formOpen ? (
        <div className="architecture-form-overlay" onClick={closeForm}>
          <div
            className="architecture-form-modal"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-label={isEditing ? 'Edit architecture' : 'Create architecture'}
          >
            <div className="architecture-form-modal-header">
              <h3>{isEditing ? 'Edit architecture' : 'New architecture'}</h3>
              <button
                type="button"
                className="architecture-form-close-button"
                onClick={closeForm}
                aria-label="Close form"
              >
                ✕
              </button>
            </div>

            <form className="project-form" onSubmit={handleFormSubmit} noValidate>
              {formError ? (
                <div className="form-error" role="alert">
                  {formError}
                </div>
              ) : null}

              <div className="field-group">
                <label htmlFor="architecture-name">Architecture Name</label>
                <input
                  id="architecture-name"
                  name="architecture-name"
                  type="text"
                  value={formName}
                  onChange={(e) => {
                    setFormName(e.target.value)
                    if (nameError) setNameError('')
                  }}
                  placeholder="e.g. Modular Monolith or Microservices Blueprint"
                  aria-invalid={Boolean(nameError)}
                  aria-describedby={nameError ? 'architecture-name-error' : undefined}
                  maxLength={255}
                />
                {nameError ? (
                  <small id="architecture-name-error" className="field-error">
                    {nameError}
                  </small>
                ) : null}
                <div className="field-meta">
                  <span>Required</span>
                  <span>{formName.length}/255</span>
                </div>
              </div>

              <div className="field-group">
                <label htmlFor="architecture-description">Description</label>
                <textarea
                  id="architecture-description"
                  name="architecture-description"
                  value={formDescription}
                  onChange={(e) => setFormDescription(e.target.value)}
                  placeholder="Describe the system architecture, boundaries, and components"
                  rows={4}
                  maxLength={5000}
                />
                <div className="field-meta">
                  <span>Optional</span>
                  <span>{formDescription.length}/5000</span>
                </div>
              </div>

              <div className="field-group">
                <label htmlFor="architecture-content">Structured Content (JSON)</label>
                <textarea
                  id="architecture-content"
                  name="architecture-content"
                  value={formContentJson}
                  onChange={(e) => {
                    setFormContentJson(e.target.value)
                    if (contentError) setContentError('')
                  }}
                  placeholder={'{\n  "style": "modular_monolith",\n  "components": ["api", "database"]\n}'}
                  rows={6}
                  className="architecture-code-input"
                  aria-invalid={Boolean(contentError)}
                  aria-describedby={contentError ? 'architecture-content-error' : undefined}
                />
                {contentError ? (
                  <small id="architecture-content-error" className="field-error">
                    {contentError}
                  </small>
                ) : null}
                <div className="field-meta">
                  <span>Optional JSON object</span>
                </div>
              </div>

              <div className="form-actions">
                <button type="button" className="secondary-button" onClick={closeForm}>
                  Cancel
                </button>
                <button
                  type="submit"
                  className="primary-button"
                  disabled={formSubmitting}
                  aria-live="polite"
                >
                  {formSubmitting
                    ? isEditing
                      ? 'Saving...'
                      : 'Creating...'
                    : isEditing
                      ? 'Save Changes'
                      : 'Create Architecture'}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {/* Main page content */}
      {loading ? (
        <LoadingState message="Loading architecture..." />
      ) : error ? (
        <ErrorState
          title="Unable to load architecture"
          message={error}
          onRetry={loadArchitecture}
        />
      ) : !architecture ? (
        <div className="empty-project-panel">
          <EmptyState
            title="No architecture defined yet"
            description={`Create the system architecture for ${project.name} to document components, data flows, and design patterns.`}
          />
          <div className="empty-project-action">
            <button
              type="button"
              className="action-button enabled"
              onClick={openCreateForm}
            >
              + Create Architecture
            </button>
          </div>
        </div>
      ) : (
        <article className="architecture-card" aria-label={`Architecture: ${architecture.name}`}>
          <div className="architecture-card-header">
            <div className="architecture-card-title-row">
              <h3 className="architecture-card-title">{architecture.name}</h3>
              <div className="architecture-card-meta">
                <span className="architecture-meta-date">
                  Created {formatArchitectureDate(architecture.created_at)}
                </span>
                <span className="architecture-meta-date">
                  Updated {formatArchitectureDate(architecture.updated_at)}
                </span>
              </div>
            </div>
          </div>

          {architecture.description && (
            <div className="architecture-card-section">
              <h4 className="architecture-section-title">Description</h4>
              <p className="architecture-card-description">{architecture.description}</p>
            </div>
          )}

          <div className="architecture-card-section">
            <h4 className="architecture-section-title">Structured Definition</h4>
            {architecture.content && Object.keys(architecture.content).length > 0 ? (
              <pre className="architecture-json-preview">
                <code>{JSON.stringify(architecture.content, null, 2)}</code>
              </pre>
            ) : (
              <p className="architecture-empty-content">No structured content defined.</p>
            )}
          </div>
        </article>
      )}
    </div>
  )
}

export default ArchitecturePage
