import { apiFetch } from './api'

export type EssayCategory = 'phrase' | 'sentence' | 'paragraph' | 'template' | 'quote'
export type ReciteResult = 'remembered' | 'forgot'

export interface EssayMaterial {
  id: string
  title: string
  category: EssayCategory
  topic: string
  content_md: string
  translation_md: string
  source: string
  due_date: string | null
  interval_days: number
  recite_count: number
  created_at: string
  updated_at: string
}

export interface EssayMaterialList {
  total: number
  materials: EssayMaterial[]
}

export interface EssayMaterialInput {
  title: string
  category: EssayCategory
  topic: string
  content_md: string
  translation_md: string
  source: string
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
    throw new Error(`Essay request failed with status ${response.status}`)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}

export function fetchMaterials(options: {
  category?: EssayCategory
  q?: string
  dueOnly?: boolean
} = {}): Promise<EssayMaterialList> {
  const params = new URLSearchParams()
  if (options.category) {
    params.set('category', options.category)
  }
  if (options.q) {
    params.set('q', options.q)
  }
  if (options.dueOnly) {
    params.set('due_only', 'true')
  }
  const query = params.toString()
  return requestJson<EssayMaterialList>(`/essay/materials${query ? `?${query}` : ''}`)
}

export function createMaterial(input: EssayMaterialInput): Promise<EssayMaterial> {
  return requestJson<EssayMaterial>('/essay/materials', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function updateMaterial(
  id: string,
  input: Partial<EssayMaterialInput>,
): Promise<EssayMaterial> {
  return requestJson<EssayMaterial>(`/essay/materials/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  })
}

export function deleteMaterial(id: string): Promise<void> {
  return requestJson<void>(`/essay/materials/${id}`, { method: 'DELETE' })
}

export function reciteMaterial(
  id: string,
  result: ReciteResult,
): Promise<{ material: EssayMaterial; next_due: string }> {
  return requestJson<{ material: EssayMaterial; next_due: string }>(
    `/essay/materials/${id}/recite`,
    {
      method: 'POST',
      body: JSON.stringify({ result }),
    },
  )
}
