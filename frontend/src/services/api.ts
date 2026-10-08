import { apiBaseUrl } from '../config/env'

export class ApiError extends Error {
  status: number | null
  code: string
  details: unknown

  constructor(message: string, status: number | null = null, code = 'API_ERROR', details: unknown = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

export type HealthResponse = {
  status: string
  service: string
}

export type DependencyStatus = {
  status: string
  type?: string
}

export type SystemHealthResponse = {
  status: string
  environment: string
  service: string
  dependencies: {
    backend: DependencyStatus
    database: DependencyStatus
  }
}

export type ProjectStatus = 'active' | 'archived'

export type ProjectCreateRequest = {
  name: string
  description?: string | null
}

export type Project = {
  id: string
  name: string
  description?: string | null
  status: ProjectStatus
  created_at: string
  updated_at: string
}

const API_BASE_URL = apiBaseUrl

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  try {
    const headers = new Headers(init.headers ?? {})
    headers.set('Accept', 'application/json')

    if (init.body !== undefined && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json')
    }

    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers,
    })

    if (!response.ok) {
      let message = 'Request failed.'
      let code = 'HTTP_ERROR'
      let details: unknown = null

      try {
        const payload = (await response.json()) as {
          error?: {
            code?: string
            message?: string
            details?: unknown
          }
        }

        if (payload.error?.message) {
          message = payload.error.message
        }
        if (payload.error?.code) {
          code = payload.error.code
        }
        if (payload.error?.details !== undefined) {
          details = payload.error.details
        }
      } catch {
        message = getStatusMessage(response.status)
      }

      throw new ApiError(message, response.status, code, details)
    }

    const text = await response.text()
    if (!text) {
      return undefined as T
    }

    try {
      return JSON.parse(text) as T
    } catch {
      throw new ApiError('Unexpected response format.', null, 'INVALID_RESPONSE')
    }
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }

    throw new ApiError(
      'Unable to connect to the CodePilot backend. Please make sure the backend is running.',
      null,
      'NETWORK_ERROR',
    )
  }
}

function getStatusMessage(status: number): string {
  switch (status) {
    case 400:
      return 'The request could not be processed.'
    case 401:
      return 'Authentication is required.'
    case 403:
      return 'You do not have permission to perform this action.'
    case 404:
      return 'The requested resource was not found.'
    case 409:
      return 'A conflict occurred while processing the request.'
    case 422:
      return 'The request data is invalid.'
    case 500:
      return 'A server error occurred.'
    case 502:
    case 503:
    case 504:
      return 'The service is temporarily unavailable.'
    default:
      return 'A request error occurred.'
  }
}

export async function createProject(project: ProjectCreateRequest): Promise<Project> {
  return request<Project>('/api/projects', {
    method: 'POST',
    body: JSON.stringify(project),
  })
}

export async function getProjects(): Promise<Project[]> {
  return request<Project[]>('/api/projects')
}

export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/api/health')
}

export async function getDependencyHealth(): Promise<SystemHealthResponse> {
  return request<SystemHealthResponse>('/api/health/dependencies')
}

export { API_BASE_URL }

