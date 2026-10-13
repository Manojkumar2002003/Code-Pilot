import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  createTask,
  deleteTask,
  getTask,
  getTasks,
  updateTask,
} from '../services/taskService'

describe('taskService', () => {
  const projectId = 'proj-123'
  const taskId = 'task-456'

  beforeEach(() => {
    vi.restoreAllMocks()
  })

  describe('getTasks', () => {
    it('sends GET request to /api/projects/:projectId/tasks', async () => {
      const mockTasks = [
        {
          id: 'task-1',
          project_id: projectId,
          title: 'Implement auth',
          description: 'JWT tokens',
          priority: 'high',
          status: 'todo',
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
      ]

      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(mockTasks),
      } as Response)

      const result = await getTasks(projectId)

      expect(result).toEqual(mockTasks)
      expect(globalThis.fetch).toHaveBeenCalledTimes(1)
      const [url, init] = vi.mocked(globalThis.fetch).mock.calls[0]
      expect(url).toContain(`/api/projects/${projectId}/tasks`)
      expect(new Headers(init?.headers).get('Accept')).toBe('application/json')
    })
  })

  describe('getTask', () => {
    it('sends GET request to /api/projects/:projectId/tasks/:taskId', async () => {
      const mockTask = {
        id: taskId,
        project_id: projectId,
        title: 'Single Task',
        description: 'Single Description',
        priority: 'medium',
        status: 'in_progress',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      }

      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(mockTask),
      } as Response)

      const result = await getTask(projectId, taskId)

      expect(result).toEqual(mockTask)
      const [url] = vi.mocked(globalThis.fetch).mock.calls[0]
      expect(url).toContain(`/api/projects/${projectId}/tasks/${taskId}`)
    })
  })

  describe('createTask', () => {
    it('sends POST request with JSON payload', async () => {
      const payload = {
        title: 'Create new task',
        description: 'Details of the task',
        priority: 'critical' as const,
        status: 'todo' as const,
      }
      const created = {
        id: 'new-task-id',
        project_id: projectId,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
        ...payload,
      }

      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(created),
      } as Response)

      const result = await createTask(projectId, payload)

      expect(result).toEqual(created)
      const [url, init] = vi.mocked(globalThis.fetch).mock.calls[0]
      expect(url).toContain(`/api/projects/${projectId}/tasks`)
      expect(init?.method).toBe('POST')
      expect(init?.body).toBe(JSON.stringify(payload))
      expect(new Headers(init?.headers).get('Content-Type')).toBe('application/json')
    })
  })

  describe('updateTask', () => {
    it('sends PATCH request with partial update payload', async () => {
      const updateData = {
        title: 'Updated task title',
        status: 'completed' as const,
      }
      const updated = {
        id: taskId,
        project_id: projectId,
        title: 'Updated task title',
        description: 'Existing description',
        priority: 'medium' as const,
        status: 'completed' as const,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-02T00:00:00Z',
      }

      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(updated),
      } as Response)

      const result = await updateTask(projectId, taskId, updateData)

      expect(result).toEqual(updated)
      const [url, init] = vi.mocked(globalThis.fetch).mock.calls[0]
      expect(url).toContain(`/api/projects/${projectId}/tasks/${taskId}`)
      expect(init?.method).toBe('PATCH')
      expect(init?.body).toBe(JSON.stringify(updateData))
    })
  })

  describe('deleteTask', () => {
    it('handles HTTP 204 No Content response properly', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: true,
        status: 204,
        text: async () => '',
      } as Response)

      await expect(deleteTask(projectId, taskId)).resolves.toBeUndefined()

      const [url, init] = vi.mocked(globalThis.fetch).mock.calls[0]
      expect(url).toContain(`/api/projects/${projectId}/tasks/${taskId}`)
      expect(init?.method).toBe('DELETE')
    })
  })

  describe('getTaskRequirements', () => {
    it('sends GET request to /api/projects/:projectId/tasks/:taskId/requirements', async () => {
      const mockReqs = [
        {
          id: 'req-1',
          project_id: projectId,
          title: 'Req 1',
          description: 'Desc',
          type: 'functional',
          priority: 'high',
          status: 'approved',
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
      ]

      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(mockReqs),
      } as Response)

      const { getTaskRequirements } = await import('../services/taskService')
      const result = await getTaskRequirements(projectId, taskId)

      expect(result).toEqual(mockReqs)
      const [url] = vi.mocked(globalThis.fetch).mock.calls[0]
      expect(url).toContain(`/api/projects/${projectId}/tasks/${taskId}/requirements`)
    })
  })

  describe('linkTaskRequirement', () => {
    it('sends POST request with requirement_id payload', async () => {
      const updatedTask = {
        id: taskId,
        project_id: projectId,
        title: 'Task Title',
        priority: 'high',
        status: 'todo',
        requirement_ids: ['req-1'],
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      }

      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(updatedTask),
      } as Response)

      const { linkTaskRequirement } = await import('../services/taskService')
      const result = await linkTaskRequirement(projectId, taskId, 'req-1')

      expect(result).toEqual(updatedTask)
      const [url, init] = vi.mocked(globalThis.fetch).mock.calls[0]
      expect(url).toContain(`/api/projects/${projectId}/tasks/${taskId}/requirements`)
      expect(init?.method).toBe('POST')
      expect(JSON.parse(init?.body as string)).toEqual({ requirement_id: 'req-1' })
    })
  })

  describe('unlinkTaskRequirement', () => {
    it('sends DELETE request to /api/projects/:projectId/tasks/:taskId/requirements/:reqId', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
        ok: true,
        status: 204,
        text: async () => '',
      } as Response)

      const { unlinkTaskRequirement } = await import('../services/taskService')
      await expect(unlinkTaskRequirement(projectId, taskId, 'req-1')).resolves.toBeUndefined()

      const [url, init] = vi.mocked(globalThis.fetch).mock.calls[0]
      expect(url).toContain(`/api/projects/${projectId}/tasks/${taskId}/requirements/req-1`)
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
            code: 'TASK_NOT_FOUND',
            message: 'Task with id not found.',
          },
        }),
      } as Response)

      await expect(getTask(projectId, taskId)).rejects.toMatchObject({
        name: 'ApiError',
        status: 404,
        message: 'Task with id not found.',
        code: 'TASK_NOT_FOUND',
      })
    })

    it('throws ApiError on network connection failure', async () => {
      vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'))

      await expect(getTasks(projectId)).rejects.toMatchObject({
        name: 'ApiError',
        status: null,
        code: 'NETWORK_ERROR',
      })
    })
  })
})
