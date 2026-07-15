export interface ServiceStatus {
  status: 'ok'
  service: string
  environment: string
}

export async function fetchServiceStatus(): Promise<ServiceStatus> {
  const baseUrl = import.meta.env.VITE_API_BASE_URL ?? ''
  const response = await fetch(`${baseUrl}/api/ping`)

  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}`)
  }

  return (await response.json()) as ServiceStatus
}
