import { apiBaseUrl } from '../config/env'

export type HealthResponse = {
  status: string
  service: string
}

const API_BASE_URL = apiBaseUrl

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/health`, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
  })

  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`)
  }

  return (await response.json()) as HealthResponse
}

export { API_BASE_URL }
