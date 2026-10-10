import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  createArchitecture,
  deleteArchitecture,
  getArchitecture,
  updateArchitecture,
} from './architectureService'

describe('architectureService', () => {
  const projectId = 'proj-101'

  beforeEach(() => {
    vi.restoreAllMocks()
  })

  describe('getArchitecture', () => {
    it('sends GET request to /api/projects/:projectId/architecture and returns data', async () => {
      const mockArchitecture = {
        id: 'arch-1',
        project_id: projectId,
        name: 'Event-Driven Core',
        description: 'Microservices with Kafka broker.',
        content: { pattern: 'event_driven', broker: 'kafka' },
        created_at: '2026-03-01T10:00:00Z',
        updated_at: '2026-03-01T12:00:00Z',
      }

      vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: true,
        text: async () => JSON.stringify(mockArchitecture),
      } as Response)

      const result = await getArchitecture(projectId)

      expect(result).toEqual(mockArchitecture)
      expect(globalThis.fetch).toHaveBeenCalledTimes(1)
      const [url, init] = vi.mocked(globalThis.fetch).mock.calls[0]
      expect(url).toContain(`/api/projects/${projectId}/architecture`)
      expect(new Headers(init?.headers).get('Accept')).toBe('application/json')
    })

    it('returns null when architecture is not found (404)', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({
          error: {
            code: 'ARCHITECTURE_NOT_FOUND',
            message: 'Architecture not found for project.',
          },
        }),
      } as Response)

      const result = await getArchitecture(projectId)
      expect(result).toBeNull()
    })

    it('throws ApiError on server error (500)', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({
          error: {
            code: 'INTERNAL_ERROR',
            message: 'Database query failed.',
          },
        }),
      } as Response)

      await expect(getArchitecture(projectId)).rejects.toMatchObject({
        name: 'ApiError',
        status: 500,
        code: 'INTERNAL_ERROR',
      })
    })
  })

  describe('createArchitecture', () => {
    it('sends POST request with JSON payload', async () => {
      const payload = {
        name: 'Clean Architecture',
        description: 'Hexagonal clean architecture.',
        content: { layers: ['domain', 'app', 'infra'] },
      }
      const created = {
        id: 'arch-2',
        project_id: projectId,
        created_at: '2026-03-02T10:00:00Z',
        updated_at: '2026-03-02T10:00:00Z',
        ...payload,
      }

      vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: true,
        text: async () => JSON.stringify(created),
      } as Response)

      const result = await createArchitecture(projectId, payload)

      expect(result).toEqual(created)
      const [url, init] = vi.mocked(globalThis.fetch).mock.calls[0]
      expect(url).toContain(`/api/projects/${projectId}/architecture`)
      expect(init?.method).toBe('POST')
      expect(init?.body).toBe(JSON.stringify(payload))
      expect(new Headers(init?.headers).get('Content-Type')).toBe('application/json')
    })
  })

  describe('updateArchitecture', () => {
    it('sends PATCH request with partial update payload', async () => {
      const updateData = {
        name: 'Updated Blueprint',
        content: { version: 2 },
      }
      const updated = {
        id: 'arch-2',
        project_id: projectId,
        name: 'Updated Blueprint',
        description: 'Existing description.',
        content: { version: 2 },
        created_at: '2026-03-02T10:00:00Z',
        updated_at: '2026-03-03T10:00:00Z',
      }

      vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: true,
        text: async () => JSON.stringify(updated),
      } as Response)

      const result = await updateArchitecture(projectId, updateData)

      expect(result).toEqual(updated)
      const [url, init] = vi.mocked(globalThis.fetch).mock.calls[0]
      expect(url).toContain(`/api/projects/${projectId}/architecture`)
      expect(init?.method).toBe('PATCH')
      expect(init?.body).toBe(JSON.stringify(updateData))
    })
  })

  describe('deleteArchitecture', () => {
    it('handles HTTP 204 No Content response properly', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: true,
        status: 204,
        text: async () => '',
      } as Response)

      await expect(deleteArchitecture(projectId)).resolves.toBeUndefined()

      const [url, init] = vi.mocked(globalThis.fetch).mock.calls[0]
      expect(url).toContain(`/api/projects/${projectId}/architecture`)
      expect(init?.method).toBe('DELETE')
    })
  })

  describe('network failure', () => {
    it('throws ApiError on connection error', async () => {
      vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'))

      await expect(deleteArchitecture(projectId)).rejects.toMatchObject({
        name: 'ApiError',
        status: null,
        code: 'NETWORK_ERROR',
      })
    })
  })
})
