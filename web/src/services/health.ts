import type { components } from '../generated/api'
import { apiFetch } from './api'

export type ServiceStatus = components['schemas']['ServiceStatus']

export async function fetchServiceStatus(): Promise<ServiceStatus> {
  const response = await apiFetch('/api/ping')

  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}`)
  }

  return (await response.json()) as ServiceStatus
}
