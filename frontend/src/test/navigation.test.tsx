import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import AppShell from '../components/layout/AppShell'
import * as api from '../services/api'
import * as requirementService from '../services/requirementService'

const testProject: api.Project = {
  id: 'proj-alpha',
  name: 'Alpha System',
  description: 'First test system',
  status: 'active',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

describe('Workspace Requirements Navigation', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(api, 'getProject').mockResolvedValue(testProject)
    vi.spyOn(requirementService, 'getRequirements').mockResolvedValue([
      {
        id: 'req-alpha-1',
        project_id: 'proj-alpha',
        title: 'Alpha requirement 1',
        description: 'Alpha description',
        type: 'functional',
        priority: 'high',
        status: 'draft',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ])
  })

  it('marks Requirements tab as active when on /projects/:projectId/requirements route', async () => {
    render(
      <MemoryRouter initialEntries={['/projects/proj-alpha/requirements']}>
        <AppShell />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: 'Alpha System' })).toBeInTheDocument()
    })

    const reqTab = screen.getByRole('link', { name: 'Requirements' })
    expect(reqTab).toBeInTheDocument()
    expect(reqTab).toHaveClass('workspace-tab-active')
    expect(reqTab).toHaveAttribute('href', '/projects/proj-alpha/requirements')

    const overviewTab = screen.getByRole('link', { name: 'Overview' })
    expect(overviewTab).not.toHaveClass('workspace-tab-active')

    await waitFor(() => {
      expect(screen.getByText('Alpha requirement 1')).toBeInTheDocument()
    })
  })

  it('preserves existing workspace overview when navigating to project root', async () => {
    render(
      <MemoryRouter initialEntries={['/projects/proj-alpha']}>
        <AppShell />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('Workspace areas')).toBeInTheDocument()
    })

    const overviewTab = screen.getByRole('link', { name: 'Overview' })
    expect(overviewTab).toHaveClass('workspace-tab-active')

    const reqTab = screen.getByRole('link', { name: 'Requirements' })
    expect(reqTab).not.toHaveClass('workspace-tab-active')
  })
})
