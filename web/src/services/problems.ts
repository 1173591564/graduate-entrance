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

export async function fetchProblemImage(name: string): Promise<string> {
  const response = await apiFetch(`/api/problems/images/${encodeURIComponent(name)}`)
  if (!response.ok) {
    throw new Error(`Problems request failed with status ${response.status}`)
  }
  return URL.createObjectURL(await response.blob())
}
