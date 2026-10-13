import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Outlet, Route, Routes } from 'react-router-dom'

import TasksPage from '../pages/TasksPage'
import * as taskService from '../services/taskService'
import * as requirementService from '../services/requirementService'
import { ApiError, type Project, type Requirement, type Task } from '../services/api'

const mockProject: Project = {
  id: 'proj-123',
  name: 'CodePilot Web',
  description: 'AI-assisted developer platform',
  status: 'active',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const mockRequirements: Requirement[] = [
  {
    id: 'req-1',
    project_id: 'proj-123',
    title: 'User Authentication Flow',
    description: 'JWT tokens',
    type: 'functional',
    priority: 'high',
    status: 'approved',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
]

const mockTasks: Task[] = [
  {
    id: 'task-1',
    project_id: 'proj-123',
    title: 'Implement User Authentication',
    description: 'Set up JWT authentication with secure cookies.',
    priority: 'high',
    status: 'in_progress',
    requirement_ids: ['req-1'],
    created_at: '2026-02-01T10:00:00Z',
    updated_at: '2026-02-02T12:00:00Z',
  },
  {
    id: 'task-2',
    project_id: 'proj-123',
    title: 'Configure Vitest Pipeline',
    description: 'Ensure automated CI test execution passes.',
    priority: 'critical',
    status: 'todo',
    requirement_ids: [],
    created_at: '2026-02-03T10:00:00Z',
    updated_at: '2026-02-03T12:00:00Z',
  },
]

function renderTasksPage(project = mockProject) {
  return render(
    <MemoryRouter initialEntries={[`/projects/${project.id}/tasks`]}>
      <Routes>
        <Route path="/projects/:projectId" element={<Outlet context={{ project }} />}>
          <Route path="tasks" element={<TasksPage />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

describe('TasksPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(requirementService, 'getRequirements').mockResolvedValue(mockRequirements)
  })

  it('renders loading state initially while fetching tasks', async () => {
    vi.spyOn(taskService, 'getTasks').mockReturnValue(new Promise(() => {}))

    renderTasksPage()

    expect(screen.getByText('Loading tasks...')).toBeInTheDocument()
  })

  it('renders project context and tasks list when loaded', async () => {
    vi.spyOn(taskService, 'getTasks').mockResolvedValue(mockTasks)

    renderTasksPage()

    await waitFor(() => {
      expect(screen.getByText('Implement User Authentication')).toBeInTheDocument()
    })

    expect(screen.getByText('Configure Vitest Pipeline')).toBeInTheDocument()
    expect(screen.getByText('In Progress')).toBeInTheDocument()
    expect(screen.getByText('High')).toBeInTheDocument()
    expect(screen.getByText('Critical')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '+ New Task' })).toBeInTheDocument()
  })

  it('renders empty state with create action when no tasks exist', async () => {
    vi.spyOn(taskService, 'getTasks').mockResolvedValue([])

    renderTasksPage()

    await waitFor(() => {
      expect(screen.getByText('No tasks yet')).toBeInTheDocument()
    })

    expect(
      screen.getByText('Create the first task for CodePilot Web to get started.'),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '+ Create Task' })).toBeInTheDocument()
  })

  it('renders error state and retries successfully', async () => {
    const getTasksSpy = vi
      .spyOn(taskService, 'getTasks')
      .mockRejectedValueOnce(new ApiError('Database failure', 500, 'INTERNAL_ERROR'))
      .mockResolvedValueOnce(mockTasks)

    renderTasksPage()

    await waitFor(() => {
      expect(screen.getByText('Unable to load tasks')).toBeInTheDocument()
    })

    expect(screen.getByText('Database failure')).toBeInTheDocument()

    const retryBtn = screen.getByRole('button', { name: /retry/i })
    fireEvent.click(retryBtn)

    await waitFor(() => {
      expect(screen.getByText('Implement User Authentication')).toBeInTheDocument()
    })

    expect(getTasksSpy).toHaveBeenCalledTimes(2)
  })

  it('validates client-side required fields on create form submission', async () => {
    vi.spyOn(taskService, 'getTasks').mockResolvedValue([])

    renderTasksPage()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '+ Create Task' })).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: '+ Create Task' }))

    expect(screen.getByRole('dialog', { name: 'Create task' })).toBeInTheDocument()

    const submitBtn = screen.getByRole('button', { name: 'Create Task' })
    fireEvent.click(submitBtn)

    expect(screen.getByText('Title is required.')).toBeInTheDocument()
  })

  it('successfully creates a task and refreshes the list', async () => {
    const user = userEvent.setup()
    const getTasksSpy = vi
      .spyOn(taskService, 'getTasks')
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce(mockTasks)

    const createTaskSpy = vi.spyOn(taskService, 'createTask').mockResolvedValue({
      id: 'task-new',
      project_id: 'proj-123',
      title: 'New Automated Task',
      description: 'New task details',
      priority: 'high',
      status: 'todo',
      created_at: '2026-03-01T10:00:00Z',
      updated_at: '2026-03-01T10:00:00Z',
    })

    renderTasksPage()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '+ Create Task' })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: '+ Create Task' }))

    const titleInput = screen.getByLabelText(/Title/i)
    const descInput = screen.getByLabelText(/Description/i)
    const prioritySelect = screen.getByLabelText(/Priority/i)

    await user.type(titleInput, 'New Automated Task')
    await user.type(descInput, 'New task details')
    await user.selectOptions(prioritySelect, 'high')

    await user.click(screen.getByRole('button', { name: 'Create Task' }))

    await waitFor(() => {
      expect(createTaskSpy).toHaveBeenCalledWith('proj-123', {
        title: 'New Automated Task',
        description: 'New task details',
        priority: 'high',
        status: 'todo',
      })
    })

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })

    expect(getTasksSpy).toHaveBeenCalledTimes(2)
  })

  it('opens edit form populated with task data and saves partial changes', async () => {
    const user = userEvent.setup()
    vi.spyOn(taskService, 'getTasks').mockResolvedValue(mockTasks)
    const updateTaskSpy = vi.spyOn(taskService, 'updateTask').mockResolvedValue({
      ...mockTasks[0],
      title: 'Updated Auth Title',
      status: 'completed',
    })

    renderTasksPage()

    await waitFor(() => {
      expect(screen.getByText('Implement User Authentication')).toBeInTheDocument()
    })

    const editBtn = screen.getByRole('button', { name: 'Edit Implement User Authentication' })
    await user.click(editBtn)

    expect(screen.getByRole('dialog', { name: 'Edit task' })).toBeInTheDocument()

    const titleInput = screen.getByLabelText(/Title/i)
    expect(titleInput).toHaveValue('Implement User Authentication')

    const statusSelect = screen.getByLabelText(/Status/i)
    expect(statusSelect).toHaveValue('in_progress')

    await user.clear(titleInput)
    await user.type(titleInput, 'Updated Auth Title')
    await user.selectOptions(statusSelect, 'completed')

    await user.click(screen.getByRole('button', { name: 'Save Changes' }))

    await waitFor(() => {
      expect(updateTaskSpy).toHaveBeenCalledWith('proj-123', 'task-1', {
        title: 'Updated Auth Title',
        status: 'completed',
      })
    })

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })
  })

  it('keeps form open and displays error when creation fails', async () => {
    const user = userEvent.setup()
    vi.spyOn(taskService, 'getTasks').mockResolvedValue([])
    vi.spyOn(taskService, 'createTask').mockRejectedValue(
      new ApiError('Validation error from server', 422, 'VALIDATION_ERROR'),
    )

    renderTasksPage()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '+ Create Task' })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: '+ Create Task' }))

    await user.type(screen.getByLabelText(/Title/i), 'Fail Task')
    await user.click(screen.getByRole('button', { name: 'Create Task' }))

    await waitFor(() => {
      expect(screen.getByText('Validation error from server')).toBeInTheDocument()
    })

    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByLabelText(/Title/i)).toHaveValue('Fail Task')
  })

  it('opens delete confirmation and can cancel without deleting', async () => {
    const user = userEvent.setup()
    vi.spyOn(taskService, 'getTasks').mockResolvedValue(mockTasks)
    const deleteTaskSpy = vi.spyOn(taskService, 'deleteTask')

    renderTasksPage()

    await waitFor(() => {
      expect(screen.getByText('Implement User Authentication')).toBeInTheDocument()
    })

    const deleteBtn = screen.getByRole('button', { name: 'Delete Implement User Authentication' })
    await user.click(deleteBtn)

    expect(screen.getByText('Delete task?')).toBeInTheDocument()
    expect(
      screen.getByText(/Are you sure you want to delete/i),
    ).toBeInTheDocument()

    const cancelBtn = screen.getByRole('button', { name: 'Cancel' })
    await user.click(cancelBtn)

    expect(screen.queryByText('Delete task?')).not.toBeInTheDocument()
    expect(deleteTaskSpy).not.toHaveBeenCalled()
  })

  it('successfully deletes a task and refreshes the list', async () => {
    const user = userEvent.setup()
    const getTasksSpy = vi
      .spyOn(taskService, 'getTasks')
      .mockResolvedValueOnce(mockTasks)
      .mockResolvedValueOnce([mockTasks[1]])

    const deleteTaskSpy = vi.spyOn(taskService, 'deleteTask').mockResolvedValue(undefined)

    renderTasksPage()

    await waitFor(() => {
      expect(screen.getByText('Implement User Authentication')).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: 'Delete Implement User Authentication' }))

    const confirmDeleteBtn = screen.getByRole('button', { name: 'Delete Task' })
    await user.click(confirmDeleteBtn)

    await waitFor(() => {
      expect(deleteTaskSpy).toHaveBeenCalledWith('proj-123', 'task-1')
    })

    expect(getTasksSpy).toHaveBeenCalledTimes(2)
  })

  it('displays error when deletion fails', async () => {
    const user = userEvent.setup()
    vi.spyOn(taskService, 'getTasks').mockResolvedValue(mockTasks)
    vi.spyOn(taskService, 'deleteTask').mockRejectedValue(
      new ApiError('Deletion prohibited', 400, 'DELETE_FAILED'),
    )

    renderTasksPage()

    await waitFor(() => {
      expect(screen.getByText('Implement User Authentication')).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: 'Delete Implement User Authentication' }))
    await user.click(screen.getByRole('button', { name: 'Delete Task' }))

    await waitFor(() => {
      expect(screen.getByText('Deletion prohibited')).toBeInTheDocument()
    })
  })

  it('renders associated requirements on task cards', async () => {
    vi.spyOn(taskService, 'getTasks').mockResolvedValue(mockTasks)

    renderTasksPage()

    await waitFor(() => {
      expect(screen.getByText('Requirements (1)')).toBeInTheDocument()
    })

    expect(screen.getByTitle('User Authentication Flow')).toBeInTheDocument()
  })

  it('allows unlinking a requirement via confirmation dialog', async () => {
    const user = userEvent.setup()
    vi.spyOn(taskService, 'getTasks').mockResolvedValue(mockTasks)
    const unlinkSpy = vi.spyOn(taskService, 'unlinkTaskRequirement').mockResolvedValue(undefined)

    renderTasksPage()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Unlink requirement User Authentication Flow' })).toBeInTheDocument()
    })

    const unlinkBtn = screen.getByRole('button', { name: 'Unlink requirement User Authentication Flow' })
    await user.click(unlinkBtn)

    expect(screen.getByText('Unlink Requirement')).toBeInTheDocument()
    expect(screen.getByText(/Are you sure you want to unlink/)).toBeInTheDocument()

    const confirmBtn = screen.getByRole('button', { name: 'Unlink Requirement' })
    await user.click(confirmBtn)

    await waitFor(() => {
      expect(unlinkSpy).toHaveBeenCalledWith('proj-123', 'task-1', 'req-1')
    })
  })

  it('allows linking a requirement via quick link dropdown', async () => {
    const user = userEvent.setup()
    vi.spyOn(taskService, 'getTasks').mockResolvedValue(mockTasks)
    const linkSpy = vi.spyOn(taskService, 'linkTaskRequirement').mockResolvedValue(mockRequirements[0])

    renderTasksPage()

    await waitFor(() => {
      expect(screen.getByText('Configure Vitest Pipeline')).toBeInTheDocument()
    })

    const select = screen.getByLabelText('Link requirement to Configure Vitest Pipeline')
    await user.selectOptions(select, 'req-1')

    await waitFor(() => {
      expect(linkSpy).toHaveBeenCalledWith('proj-123', 'task-2', 'req-1')
    })
  })
})
