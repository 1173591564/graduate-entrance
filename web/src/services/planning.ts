import { apiFetch } from './api'

export interface PlanningSubject {
  id: string
  code: string
  name: string
  order: number
}

export interface PhaseSubjectRatio {
  subject_id: string
  percentage: number
}

export interface PlanPhaseInput {
  name: string
  start_date: string
  end_date: string
  description: string
  milestones: string[]
  allow_new_tasks: boolean
  order: number
  subject_ratios: PhaseSubjectRatio[]
}

export interface PlanPhase extends PlanPhaseInput {
  id: string
}

export interface AvailabilityRule {
  weekday: number
  available_minutes: number
}

export interface AvailabilityPeriodInput {
  name: string
  start_date: string
  end_date: string
  weekly_target_minutes: number
  order: number
  rules: AvailabilityRule[]
}

export interface AvailabilityPeriod extends AvailabilityPeriodInput {
  id: string
}

export interface AvailabilityExceptionInput {
  date: string
  available_minutes: number
  reason: string
}

export interface AvailabilityException extends AvailabilityExceptionInput {
  id: string
}

export type MaterialType =
  | 'textbook'
  | 'exercise_book'
  | 'past_paper'
  | 'course'
  | 'vocabulary'
  | 'other'

export interface MaterialInput {
  subject_id: string | null
  module_id?: string | null
  name: string
  material_type: MaterialType
  source: string
  description: string
  active: boolean
  order: number
}

export interface Material extends MaterialInput {
  id: string
}

export type TaskType =
  | 'reading'
  | 'practice'
  | 'dictation'
  | 'past_paper'
  | 'memorization'
  | 'review'

export interface TaskTemplateInput {
  subject_id: string
  material_id: string | null
  name: string
  task_type: TaskType
  default_est_minutes: number
  description: string
  active: boolean
  order: number
  phase_ids: string[]
}

export interface TaskTemplate extends TaskTemplateInput {
  id: string
}

export interface PlanningConfig {
  subjects: PlanningSubject[]
  phases: PlanPhase[]
  availability_periods: AvailabilityPeriod[]
  availability_exceptions: AvailabilityException[]
  materials: Material[]
  task_templates: TaskTemplate[]
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await apiFetch(`/api/planning${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  })
  if (!response.ok) {
    throw new Error(`Planning request failed with status ${response.status}`)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}

export function fetchPlanningConfig(): Promise<PlanningConfig> {
  return request<PlanningConfig>('/config')
}

export function createPlanPhase(payload: PlanPhaseInput): Promise<PlanPhase> {
  return request<PlanPhase>('/phases', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function deletePlanPhase(id: string): Promise<void> {
  return request<void>(`/phases/${id}`, { method: 'DELETE' })
}

export function createAvailabilityPeriod(
  payload: AvailabilityPeriodInput,
): Promise<AvailabilityPeriod> {
  return request<AvailabilityPeriod>('/availability-periods', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function deleteAvailabilityPeriod(id: string): Promise<void> {
  return request<void>(`/availability-periods/${id}`, { method: 'DELETE' })
}

export function createAvailabilityException(
  payload: AvailabilityExceptionInput,
): Promise<AvailabilityException> {
  return request<AvailabilityException>('/availability-exceptions', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function deleteAvailabilityException(id: string): Promise<void> {
  return request<void>(`/availability-exceptions/${id}`, { method: 'DELETE' })
}

export function createMaterial(payload: MaterialInput): Promise<Material> {
  return request<Material>('/materials', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function deleteMaterial(id: string): Promise<void> {
  return request<void>(`/materials/${id}`, { method: 'DELETE' })
}

export function createTaskTemplate(payload: TaskTemplateInput): Promise<TaskTemplate> {
  return request<TaskTemplate>('/task-templates', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function deleteTaskTemplate(id: string): Promise<void> {
  return request<void>(`/task-templates/${id}`, { method: 'DELETE' })
}
