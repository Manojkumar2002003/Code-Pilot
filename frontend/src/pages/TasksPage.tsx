import { type FormEvent, useCallback, useEffect, useState } from 'react'
import { useOutletContext } from 'react-router-dom'

import EmptyState from '../components/common/EmptyState'
import ErrorState from '../components/common/ErrorState'
import LoadingState from '../components/common/LoadingState'
import type { WorkspaceOutletContext } from '../components/workspace/ProjectWorkspaceLayout'
import {
  ApiError,
  type Task,
  type TaskCreateRequest,
  type TaskPriority,
  type TaskStatus,
  type TaskUpdateRequest,
} from '../services/api'
import {
  createTask,
  deleteTask,
  getTasks,
  updateTask,
} from '../services/taskService'

const TASK_PRIORITY_LABELS: Record<TaskPriority, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  critical: 'Critical',
}

const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  todo: 'To Do',
  in_progress: 'In Progress',
  completed: 'Completed',
  blocked: 'Blocked',
  cancelled: 'Cancelled',
}

function formatTaskDate(value: string): string {
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

function TasksPage() {
  const { project } = useOutletContext<WorkspaceOutletContext>()

  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Form modal state
  const [formOpen, setFormOpen] = useState(false)
  const [editingTask, setEditingTask] = useState<Task | null>(null)

  // Form fields
  const [formTitle, setFormTitle] = useState('')
  const [formDescription, setFormDescription] = useState('')
  const [formPriority, setFormPriority] = useState<TaskPriority>('medium')
  const [formStatus, setFormStatus] = useState<TaskStatus>('todo')

  // Form validation / submission state
  const [formSubmitting, setFormSubmitting] = useState(false)
  const [formError, setFormError] = useState('')
  const [titleError, setTitleError] = useState('')
  const [descriptionError, setDescriptionError] = useState('')

  // Delete state
  const [deleteTarget, setDeleteTarget] = useState<Task | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const loadTasks = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await getTasks(project.id)
      setTasks(data)
    } catch (caughtError) {
      if (caughtError instanceof ApiError) {
        setError(caughtError.message)
        return
      }

      setError('Unable to load tasks. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [project.id])

  useEffect(() => {
    void loadTasks()
  }, [loadTasks])

  const openCreateForm = () => {
    setEditingTask(null)
    setFormTitle('')
    setFormDescription('')
    setFormPriority('medium')
    setFormStatus('todo')
    setFormError('')
    setTitleError('')
    setDescriptionError('')
    setFormOpen(true)
  }

  const openEditForm = (task: Task) => {
    setEditingTask(task)
    setFormTitle(task.title)
    setFormDescription(task.description ?? '')
    setFormPriority(task.priority)
    setFormStatus(task.status)
    setFormError('')
    setTitleError('')
    setDescriptionError('')
    setFormOpen(true)
  }

  const closeForm = () => {
    setFormOpen(false)
    setEditingTask(null)
  }

  const validateForm = (): boolean => {
    let valid = true
    const trimmedTitle = formTitle.trim()
    const trimmedDescription = formDescription.trim()

    if (!trimmedTitle) {
      setTitleError('Title is required.')
      valid = false
    } else if (trimmedTitle.length > 255) {
      setTitleError('Title must be 255 characters or fewer.')
      valid = false
    } else {
      setTitleError('')
    }

    if (trimmedDescription.length > 5000) {
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
      if (editingTask) {
        const payload: TaskUpdateRequest = {}
        if (trimmedTitle !== editingTask.title) payload.title = trimmedTitle
        if (trimmedDescription !== (editingTask.description ?? '')) {
          payload.description = trimmedDescription || null
        }
        if (formPriority !== editingTask.priority) payload.priority = formPriority
        if (formStatus !== editingTask.status) payload.status = formStatus

        // If nothing changed, simply close form
        if (Object.keys(payload).length === 0) {
          closeForm()
          return
        }

        await updateTask(project.id, editingTask.id, payload)
      } else {
        const payload: TaskCreateRequest = {
          title: trimmedTitle,
          description: trimmedDescription || null,
          priority: formPriority,
          status: formStatus,
        }
        await createTask(project.id, payload)
      }

      closeForm()
      await loadTasks()
    } catch (caughtError) {
      if (caughtError instanceof ApiError) {
        setFormError(caughtError.message)
        return
      }

      setFormError(
        editingTask
          ? 'Unable to update the task. Please try again.'
          : 'Unable to create the task. Please try again.',
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
      await deleteTask(project.id, deleteTarget.id)
      setDeleteTarget(null)
      await loadTasks()
    } catch (caughtError) {
      if (caughtError instanceof ApiError) {
        setDeleteError(caughtError.message)
        return
      }

      setDeleteError('Unable to delete the task. Please try again.')
    } finally {
      setDeleting(false)
    }
  }

  const isEditing = editingTask !== null

  return (
    <div className="tasks-page">
      <div className="tasks-page-header">
        <div className="tasks-header-text">
          <p className="eyebrow page-eyebrow">Tasks</p>
          <h2>Project tasks</h2>
          <p className="tasks-subtitle">
            Manage engineering tasks, track status, and organize work for{' '}
            <strong>{project.name}</strong>.
          </p>
        </div>

        {!loading && !error && tasks.length > 0 && (
          <button
            type="button"
            className="primary-button task-create-button"
            onClick={openCreateForm}
          >
            + New Task
          </button>
        )}
      </div>

      {/* Delete confirmation */}
      {deleteTarget ? (
        <div className="state-panel delete-confirmation task-delete-confirmation">
          <h3>Delete task?</h3>
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
              {deleting ? 'Deleting...' : 'Delete Task'}
            </button>
          </div>
        </div>
      ) : null}

      {/* Form modal */}
      {formOpen ? (
        <div className="task-form-overlay" onClick={closeForm}>
          <div
            className="task-form-modal"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-label={isEditing ? 'Edit task' : 'Create task'}
          >
            <div className="task-form-modal-header">
              <h3>{isEditing ? 'Edit task' : 'New task'}</h3>
              <button
                type="button"
                className="task-form-close-button"
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
                <label htmlFor="task-title">Title</label>
                <input
                  id="task-title"
                  name="task-title"
                  type="text"
                  value={formTitle}
                  onChange={(e) => {
                    setFormTitle(e.target.value)
                    if (titleError) setTitleError('')
                  }}
                  placeholder="Enter task title"
                  aria-invalid={Boolean(titleError)}
                  aria-describedby={titleError ? 'task-title-error' : undefined}
                  maxLength={255}
                />
                {titleError ? (
                  <small id="task-title-error" className="field-error">
                    {titleError}
                  </small>
                ) : null}
                <div className="field-meta">
                  <span>Required</span>
                  <span>{formTitle.length}/255</span>
                </div>
              </div>

              <div className="field-group">
                <label htmlFor="task-description">Description</label>
                <textarea
                  id="task-description"
                  name="task-description"
                  value={formDescription}
                  onChange={(e) => {
                    setFormDescription(e.target.value)
                    if (descriptionError) setDescriptionError('')
                  }}
                  placeholder="Describe the task (optional)"
                  rows={4}
                  aria-invalid={Boolean(descriptionError)}
                  aria-describedby={descriptionError ? 'task-description-error' : undefined}
                  maxLength={5000}
                />
                {descriptionError ? (
                  <small id="task-description-error" className="field-error">
                    {descriptionError}
                  </small>
                ) : null}
                <div className="field-meta">
                  <span>Optional</span>
                  <span>{formDescription.length}/5000</span>
                </div>
              </div>

              <div className="task-form-row">
                <div className="field-group">
                  <label htmlFor="task-priority">Priority</label>
                  <select
                    id="task-priority"
                    name="task-priority"
                    value={formPriority}
                    onChange={(e) => setFormPriority(e.target.value as TaskPriority)}
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>

                <div className="field-group">
                  <label htmlFor="task-status">Status</label>
                  <select
                    id="task-status"
                    name="task-status"
                    value={formStatus}
                    onChange={(e) => setFormStatus(e.target.value as TaskStatus)}
                  >
                    <option value="todo">To Do</option>
                    <option value="in_progress">In Progress</option>
                    <option value="completed">Completed</option>
                    <option value="blocked">Blocked</option>
                    <option value="cancelled">Cancelled</option>
                  </select>
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
                      : 'Create Task'}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {/* Content */}
      {loading ? (
        <LoadingState message="Loading tasks..." />
      ) : error ? (
        <ErrorState
          title="Unable to load tasks"
          message={error}
          onRetry={loadTasks}
        />
      ) : tasks.length === 0 ? (
        <div className="empty-project-panel">
          <EmptyState
            title="No tasks yet"
            description={`Create the first task for ${project.name} to get started.`}
          />
          <div className="empty-project-action">
            <button type="button" className="action-button enabled" onClick={openCreateForm}>
              + Create Task
            </button>
          </div>
        </div>
      ) : (
        <div className="task-list">
          {tasks.map((task) => (
            <article
              key={task.id}
              className="task-card"
              aria-label={`Task: ${task.title}`}
            >
              <div className="task-card-header">
                <div className="task-card-title-row">
                  <h3 className="task-card-title">{task.title}</h3>
                  <div className="task-card-badges">
                    <span
                      className={`task-badge task-badge-priority task-badge-priority-${task.priority}`}
                    >
                      {TASK_PRIORITY_LABELS[task.priority]}
                    </span>
                    <span
                      className={`task-badge task-badge-status task-badge-status-${task.status}`}
                    >
                      {TASK_STATUS_LABELS[task.status]}
                    </span>
                  </div>
                </div>
              </div>

              {task.description ? (
                <p className="task-card-description">{task.description}</p>
              ) : null}

              <div className="task-card-footer">
                <div className="task-card-meta">
                  <span className="task-meta-date">
                    Updated {formatTaskDate(task.updated_at)}
                  </span>
                </div>

                <div className="task-card-actions">
                  <button
                    type="button"
                    className="secondary-button task-action-button"
                    onClick={() => openEditForm(task)}
                    aria-label={`Edit ${task.title}`}
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    className="danger-button task-action-button"
                    onClick={() => {
                      setDeleteError(null)
                      setDeleteTarget(task)
                    }}
                    aria-label={`Delete ${task.title}`}
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

export default TasksPage
