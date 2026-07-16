import { apiFetch } from './api'

export interface SubjectGoal {
  subject_id: string
  subject_name: string
  target_score: number
  full_score: number
  note: string
  updated_at: string
}

export interface SubjectGoalInput {
  subject_id: string
  target_score: number
  full_score: number
  note?: string
}

export interface WeakKnowledgePoint {
  knowledge_point_id: string
  knowledge_point_name: string
  mastery: number
  problem_count: number
  forgot_reviews: number
}

export interface SubjectMastery {
  subject_id: string
  subject_name: string
  target_score: number | null
  full_score: number | null
  knowledge_point_total: number
  studied_points: number
  coverage: number
  mastery: number
  estimated_score: number | null
  studied_minutes: number
  problem_count: number
  wrong_count: number
  weak_points: WeakKnowledgePoint[]
}

export interface StudyProfile {
  as_of: string
  exam_date: string
  days_to_exam: number
  overall_mastery: number
  overall_coverage: number
  subjects: SubjectMastery[]
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
    throw new Error(`Profile request failed with status ${response.status}`)
  }
  return (await response.json()) as T
}

export function fetchStudyProfile(): Promise<StudyProfile> {
  return requestJson<StudyProfile>('/profile')
}

export function fetchGoals(): Promise<{ goals: SubjectGoal[] }> {
  return requestJson<{ goals: SubjectGoal[] }>('/profile/goals')
}

export function saveGoals(goals: SubjectGoalInput[]): Promise<{ goals: SubjectGoal[] }> {
  return requestJson<{ goals: SubjectGoal[] }>('/profile/goals', {
    method: 'PUT',
    body: JSON.stringify({ goals }),
  })
}
