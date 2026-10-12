import { request } from './api'
import type { Task, TaskCreateRequest, TaskUpdateRequest } from './api'

export async function getTasks(projectId: string): Promise<Task[]> {
  return request<Task[]>(`/api/projects/${projectId}/tasks`)
}

export async function getTask(projectId: string, taskId: string): Promise<Task> {
  return request<Task>(`/api/projects/${projectId}/tasks/${taskId}`)
}

export async function createTask(projectId: string, data: TaskCreateRequest): Promise<Task> {
  return request<Task>(`/api/projects/${projectId}/tasks`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateTask(
  projectId: string,
  taskId: string,
  data: TaskUpdateRequest,
): Promise<Task> {
  return request<Task>(`/api/projects/${projectId}/tasks/${taskId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function deleteTask(projectId: string, taskId: string): Promise<void> {
  await request<void>(`/api/projects/${projectId}/tasks/${taskId}`, {
    method: 'DELETE',
  })
}
