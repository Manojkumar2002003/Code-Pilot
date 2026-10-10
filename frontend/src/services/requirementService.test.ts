import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  createRequirement,
  deleteRequirement,
  getRequirement,
  getRequirements,
  updateRequirement,
} from './requirementService'

describe('requirementService', () => {
  const projectId = 'proj-123'
  const requirementId = 'req-456'

  beforeEach(() => {
    vi.restoreAllMocks()
  })

  describe('getRequirements', () => {
    it('sends GET request to /api/projects/:projectId/requirements', async () => {
      const mockRequirements = [
        {
          id: 'req-1',
          project_id: projectId,
          title: 'Req 1',
          description: 'Desc 1',
          type: 'functional',
          priority: 'high',
          status: 'draft',
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
      ]

      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(mockRequirements),
      } as Response)

      const result = await getRequirements(projectId)

      expect(result).toEqual(mockRequirements)
      expect(globalThis.fetch).toHaveBeenCalledTimes(1)
      const [url, init] = vi.mocked(globalThis.fetch).mock.calls[0]
      expect(url).toContain(`/api/projects/${projectId}/requirements`)
      expect(new Headers(init?.headers).get('Accept')).toBe('application/json')
    })
  })

  describe('getRequirement', () => {
    it('sends GET request to /api/projects/:projectId/requirements/:requirementId', async () => {
      const mockRequirement = {
        id: requirementId,
        project_id: projectId,
        title: 'Req Single',
        description: 'Desc Single',
        type: 'functional',
        priority: 'medium',
        status: 'approved',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      }

      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(mockRequirement),
      } as Response)

      const result = await getRequirement(projectId, requirementId)

      expect(result).toEqual(mockRequirement)
      const [url] = vi.mocked(globalThis.fetch).mock.calls[0]
      expect(url).toContain(`/api/projects/${projectId}/requirements/${requirementId}`)
    })
  })

  describe('createRequirement', () => {
    it('sends POST request with JSON payload', async () => {
      const payload = {
        title: 'New requirement',
        description: 'New description',
        type: 'functional' as const,
        priority: 'critical' as const,
      }
      const created = {
        id: 'new-id',
        project_id: projectId,
        status: 'draft' as const,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
        ...payload,
      }

      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(created),
      } as Response)

      const result = await createRequirement(projectId, payload)

      expect(result).toEqual(created)
      const [url, init] = vi.mocked(globalThis.fetch).mock.calls[0]
      expect(url).toContain(`/api/projects/${projectId}/requirements`)
      expect(init?.method).toBe('POST')
      expect(init?.body).toBe(JSON.stringify(payload))
      expect(new Headers(init?.headers).get('Content-Type')).toBe('application/json')
    })
  })

  describe('updateRequirement', () => {
    it('sends PATCH request with partial update payload', async () => {
      const updateData = {
        title: 'Updated title',
        status: 'approved' as const,
      }
      const updated = {
        id: requirementId,
        project_id: projectId,
        title: 'Updated title',
        description: 'Existing desc',
        type: 'functional' as const,
        priority: 'medium' as const,
        status: 'approved' as const,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-02T00:00:00Z',
      }

      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(updated),
      } as Response)

      const result = await updateRequirement(projectId, requirementId, updateData)

      expect(result).toEqual(updated)
      const [url, init] = vi.mocked(globalThis.fetch).mock.calls[0]
      expect(url).toContain(`/api/projects/${projectId}/requirements/${requirementId}`)
      expect(init?.method).toBe('PATCH')
      expect(init?.body).toBe(JSON.stringify(updateData))
    })
  })

  describe('deleteRequirement', () => {
    it('handles HTTP 204 No Content response properly', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: true,
        status: 204,
        text: async () => '',
      } as Response)

      await expect(deleteRequirement(projectId, requirementId)).resolves.toBeUndefined()

      const [url, init] = vi.mocked(globalThis.fetch).mock.calls[0]
      expect(url).toContain(`/api/projects/${projectId}/requirements/${requirementId}`)
      expect(init?.method).toBe('DELETE')
    })
  })

  describe('error handling', () => {
    it('throws ApiError with server error details on failure', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({
          error: {
            code: 'NOT_FOUND',
            message: 'Requirement not found.',
          },
        }),
      } as Response)

      await expect(getRequirement(projectId, requirementId)).rejects.toMatchObject({
        name: 'ApiError',
        status: 404,
        message: 'Requirement not found.',
        code: 'NOT_FOUND',
      })
    })

    it('throws ApiError on network connection failure', async () => {
      vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'))

      await expect(getRequirements(projectId)).rejects.toMatchObject({
        name: 'ApiError',
        status: null,
        code: 'NETWORK_ERROR',
      })
    })
  })
})
