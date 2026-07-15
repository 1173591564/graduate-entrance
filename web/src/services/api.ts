const baseUrl = import.meta.env.VITE_API_BASE_URL ?? ''
const apiToken = import.meta.env.VITE_API_TOKEN ?? ''

export function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers)
  if (apiToken) {
    headers.set('Authorization', `Bearer ${apiToken}`)
  }
  return fetch(`${baseUrl}${path}`, {
    ...init,
    headers,
  })
}
