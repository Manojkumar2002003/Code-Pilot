import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Outlet, Route, Routes } from 'react-router-dom'

import ArchitecturePage from './ArchitecturePage'
import * as architectureService from '../services/architectureService'
import { ApiError, type Architecture, type Project } from '../services/api'

const mockProject: Project = {
  id: 'proj-123',
  name: 'CodePilot Web',
  description: 'AI-assisted developer platform',
  status: 'active',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const mockArchitecture: Architecture = {
  id: 'arch-1',
  project_id: 'proj-123',
  name: 'Modular Monolith Blueprint',
  description: 'Layered architecture with domain services and SQLite database.',
  content: {
    pattern: 'modular_monolith',
    components: ['api', 'service_layer', 'repository', 'sqlite'],
    version: 1,
  },
  created_at: '2026-02-01T10:00:00Z',
  updated_at: '2026-02-02T12:00:00Z',
}

function renderArchitecturePage(project = mockProject) {
  return render(
    <MemoryRouter initialEntries={[`/projects/${project.id}/architecture`]}>
      <Routes>
        <Route path="/projects/:projectId" element={<Outlet context={{ project }} />}>
          <Route path="architecture" element={<ArchitecturePage />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

describe('ArchitecturePage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders loading state initially while fetching architecture', async () => {
    vi.spyOn(architectureService, 'getArchitecture').mockReturnValue(new Promise(() => {}))

    renderArchitecturePage()

    expect(screen.getByText('Loading architecture...')).toBeInTheDocument()
  })

  it('renders existing architecture information when loaded', async () => {
    vi.spyOn(architectureService, 'getArchitecture').mockResolvedValue(mockArchitecture)

    renderArchitecturePage()

    await waitFor(() => {
      expect(screen.getByText('Project architecture')).toBeInTheDocument()
    })

    expect(screen.getByText('CodePilot Web')).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 3, name: 'Modular Monolith Blueprint' })).toBeInTheDocument()
    expect(
      screen.getByText('Layered architecture with domain services and SQLite database.'),
    ).toBeInTheDocument()
    expect(screen.getByText(/pattern/)).toBeInTheDocument()
    expect(screen.getByText(/modular_monolith/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Edit architecture' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Delete architecture' })).toBeInTheDocument()
  })

  it('displays empty state with create action when no architecture exists', async () => {
    vi.spyOn(architectureService, 'getArchitecture').mockResolvedValue(null)

    renderArchitecturePage()

    await waitFor(() => {
      expect(screen.getByText('No architecture defined yet')).toBeInTheDocument()
    })

    expect(
      screen.getByText(/Create the system architecture for CodePilot Web/),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '+ Create Architecture' })).toBeInTheDocument()
  })

  it('displays error state and provides retry action when API call fails', async () => {
    vi.spyOn(architectureService, 'getArchitecture')
      .mockRejectedValueOnce(new ApiError('Failed to load project architecture.', 500))
      .mockResolvedValueOnce(mockArchitecture)

    renderArchitecturePage()

    await waitFor(() => {
      expect(screen.getByText('Unable to load architecture')).toBeInTheDocument()
    })
    expect(screen.getByText('Failed to load project architecture.')).toBeInTheDocument()

    const retryButton = screen.getByRole('button', { name: 'Retry' })
    await userEvent.click(retryButton)

    await waitFor(() => {
      expect(screen.getByText('Modular Monolith Blueprint')).toBeInTheDocument()
    })
  })

  it('validates required name field on create form submission', async () => {
    vi.spyOn(architectureService, 'getArchitecture').mockResolvedValue(null)

    renderArchitecturePage()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '+ Create Architecture' })).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole('button', { name: '+ Create Architecture' }))

    expect(screen.getByRole('dialog', { name: 'Create architecture' })).toBeInTheDocument()

    const submitBtn = screen.getByRole('button', { name: 'Create Architecture' })
    await userEvent.click(submitBtn)

    expect(screen.getByText('Architecture name is required.')).toBeInTheDocument()
  })

  it('validates structured JSON syntax on create form', async () => {
    vi.spyOn(architectureService, 'getArchitecture').mockResolvedValue(null)

    renderArchitecturePage()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '+ Create Architecture' })).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole('button', { name: '+ Create Architecture' }))

    await userEvent.type(screen.getByLabelText(/architecture name/i), 'Microservices')
    fireEvent.change(screen.getByLabelText(/structured content/i), {
      target: { value: '{ invalid json }' },
    })

    await userEvent.click(screen.getByRole('button', { name: 'Create Architecture' }))

    expect(screen.getByText('Content must be valid JSON.')).toBeInTheDocument()
  })

  it('rejects JSON arrays or non-object primitives for content', async () => {
    vi.spyOn(architectureService, 'getArchitecture').mockResolvedValue(null)

    renderArchitecturePage()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '+ Create Architecture' })).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole('button', { name: '+ Create Architecture' }))

    await userEvent.type(screen.getByLabelText(/architecture name/i), 'Microservices')
    fireEvent.change(screen.getByLabelText(/structured content/i), {
      target: { value: '["item1", "item2"]' },
    })

    await userEvent.click(screen.getByRole('button', { name: 'Create Architecture' }))

    expect(screen.getByText('Content must be a valid JSON object.')).toBeInTheDocument()
  })

  it('successfully creates an architecture and refreshes the display', async () => {
    const user = userEvent.setup()
    vi.spyOn(architectureService, 'getArchitecture')
      .mockResolvedValueOnce(null)
      .mockResolvedValueOnce(mockArchitecture)

    const createSpy = vi.spyOn(architectureService, 'createArchitecture').mockResolvedValueOnce(
      mockArchitecture,
    )

    renderArchitecturePage()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '+ Create Architecture' })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: '+ Create Architecture' }))

    await user.type(screen.getByLabelText(/architecture name/i), 'Modular Monolith Blueprint')
    await user.type(
      screen.getByLabelText(/description/i),
      'Layered architecture with domain services and SQLite database.',
    )
    fireEvent.change(screen.getByLabelText(/structured content/i), {
      target: { value: '{"pattern": "modular_monolith"}' },
    })

    await user.click(screen.getByRole('button', { name: 'Create Architecture' }))

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith('proj-123', {
        name: 'Modular Monolith Blueprint',
        description: 'Layered architecture with domain services and SQLite database.',
        content: { pattern: 'modular_monolith' },
      })
    })

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 3, name: 'Modular Monolith Blueprint' })).toBeInTheDocument()
    })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('opens edit form populated with current values and updates architecture', async () => {
    const user = userEvent.setup()
    const updatedArch: Architecture = {
      ...mockArchitecture,
      name: 'Modular Monolith Blueprint v2',
      description: 'Updated architecture description.',
    }

    vi.spyOn(architectureService, 'getArchitecture')
      .mockResolvedValueOnce(mockArchitecture)
      .mockResolvedValueOnce(updatedArch)

    const updateSpy = vi.spyOn(architectureService, 'updateArchitecture').mockResolvedValueOnce(
      updatedArch,
    )

    renderArchitecturePage()

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 3, name: 'Modular Monolith Blueprint' })).toBeInTheDocument()
    })

    const editBtn = screen.getByRole('button', { name: 'Edit architecture' })
    await user.click(editBtn)

    expect(screen.getByRole('dialog', { name: 'Edit architecture' })).toBeInTheDocument()
    const nameInput = screen.getByLabelText(/architecture name/i)
    expect(nameInput).toHaveValue('Modular Monolith Blueprint')

    await user.clear(nameInput)
    await user.type(nameInput, 'Modular Monolith Blueprint v2')

    await user.click(screen.getByRole('button', { name: 'Save Changes' }))

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith('proj-123', {
        name: 'Modular Monolith Blueprint v2',
      })
    })

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 3, name: 'Modular Monolith Blueprint v2' })).toBeInTheDocument()
    })
  })

  it('requires delete confirmation and removes architecture on confirm', async () => {
    const user = userEvent.setup()
    vi.spyOn(architectureService, 'getArchitecture').mockResolvedValueOnce(mockArchitecture)

    const deleteSpy = vi.spyOn(architectureService, 'deleteArchitecture').mockResolvedValueOnce()

    renderArchitecturePage()

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 3, name: 'Modular Monolith Blueprint' })).toBeInTheDocument()
    })

    const deleteBtn = screen.getByRole('button', { name: 'Delete architecture' })
    await user.click(deleteBtn)

    // Confirmation panel appears
    expect(screen.getByText('Delete architecture?')).toBeInTheDocument()
    expect(
      screen.getByText(/Are you sure you want to delete the architecture definition/),
    ).toBeInTheDocument()

    // Confirm deletion
    const confirmDeleteBtn = screen.getByRole('button', { name: 'Delete Architecture' })
    await user.click(confirmDeleteBtn)

    await waitFor(() => {
      expect(deleteSpy).toHaveBeenCalledWith('proj-123')
    })

    // Page returns to empty state
    await waitFor(() => {
      expect(screen.getByText('No architecture defined yet')).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: '+ Create Architecture' })).toBeInTheDocument()
  })

  it('allows canceling delete action', async () => {
    const user = userEvent.setup()
    vi.spyOn(architectureService, 'getArchitecture').mockResolvedValueOnce(mockArchitecture)

    renderArchitecturePage()

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 3, name: 'Modular Monolith Blueprint' })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: 'Delete architecture' }))
    expect(screen.getByText('Delete architecture?')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(screen.queryByText('Delete architecture?')).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 3, name: 'Modular Monolith Blueprint' })).toBeInTheDocument()
  })

  it('keeps form open and displays error when creation fails', async () => {
    const user = userEvent.setup()
    vi.spyOn(architectureService, 'getArchitecture').mockResolvedValue(null)
    vi.spyOn(architectureService, 'createArchitecture').mockRejectedValueOnce(
      new ApiError('An architecture already exists for this project.', 409),
    )

    renderArchitecturePage()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '+ Create Architecture' })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: '+ Create Architecture' }))
    await user.type(screen.getByLabelText(/architecture name/i), 'Duplicate Arch')

    await user.click(screen.getByRole('button', { name: 'Create Architecture' }))

    await waitFor(() => {
      expect(
        screen.getByText('An architecture already exists for this project.'),
      ).toBeInTheDocument()
    })

    // Input preserved
    expect(screen.getByLabelText(/architecture name/i)).toHaveValue('Duplicate Arch')
  })

  it('scopes architecture requests to the current project ID', async () => {
    const getSpy = vi.spyOn(architectureService, 'getArchitecture').mockResolvedValue(null)

    const projectGamma: Project = {
      ...mockProject,
      id: 'proj-gamma',
      name: 'Project Gamma',
    }

    renderArchitecturePage(projectGamma)

    await waitFor(() => {
      expect(getSpy).toHaveBeenCalledWith('proj-gamma')
    })
    expect(screen.getByText('Project Gamma')).toBeInTheDocument()
  })
})
