import { apiFetch } from './api'

export type RecitationSubject = 'politics' | 'english' | 'math' | 'cs408'

export interface RecitationItem {
  id: string
  subject: RecitationSubject
  category: string
  title: string
  content_md: string
  recite_count: number
  last_recited_on: string | null
  recited_today: boolean
}

export interface RecitationGroup {
  category: string
  items: RecitationItem[]
}

export interface RecitationStats {
  total_count: number
  recited_today: number
  never_recited: number
}

export interface RecitationListResponse {
  groups: RecitationGroup[]
  stats: RecitationStats
}

export interface RecitationTodayResponse {
  date: string
  item: RecitationItem | null
  stats: RecitationStats
}

export interface ReciteResult {
  item: RecitationItem
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await apiFetch(`/api${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  })
  if (!response.ok) {
    throw new Error(`Recitation API 请求失败：${response.status}`)
  }
  return (await response.json()) as T
}

export function fetchRecitations(
  subject?: RecitationSubject,
): Promise<RecitationListResponse> {
  const query = subject ? `?subject=${subject}` : ''
  return request<RecitationListResponse>(`/recitations${query}`)
}

export function fetchRecitationToday(
  subject?: RecitationSubject,
): Promise<RecitationTodayResponse> {
  const query = subject ? `?subject=${subject}` : ''
  return request<RecitationTodayResponse>(`/recitations/today${query}`)
}

export function reciteItem(itemId: string, undo = false): Promise<ReciteResult> {
  return request<ReciteResult>(`/recitations/${itemId}/recite`, {
    method: 'POST',
    body: JSON.stringify({ undo }),
  })
}
