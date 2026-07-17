import { apiFetch } from './api'

export interface RetroMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface RetroSubjectSnapshot {
  subject_name: string
  mastery: number
  coverage: number
  target_score: number | null
  estimated_score: number | null
}

export interface RetroGapSuggestion {
  knowledge_point_id: string
  knowledge_point_name: string
  subject_name: string
  mastery: number
  target: number
  gap: number
  suggestion: string
}

export interface RetroContext {
  week_start: string
  week_end: string
  planned_minutes: number
  completed_minutes: number
  total_tasks: number
  completed_tasks: number
  execution_rate: number
  days_to_exam: number
  subjects: RetroSubjectSnapshot[]
  weak_points: string[]
  gap_suggestions: RetroGapSuggestion[]
}

export interface RetroSession {
  context: RetroContext
  messages: RetroMessage[]
}

export interface AiDailyFocus {
  date: string
  focus: string
}

export interface RetroConfirmResult {
  plan: {
    plan: unknown
    advice: {
      week_start: string
      summary: string
      daily_focus: AiDailyFocus[]
      review_suggestions: string[]
      model: string
      created_at: string
    }
  }
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await apiFetch(`/api${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  })
  if (!response.ok) {
    throw new Error(`Retro request failed with status ${response.status}`)
  }
  return (await response.json()) as T
}

export function fetchRetroSession(weekStart?: string): Promise<RetroSession> {
  const query = weekStart ? `?week_start=${weekStart}` : ''
  return requestJson<RetroSession>(`/retro${query}`)
}

export function sendRetroMessage(
  content: string,
  weekStart?: string,
): Promise<{ messages: RetroMessage[] }> {
  return requestJson<{ messages: RetroMessage[] }>('/retro/messages', {
    method: 'POST',
    body: JSON.stringify({ content, week_start: weekStart ?? null }),
  })
}

export function confirmNextWeekPlan(weekStart?: string): Promise<RetroConfirmResult> {
  return requestJson<RetroConfirmResult>('/retro/confirm', {
    method: 'POST',
    body: JSON.stringify({ week_start: weekStart ?? null }),
  })
}
