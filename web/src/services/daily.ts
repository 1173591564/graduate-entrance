import { apiFetch } from './api'

export type TaskStatus = 'planned' | 'completed' | 'skipped'

export interface TodayTask {
  id: string
  phase_name: string
  subject_name: string
  knowledge_point_name: string
  material_name: string | null
  title: string
  task_type: string
  planned_date: string
  est_minutes: number
  status: TaskStatus
  actual_minutes: number | null
  done_at: string | null
  carry_count: number
  order: number
}

export interface TodaySummary {
  date: string
  planned_minutes: number
  completed_minutes: number
  remaining_minutes: number
  tasks: TodayTask[]
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
    throw new Error(`Daily request failed with status ${response.status}`)
  }
  return (await response.json()) as T
}

export function fetchToday(date?: string): Promise<TodaySummary> {
  const query = date ? `?date=${encodeURIComponent(date)}` : ''
  return request<TodaySummary>(`/today${query}`)
}

export function completeTodayTask(id: string, actualMinutes: number): Promise<TodayTask> {
  return request<TodayTask>(`/tasks/${id}/done`, {
    method: 'POST',
    body: JSON.stringify({ actual_minutes: actualMinutes }),
  })
}
