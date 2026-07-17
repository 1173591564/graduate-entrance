import { apiFetch } from './api'

export type PaperStatus = 'unread' | 'reading' | 'done'

export interface Paper {
  id: string
  rel_path: string
  title: string
  category: string
  size_bytes: number
  status: PaperStatus
  has_file: boolean
  started_on: string | null
  finished_on: string | null
}

export interface PaperGroup {
  category: string
  papers: Paper[]
}

export interface PaperStats {
  total_count: number
  unread_count: number
  reading_count: number
  done_count: number
}

export interface PaperListResponse {
  groups: PaperGroup[]
  stats: PaperStats
}

export interface PaperTodayResponse {
  date: string
  paper: Paper | null
  stats: PaperStats
}

export interface PaperStatusResult {
  paper: Paper
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
    throw new Error(`Papers API 请求失败：${response.status}`)
  }
  return (await response.json()) as T
}

export function fetchPapers(): Promise<PaperListResponse> {
  return request<PaperListResponse>('/papers')
}

export function fetchPaperToday(): Promise<PaperTodayResponse> {
  return request<PaperTodayResponse>('/papers/today')
}

export function setPaperStatus(
  paperId: string,
  status: PaperStatus,
): Promise<PaperStatusResult> {
  return request<PaperStatusResult>(`/papers/${paperId}/status`, {
    method: 'POST',
    body: JSON.stringify({ status }),
  })
}

export async function openPaperFile(paperId: string): Promise<void> {
  const response = await apiFetch(`/api/papers/${paperId}/file`)
  if (!response.ok) {
    throw new Error(`PDF 加载失败：${response.status}`)
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  window.open(url, '_blank', 'noopener')
}
