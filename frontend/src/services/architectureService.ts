import { ApiError, request } from './api'
import type {
  Architecture,
  ArchitectureCreateRequest,
  ArchitectureUpdateRequest,
} from './api'

export async function getArchitecture(projectId: string): Promise<Architecture | null> {
  try {
    return await request<Architecture>(`/api/projects/${projectId}/architecture`)
  } catch (error) {
    if (error instanceof ApiError && (error.code === 'ARCHITECTURE_NOT_FOUND' || error.status === 404)) {
      return null
    }
    throw error
  }
}

export async function createArchitecture(
  projectId: string,
  data: ArchitectureCreateRequest,
): Promise<Architecture> {
  return request<Architecture>(`/api/projects/${projectId}/architecture`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateArchitecture(
  projectId: string,
  data: ArchitectureUpdateRequest,
): Promise<Architecture> {
  return request<Architecture>(`/api/projects/${projectId}/architecture`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function deleteArchitecture(projectId: string): Promise<void> {
  await request<void>(`/api/projects/${projectId}/architecture`, {
    method: 'DELETE',
  })
}
