import { type FormEvent, useCallback, useEffect, useState } from 'react'
import { useOutletContext } from 'react-router-dom'

import EmptyState from '../components/common/EmptyState'
import ErrorState from '../components/common/ErrorState'
import LoadingState from '../components/common/LoadingState'
import type { WorkspaceOutletContext } from '../components/workspace/ProjectWorkspaceLayout'
import {
  ApiError,
  type Requirement,
  type RequirementCreateRequest,
  type RequirementPriority,
  type RequirementStatus,
  type RequirementType,
  type RequirementUpdateRequest,
} from '../services/api'
import {
  createRequirement,
  deleteRequirement,
  getRequirements,
  updateRequirement,
} from '../services/requirementService'

const REQUIREMENT_TYPE_LABELS: Record<RequirementType, string> = {
  functional: 'Functional',
  non_functional: 'Non-functional',
}

const REQUIREMENT_PRIORITY_LABELS: Record<RequirementPriority, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  critical: 'Critical',
}

const REQUIREMENT_STATUS_LABELS: Record<RequirementStatus, string> = {
  draft: 'Draft',
  approved: 'Approved',
  rejected: 'Rejected',
}

function formatRequirementDate(value: string): string {
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

function RequirementsPage() {
  const { project } = useOutletContext<WorkspaceOutletContext>()

  const [requirements, setRequirements] = useState<Requirement[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Form modal state
  const [formOpen, setFormOpen] = useState(false)
  const [editingRequirement, setEditingRequirement] = useState<Requirement | null>(null)

  // Form fields
  const [formTitle, setFormTitle] = useState('')
  const [formDescription, setFormDescription] = useState('')
  const [formType, setFormType] = useState<RequirementType>('functional')
  const [formPriority, setFormPriority] = useState<RequirementPriority>('medium')
  const [formStatus, setFormStatus] = useState<RequirementStatus>('draft')

  // Form state
  const [formSubmitting, setFormSubmitting] = useState(false)
  const [formError, setFormError] = useState('')
  const [titleError, setTitleError] = useState('')
  const [descriptionError, setDescriptionError] = useState('')

  // Delete state
  const [deleteTarget, setDeleteTarget] = useState<Requirement | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const loadRequirements = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await getRequirements(project.id)
      setRequirements(data)
    } catch (caughtError) {
      if (caughtError instanceof ApiError) {
        setError(caughtError.message)
        return
      }

      setError('Unable to load requirements. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [project.id])

  useEffect(() => {
    void loadRequirements()
  }, [loadRequirements])

  const openCreateForm = () => {
    setEditingRequirement(null)
    setFormTitle('')
    setFormDescription('')
    setFormType('functional')
    setFormPriority('medium')
    setFormStatus('draft')
    setFormError('')
    setTitleError('')
    setDescriptionError('')
    setFormOpen(true)
  }

  const openEditForm = (requirement: Requirement) => {
    setEditingRequirement(requirement)
    setFormTitle(requirement.title)
    setFormDescription(requirement.description)
    setFormType(requirement.type)
    setFormPriority(requirement.priority)
    setFormStatus(requirement.status)
    setFormError('')
    setTitleError('')
    setDescriptionError('')
    setFormOpen(true)
  }

  const closeForm = () => {
    setFormOpen(false)
    setEditingRequirement(null)
  }

  const validateForm = (): boolean => {
    let valid = true

    const trimmedTitle = formTitle.trim()
    const trimmedDescription = formDescription.trim()

    if (!trimmedTitle) {
      setTitleError('Title is required.')
      valid = false
    } else if (trimmedTitle.length > 200) {
      setTitleError('Title must be 200 characters or fewer.')
      valid = false
    } else {
      setTitleError('')
    }

    if (!trimmedDescription) {
      setDescriptionError('Description is required.')
      valid = false
    } else if (trimmedDescription.length > 5000) {
      setDescriptionError('Description must be 5000 characters or fewer.')
      valid = false
    } else {
      setDescriptionError('')
    }

    return valid
  }

  const handleFormSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (!validateForm()) {
      return
    }

    setFormError('')
    setFormSubmitting(true)

    const trimmedTitle = formTitle.trim()
    const trimmedDescription = formDescription.trim()

    try {
      if (editingRequirement) {
        const payload: RequirementUpdateRequest = {}
        if (trimmedTitle !== editingRequirement.title) payload.title = trimmedTitle
        if (trimmedDescription !== editingRequirement.description) payload.description = trimmedDescription
        if (formType !== editingRequirement.type) payload.type = formType
        if (formPriority !== editingRequirement.priority) payload.priority = formPriority
        if (formStatus !== editingRequirement.status) payload.status = formStatus

        // Backend requires at least one field
        if (Object.keys(payload).length === 0) {
          closeForm()
          return
        }

        await updateRequirement(project.id, editingRequirement.id, payload)
      } else {
        const payload: RequirementCreateRequest = {
          title: trimmedTitle,
          description: trimmedDescription,
          type: formType,
          priority: formPriority,
        }
        await createRequirement(project.id, payload)
      }

      closeForm()
      await loadRequirements()
    } catch (caughtError) {
      if (caughtError instanceof ApiError) {
        setFormError(caughtError.message)
        return
      }

      setFormError(
        editingRequirement
          ? 'Unable to update the requirement. Please try again.'
          : 'Unable to create the requirement. Please try again.',
      )
    } finally {
      setFormSubmitting(false)
    }
  }

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return

    setDeleteError(null)
    setDeleting(true)

    try {
      await deleteRequirement(project.id, deleteTarget.id)
      setDeleteTarget(null)
      await loadRequirements()
    } catch (caughtError) {
      if (caughtError instanceof ApiError) {
        setDeleteError(caughtError.message)
        return
      }

      setDeleteError('Unable to delete the requirement. Please try again.')
    } finally {
      setDeleting(false)
    }
  }

  const isEditing = editingRequirement !== null

  return (
    <div className="requirements-page">
      <div className="requirements-page-header">
        <div className="requirements-header-text">
          <p className="eyebrow page-eyebrow">Requirements</p>
          <h2>Project requirements</h2>
          <p className="requirements-subtitle">
            Define and manage the functional and non-functional requirements for{' '}
            <strong>{project.name}</strong>.
          </p>
        </div>

        {!loading && !error && requirements.length > 0 && (
          <button
            type="button"
            className="primary-button requirement-create-button"
            onClick={openCreateForm}
          >
            + New Requirement
          </button>
        )}
      </div>

      {/* Delete confirmation */}
      {deleteTarget ? (
        <div className="state-panel delete-confirmation requirement-delete-confirmation">
          <h3>Delete requirement?</h3>
          <p>
            Are you sure you want to delete <strong>{deleteTarget.title}</strong>? This action
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
                setDeleteTarget(null)
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
              {deleting ? 'Deleting...' : 'Delete Requirement'}
            </button>
          </div>
        </div>
      ) : null}

      {/* Form modal */}
      {formOpen ? (
        <div className="requirement-form-overlay" onClick={closeForm}>
          <div
            className="requirement-form-modal"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-label={isEditing ? 'Edit requirement' : 'Create requirement'}
          >
            <div className="requirement-form-modal-header">
              <h3>{isEditing ? 'Edit requirement' : 'New requirement'}</h3>
              <button
                type="button"
                className="requirement-form-close-button"
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
                <label htmlFor="requirement-title">Title</label>
                <input
                  id="requirement-title"
                  name="requirement-title"
                  type="text"
                  value={formTitle}
                  onChange={(e) => {
                    setFormTitle(e.target.value)
                    if (titleError) setTitleError('')
                  }}
                  placeholder="Enter requirement title"
                  aria-invalid={Boolean(titleError)}
                  aria-describedby={titleError ? 'requirement-title-error' : undefined}
                  maxLength={200}
                />
                {titleError ? (
                  <small id="requirement-title-error" className="field-error">
                    {titleError}
                  </small>
                ) : null}
                <div className="field-meta">
                  <span>Required</span>
                  <span>{formTitle.length}/200</span>
                </div>
              </div>

              <div className="field-group">
                <label htmlFor="requirement-description">Description</label>
                <textarea
                  id="requirement-description"
                  name="requirement-description"
                  value={formDescription}
                  onChange={(e) => {
                    setFormDescription(e.target.value)
                    if (descriptionError) setDescriptionError('')
                  }}
                  placeholder="Describe the requirement"
                  rows={4}
                  aria-invalid={Boolean(descriptionError)}
                  aria-describedby={descriptionError ? 'requirement-description-error' : undefined}
                  maxLength={5000}
                />
                {descriptionError ? (
                  <small id="requirement-description-error" className="field-error">
                    {descriptionError}
                  </small>
                ) : null}
                <div className="field-meta">
                  <span>Required</span>
                  <span>{formDescription.length}/5000</span>
                </div>
              </div>

              <div className="requirement-form-row">
                <div className="field-group">
                  <label htmlFor="requirement-type">Type</label>
                  <select
                    id="requirement-type"
                    name="requirement-type"
                    value={formType}
                    onChange={(e) => setFormType(e.target.value as RequirementType)}
                  >
                    <option value="functional">Functional</option>
                    <option value="non_functional">Non-functional</option>
                  </select>
                </div>

                <div className="field-group">
                  <label htmlFor="requirement-priority">Priority</label>
                  <select
                    id="requirement-priority"
                    name="requirement-priority"
                    value={formPriority}
                    onChange={(e) => setFormPriority(e.target.value as RequirementPriority)}
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>

                {isEditing ? (
                  <div className="field-group">
                    <label htmlFor="requirement-status">Status</label>
                    <select
                      id="requirement-status"
                      name="requirement-status"
                      value={formStatus}
                      onChange={(e) => setFormStatus(e.target.value as RequirementStatus)}
                    >
                      <option value="draft">Draft</option>
                      <option value="approved">Approved</option>
                      <option value="rejected">Rejected</option>
                    </select>
                  </div>
                ) : null}
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
                      : 'Create Requirement'}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {/* Content */}
      {loading ? (
        <LoadingState message="Loading requirements..." />
      ) : error ? (
        <ErrorState
          title="Unable to load requirements"
          message={error}
          onRetry={loadRequirements}
        />
      ) : requirements.length === 0 ? (
        <div className="empty-project-panel">
          <EmptyState
            title="No requirements yet"
            description={`Create the first requirement for ${project.name} to get started.`}
          />
          <div className="empty-project-action">
            <button type="button" className="action-button enabled" onClick={openCreateForm}>
              + Create Requirement
            </button>
          </div>
        </div>
      ) : (
        <div className="requirement-list">
          {requirements.map((requirement) => (
            <article
              key={requirement.id}
              className="requirement-card"
              aria-label={`Requirement: ${requirement.title}`}
            >
              <div className="requirement-card-header">
                <div className="requirement-card-title-row">
                  <h3 className="requirement-card-title">{requirement.title}</h3>
                  <div className="requirement-card-badges">
                    <span
                      className={`requirement-badge requirement-badge-priority requirement-badge-priority-${requirement.priority}`}
                    >
                      {REQUIREMENT_PRIORITY_LABELS[requirement.priority]}
                    </span>
                    <span
                      className={`requirement-badge requirement-badge-status requirement-badge-status-${requirement.status}`}
                    >
                      {REQUIREMENT_STATUS_LABELS[requirement.status]}
                    </span>
                  </div>
                </div>
              </div>

              <p className="requirement-card-description">{requirement.description}</p>

              <div className="requirement-card-footer">
                <div className="requirement-card-meta">
                  <span className="requirement-meta-tag">
                    {REQUIREMENT_TYPE_LABELS[requirement.type]}
                  </span>
                  <span className="requirement-meta-date">
                    Updated {formatRequirementDate(requirement.updated_at)}
                  </span>
                </div>

                <div className="requirement-card-actions">
                  <button
                    type="button"
                    className="secondary-button requirement-action-button"
                    onClick={() => openEditForm(requirement)}
                    aria-label={`Edit ${requirement.title}`}
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    className="danger-button requirement-action-button"
                    onClick={() => {
                      setDeleteError(null)
                      setDeleteTarget(requirement)
                    }}
                    aria-label={`Delete ${requirement.title}`}
                  >
                    Delete
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}

export default RequirementsPage
