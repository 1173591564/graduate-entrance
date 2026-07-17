import { apiFetch } from './api'

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message)
  }
}

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
  priority_score: number
}

export interface TodaySummary {
  date: string
  planned_minutes: number
  completed_minutes: number
  remaining_minutes: number
  due_review_count: number
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
    let message = `Daily request failed with status ${response.status}`
    try {
      const payload = (await response.json()) as { error?: { message?: string } }
      if (payload.error?.message) {
        message = payload.error.message
      }
    } catch {
      // keep the generic message when the body is not JSON
    }
    throw new ApiError(response.status, message)
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

export interface AiDailyFocus {
  date: string
  focus: string
}

export interface AiWeekAdvice {
  week_start: string
  summary: string
  daily_focus: AiDailyFocus[]
  review_suggestions: string[]
  model: string
  created_at: string
}

export interface AiWeekPlan {
  plan: {
    start_date: string
    end_date: string
    persisted: boolean
    tasks: unknown[]
    days: Array<{
      date: string
      available_minutes: number
      planned_minutes: number
      remaining_minutes: number
    }>
    warnings: string[]
  }
  advice: AiWeekAdvice
}

export function generateAiWeekPlan(startDate?: string): Promise<AiWeekPlan> {
  return request<AiWeekPlan>('/plan/ai-week', {
    method: 'POST',
    body: JSON.stringify(startDate ? { start_date: startDate } : {}),
  })
}

export function fetchAiWeekAdvice(weekStart?: string): Promise<AiWeekAdvice> {
  const query = weekStart ? `?week_start=${encodeURIComponent(weekStart)}` : ''
  return request<AiWeekAdvice>(`/plan/ai-week${query}`)
}
