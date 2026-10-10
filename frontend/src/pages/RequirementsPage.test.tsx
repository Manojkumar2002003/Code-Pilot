import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Outlet, Route, Routes } from 'react-router-dom'

import RequirementsPage from './RequirementsPage'
import * as requirementService from '../services/requirementService'
import { ApiError, type Project, type Requirement } from '../services/api'

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
    description: 'Implement JWT authentication with OAuth support for GitHub.',
    type: 'functional',
    priority: 'high',
    status: 'approved',
    created_at: '2026-02-01T10:00:00Z',
    updated_at: '2026-02-02T12:00:00Z',
  },
  {
    id: 'req-2',
    project_id: 'proj-123',
    title: 'Sub-200ms API Latency',
    description: 'Ensure 99th percentile response time is under 200ms.',
    type: 'non_functional',
    priority: 'critical',
    status: 'draft',
    created_at: '2026-02-03T10:00:00Z',
    updated_at: '2026-02-03T12:00:00Z',
  },
]

function renderRequirementsPage(project = mockProject) {
  return render(
    <MemoryRouter initialEntries={[`/projects/${project.id}/requirements`]}>
      <Routes>
        <Route path="/projects/:projectId" element={<Outlet context={{ project }} />}>
          <Route path="requirements" element={<RequirementsPage />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

describe('RequirementsPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders loading state initially while fetching requirements', async () => {
    vi.spyOn(requirementService, 'getRequirements').mockReturnValue(new Promise(() => {}))

    renderRequirementsPage()

    expect(screen.getByText('Loading requirements...')).toBeInTheDocument()
  })

  it('renders project context and requirements list when loaded', async () => {
    vi.spyOn(requirementService, 'getRequirements').mockResolvedValue(mockRequirements)

    renderRequirementsPage()

    await waitFor(() => {
      expect(screen.getByText('Project requirements')).toBeInTheDocument()
    })

    expect(screen.getByText('CodePilot Web')).toBeInTheDocument()
    expect(screen.getByText('User Authentication Flow')).toBeInTheDocument()
    expect(screen.getByText('Sub-200ms API Latency')).toBeInTheDocument()
    expect(screen.getByText('Implement JWT authentication with OAuth support for GitHub.')).toBeInTheDocument()
    expect(screen.getByText('High')).toBeInTheDocument()
    expect(screen.getByText('Critical')).toBeInTheDocument()
    expect(screen.getByText('Approved')).toBeInTheDocument()
    expect(screen.getByText('Draft')).toBeInTheDocument()
    expect(screen.getByText('Functional')).toBeInTheDocument()
    expect(screen.getByText('Non-functional')).toBeInTheDocument()
  })

  it('displays empty state with action when no requirements exist', async () => {
    vi.spyOn(requirementService, 'getRequirements').mockResolvedValue([])

    renderRequirementsPage()

    await waitFor(() => {
      expect(screen.getByText('No requirements yet')).toBeInTheDocument()
    })

    expect(
      screen.getByText('Create the first requirement for CodePilot Web to get started.'),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '+ Create Requirement' })).toBeInTheDocument()
  })

  it('displays error state and provides retry action when API call fails', async () => {
    vi.spyOn(requirementService, 'getRequirements')
      .mockRejectedValueOnce(new ApiError('Failed to load backend requirements.', 500))
      .mockResolvedValueOnce(mockRequirements)

    renderRequirementsPage()

    await waitFor(() => {
      expect(screen.getByText('Unable to load requirements')).toBeInTheDocument()
    })
    expect(screen.getByText('Failed to load backend requirements.')).toBeInTheDocument()

    const retryButton = screen.getByRole('button', { name: 'Retry' })
    await userEvent.click(retryButton)

    await waitFor(() => {
      expect(screen.getByText('User Authentication Flow')).toBeInTheDocument()
    })
  })

  it('validates client-side required fields on create form submission', async () => {
    vi.spyOn(requirementService, 'getRequirements').mockResolvedValue([])

    renderRequirementsPage()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '+ Create Requirement' })).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole('button', { name: '+ Create Requirement' }))

    expect(screen.getByRole('dialog', { name: 'Create requirement' })).toBeInTheDocument()

    const submitBtn = screen.getByRole('button', { name: 'Create Requirement' })
    await userEvent.click(submitBtn)

    expect(screen.getByText('Title is required.')).toBeInTheDocument()
    expect(screen.getByText('Description is required.')).toBeInTheDocument()
  })

  it('successfully creates a requirement and refreshes the list', async () => {
    const user = userEvent.setup()
    vi.spyOn(requirementService, 'getRequirements')
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([
        {
          id: 'req-new',
          project_id: 'proj-123',
          title: 'Database connection pooling',
          description: 'Configure HikariCP connection pool with maximum 20 connections.',
          type: 'non_functional',
          priority: 'high',
          status: 'draft',
          created_at: '2026-02-04T00:00:00Z',
          updated_at: '2026-02-04T00:00:00Z',
        },
      ])

    const createSpy = vi.spyOn(requirementService, 'createRequirement').mockResolvedValueOnce({
      id: 'req-new',
      project_id: 'proj-123',
      title: 'Database connection pooling',
      description: 'Configure HikariCP connection pool with maximum 20 connections.',
      type: 'non_functional',
      priority: 'high',
      status: 'draft',
      created_at: '2026-02-04T00:00:00Z',
      updated_at: '2026-02-04T00:00:00Z',
    })

    renderRequirementsPage()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '+ Create Requirement' })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: '+ Create Requirement' }))

    await user.type(screen.getByLabelText(/title/i), 'Database connection pooling')
    await user.type(
      screen.getByLabelText(/description/i),
      'Configure HikariCP connection pool with maximum 20 connections.',
    )
    await user.selectOptions(screen.getByLabelText(/type/i), 'non_functional')
    await user.selectOptions(screen.getByLabelText(/priority/i), 'high')

    await user.click(screen.getByRole('button', { name: 'Create Requirement' }))

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith('proj-123', {
        title: 'Database connection pooling',
        description: 'Configure HikariCP connection pool with maximum 20 connections.',
        type: 'non_functional',
        priority: 'high',
      })
    })

    await waitFor(() => {
      expect(screen.getByText('Database connection pooling')).toBeInTheDocument()
    })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('opens edit form populated with requirement data and saves partial changes', async () => {
    const user = userEvent.setup()
    vi.spyOn(requirementService, 'getRequirements')
      .mockResolvedValueOnce(mockRequirements)
      .mockResolvedValueOnce([
        {
          ...mockRequirements[0],
          title: 'User Authentication Flow (Updated)',
          status: 'approved',
        },
        mockRequirements[1],
      ])

    const updateSpy = vi.spyOn(requirementService, 'updateRequirement').mockResolvedValueOnce({
      ...mockRequirements[0],
      title: 'User Authentication Flow (Updated)',
    })

    renderRequirementsPage()

    await waitFor(() => {
      expect(screen.getByText('User Authentication Flow')).toBeInTheDocument()
    })

    const editBtn = screen.getByRole('button', { name: 'Edit User Authentication Flow' })
    await user.click(editBtn)

    expect(screen.getByRole('dialog', { name: 'Edit requirement' })).toBeInTheDocument()
    const titleInput = screen.getByLabelText(/title/i)
    expect(titleInput).toHaveValue('User Authentication Flow')

    await user.clear(titleInput)
    await user.type(titleInput, 'User Authentication Flow (Updated)')

    await user.click(screen.getByRole('button', { name: 'Save Changes' }))

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith('proj-123', 'req-1', {
        title: 'User Authentication Flow (Updated)',
      })
    })

    await waitFor(() => {
      expect(screen.getByText('User Authentication Flow (Updated)')).toBeInTheDocument()
    })
  })

  it('requires delete confirmation and removes requirement on confirm', async () => {
    const user = userEvent.setup()
    vi.spyOn(requirementService, 'getRequirements')
      .mockResolvedValueOnce(mockRequirements)
      .mockResolvedValueOnce([mockRequirements[1]])

    const deleteSpy = vi.spyOn(requirementService, 'deleteRequirement').mockResolvedValueOnce()

    renderRequirementsPage()

    await waitFor(() => {
      expect(screen.getByText('User Authentication Flow')).toBeInTheDocument()
    })

    const deleteBtn = screen.getByRole('button', { name: 'Delete User Authentication Flow' })
    await user.click(deleteBtn)

    // Confirmation panel appears
    expect(screen.getByText('Delete requirement?')).toBeInTheDocument()
    expect(
      screen.getByText(/Are you sure you want to delete/),
    ).toBeInTheDocument()

    // Confirm deletion
    const confirmDeleteBtn = screen.getByRole('button', { name: 'Delete Requirement' })
    await user.click(confirmDeleteBtn)

    await waitFor(() => {
      expect(deleteSpy).toHaveBeenCalledWith('proj-123', 'req-1')
    })

    await waitFor(() => {
      expect(screen.queryByText('User Authentication Flow')).not.toBeInTheDocument()
    })
    expect(screen.getByText('Sub-200ms API Latency')).toBeInTheDocument()
  })

  it('keeps form open and displays error when creation fails', async () => {
    const user = userEvent.setup()
    vi.spyOn(requirementService, 'getRequirements').mockResolvedValue([])
    vi.spyOn(requirementService, 'createRequirement').mockRejectedValueOnce(
      new ApiError('Title already exists in project.', 409),
    )

    renderRequirementsPage()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '+ Create Requirement' })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: '+ Create Requirement' }))
    await user.type(screen.getByLabelText(/title/i), 'Duplicate Title')
    await user.type(screen.getByLabelText(/description/i), 'Duplicate Description')

    await user.click(screen.getByRole('button', { name: 'Create Requirement' }))

    await waitFor(() => {
      expect(screen.getByText('Title already exists in project.')).toBeInTheDocument()
    })

    // Form inputs are preserved
    expect(screen.getByLabelText(/title/i)).toHaveValue('Duplicate Title')
    expect(screen.getByLabelText(/description/i)).toHaveValue('Duplicate Description')
  })

  it('scopes requirements to the current project ID', async () => {
    const listSpy = vi.spyOn(requirementService, 'getRequirements').mockResolvedValue([])

    const projectBeta: Project = {
      ...mockProject,
      id: 'proj-beta',
      name: 'Project Beta',
    }

    renderRequirementsPage(projectBeta)

    await waitFor(() => {
      expect(listSpy).toHaveBeenCalledWith('proj-beta')
    })
    expect(screen.getByText('Project Beta')).toBeInTheDocument()
  })
})
