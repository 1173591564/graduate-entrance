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

export interface RescheduleSummary {
  start_date: string
  end_date: string
  carried_over: number
  warnings: string[]
}

export function reschedulePlan(options: {
  startDate: string
  leaveDates?: string[]
}): Promise<RescheduleSummary> {
  return request<RescheduleSummary>('/plan/reschedule', {
    method: 'POST',
    body: JSON.stringify({
      start_date: options.startDate,
      leave_dates: options.leaveDates ?? [],
    }),
  })
}

export interface WeeklyStat {
  week_start: string
  week_end: string
  planned_minutes: number
  completed_minutes: number
  target_minutes: number | null
  total_tasks: number
  completed_tasks: number
  execution_rate: number
}

export interface WeeklyStatsSummary {
  start_date: string
  end_date: string
  weeks: WeeklyStat[]
  total_planned_minutes: number
  total_completed_minutes: number
  overall_execution_rate: number
}

export function fetchWeeklyStats(options?: {
  start?: string
  end?: string
}): Promise<WeeklyStatsSummary> {
  const params = new URLSearchParams()
  if (options?.start) {
    params.set('start', options.start)
  }
  if (options?.end) {
    params.set('end', options.end)
  }
  const query = params.toString()
  return request<WeeklyStatsSummary>(`/stats/weekly${query ? `?${query}` : ''}`)
}

export function completeTodayTask(id: string, actualMinutes: number): Promise<TodayTask> {
  return request<TodayTask>(`/tasks/${id}/done`, {
    method: 'POST',
    body: JSON.stringify({ actual_minutes: actualMinutes }),
  })
}
