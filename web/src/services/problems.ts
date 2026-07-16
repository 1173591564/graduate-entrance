import { apiFetch } from './api'

export type ProblemKind = 'wrong' | 'hard' | 'good'
export type ProblemCause =
  | ''
  | 'concept'
  | 'calculation'
  | 'method'
  | 'memory'
  | 'misread'
  | 'other'
export type ProblemStatus = 'draft' | 'confirmed'
export type KnowledgePointRole = 'primary' | 'secondary'

export interface ProblemKnowledgePointInput {
  knowledge_point_id: string
  role: KnowledgePointRole
  weight: number
}

export interface ProblemKnowledgePointRead {
  knowledge_point_id: string
  knowledge_point_name: string
  role: KnowledgePointRole
  weight: number
}

export interface SolutionRead {
  id: string
  content_md: string
  method_tag: string
  source: 'self' | 'answer' | 'gpt'
  verified: boolean
  created_at: string
}

export interface Problem {
  id: string
  subject_id: string | null
  subject_name: string | null
  content_md: string
  images: string[]
  source_ref: string
  kind: ProblemKind
  my_answer_md: string
  cause: ProblemCause
  note: string
  status: ProblemStatus
  due_date: string | null
  reps: number
  confirmed_at: string | null
  created_at: string
  knowledge_points: ProblemKnowledgePointRead[]
  solutions: SolutionRead[]
}

export interface PendingProblems {
  total: number
  problems: Problem[]
}

export type ReviewGrade = 'forgot' | 'vague' | 'mastered'

export interface DueReviews {
  total: number
  as_of: string
  problems: Problem[]
}

export interface ReviewResult {
  problem: Problem
  grade: ReviewGrade
  ef: number
  interval_days: number
  reps: number
  due_date: string
}

export interface ProblemConfirmPayload {
  content_md: string
  kind: ProblemKind
  cause: ProblemCause
  my_answer_md: string
  note: string
  source_ref: string
  knowledge_points: ProblemKnowledgePointInput[]
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
    throw new Error(`Problems request failed with status ${response.status}`)
  }
  return (await response.json()) as T
}

export interface ProblemSubmitInput {
  subjectId?: string
  kind: ProblemKind
  contentMd: string
  sourceRef: string
  myAnswerMd: string
  note: string
  images: File[]
}

export async function submitProblem(input: ProblemSubmitInput): Promise<Problem> {
  const form = new FormData()
  if (input.subjectId) {
    form.set('subject_id', input.subjectId)
  }
  form.set('kind', input.kind)
  form.set('content_md', input.contentMd)
  form.set('source_ref', input.sourceRef)
  form.set('my_answer_md', input.myAnswerMd)
  form.set('note', input.note)
  for (const image of input.images) {
    form.append('images', image)
  }
  const response = await apiFetch('/api/problems', {
    method: 'POST',
    body: form,
  })
  if (!response.ok) {
    throw new Error(`Problems request failed with status ${response.status}`)
  }
  return (await response.json()) as Problem
}

export function fetchPendingProblems(): Promise<PendingProblems> {
  return requestJson<PendingProblems>('/problems/pending')
}

export function confirmProblem(id: string, payload: ProblemConfirmPayload): Promise<Problem> {
  return requestJson<Problem>(`/problems/${id}/confirm`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export interface ExtractedKnowledgePoint {
  knowledge_point_id: string
  knowledge_point_name: string
  role: KnowledgePointRole
  weight: number
}

export interface ExtractedSolution {
  content_md: string
  method_tag: string
}

export interface ProblemExtractionResult {
  problem_id: string
  model: string
  content_md: string
  knowledge_points: ExtractedKnowledgePoint[]
  solution: ExtractedSolution | null
}

export interface SolutionCreatePayload {
  content_md: string
  method_tag: string
  source: 'self' | 'answer' | 'gpt'
}

export function addSolution(id: string, payload: SolutionCreatePayload): Promise<Problem> {
  return requestJson<Problem>(`/problems/${id}/solutions`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function extractProblem(id: string): Promise<ProblemExtractionResult> {
  return requestJson<ProblemExtractionResult>(`/problems/${id}/extract`, {
    method: 'POST',
  })
}

export function fetchDueReviews(includeDrafts = true): Promise<DueReviews> {
  const query = includeDrafts ? '' : '?include_drafts=false'
  return requestJson<DueReviews>(`/problems/reviews/due${query}`)
}

export function reviewProblem(id: string, grade: ReviewGrade): Promise<ReviewResult> {
  return requestJson<ReviewResult>(`/problems/${id}/review`, {
    method: 'POST',
    body: JSON.stringify({ grade }),
  })
}

export async function fetchProblemImage(name: string): Promise<string> {
  const response = await apiFetch(`/api/problems/images/${encodeURIComponent(name)}`)
  if (!response.ok) {
    throw new Error(`Problems request failed with status ${response.status}`)
  }
  return URL.createObjectURL(await response.blob())
}

export interface KnowledgePointInsight {
  knowledge_point_id: string
  knowledge_point_name: string
  problem_count: number
  weighted_errors: number
  forgot_reviews: number
  total_reviews: number
  weakness_score: number
}

export interface CauseInsight {
  cause: ProblemCause
  count: number
}

export interface SubjectInsight {
  subject_id: string | null
  subject_name: string
  problem_count: number
  wrong_count: number
}

export interface WeeklyTrendPoint {
  week_start: string
  new_problems: number
  reviews: number
  forgot: number
  vague: number
  mastered: number
}

export interface ProblemInsights {
  as_of: string
  total_problems: number
  confirmed_problems: number
  knowledge_points: KnowledgePointInsight[]
  causes: CauseInsight[]
  subjects: SubjectInsight[]
  weekly_trend: WeeklyTrendPoint[]
}

export function fetchProblemInsights(): Promise<ProblemInsights> {
  return requestJson<ProblemInsights>('/stats/insights')
}
