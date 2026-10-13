import { request } from './api'
import type { Requirement, RequirementCreateRequest, RequirementUpdateRequest, Task } from './api'

export async function getRequirements(projectId: string): Promise<Requirement[]> {
  return request<Requirement[]>(`/api/projects/${projectId}/requirements`)
}

export async function getRequirement(projectId: string, requirementId: string): Promise<Requirement> {
  return request<Requirement>(`/api/projects/${projectId}/requirements/${requirementId}`)
}

export async function createRequirement(projectId: string, data: RequirementCreateRequest): Promise<Requirement> {
  return request<Requirement>(`/api/projects/${projectId}/requirements`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateRequirement(
  projectId: string,
  requirementId: string,
  data: RequirementUpdateRequest,
): Promise<Requirement> {
  return request<Requirement>(`/api/projects/${projectId}/requirements/${requirementId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function deleteRequirement(projectId: string, requirementId: string): Promise<void> {
  await request<void>(`/api/projects/${projectId}/requirements/${requirementId}`, {
    method: 'DELETE',
  })
}

export async function getRequirementTasks(projectId: string, requirementId: string): Promise<Task[]> {
  return request<Task[]>(`/api/projects/${projectId}/requirements/${requirementId}/tasks`)
}

export async function linkRequirementTask(
  projectId: string,
  requirementId: string,
  taskId: string,
): Promise<Task> {
  return request<Task>(`/api/projects/${projectId}/requirements/${requirementId}/tasks`, {
    method: 'POST',
    body: JSON.stringify({ task_id: taskId }),
  })
}

export async function unlinkRequirementTask(
  projectId: string,
  requirementId: string,
  taskId: string,
): Promise<void> {
  await request<void>(`/api/projects/${projectId}/requirements/${requirementId}/tasks/${taskId}`, {
    method: 'DELETE',
  })
}

