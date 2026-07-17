import { apiFetch } from './api'

export type VocabGrade = 'forgot' | 'vague' | 'mastered'

export interface VocabWord {
  id: string
  word: string
  meaning: string
  book_page: number
  ef: number
  interval_days: number
  due_date: string | null
  reps: number
}

export interface VocabTodayResponse {
  date: string
  due_words: VocabWord[]
  new_words: VocabWord[]
  due_count: number
  learned_count: number
  total_count: number
}

export interface VocabGradeResult {
  word: VocabWord
  grade: VocabGrade
  due_date: string
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
    throw new Error(`Vocab API 请求失败：${response.status}`)
  }
  return (await response.json()) as T
}

export function fetchVocabToday(newLimit = 50): Promise<VocabTodayResponse> {
  return request<VocabTodayResponse>(`/vocab/today?new_limit=${newLimit}`)
}

export function gradeVocabWord(wordId: string, grade: VocabGrade): Promise<VocabGradeResult> {
  return request<VocabGradeResult>(`/vocab/${wordId}/grade`, {
    method: 'POST',
    body: JSON.stringify({ grade }),
  })
}
