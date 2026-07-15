export interface KnowledgePoint {
  id: string
  name: string
  requirement_raw: string
  requirement_level: string
  requirement_actions: string[]
  common_exam_style: string
  note: string
  order: number
}

export interface SyllabusSection {
  id: string
  name: string
  order: number
  knowledge_points: KnowledgePoint[]
}

export interface SyllabusChapter {
  id: string
  name: string
  order: number
  sections: SyllabusSection[]
  knowledge_points: KnowledgePoint[]
}

export interface SyllabusModule {
  id: string
  name: string
  order: number
  chapters: SyllabusChapter[]
}

export interface ExamSection {
  id: string
  name: string
  score: number | null
  duration_minutes: number | null
  description: string
  order: number
}

export interface ExamBlueprint {
  id: string
  name: string
  total_score: number | null
  duration_minutes: number | null
  description: string
  sections: ExamSection[]
}

export interface SubjectSyllabus {
  id: string
  code: string
  name: string
  order: number
  modules: SyllabusModule[]
  exam_blueprints: ExamBlueprint[]
  source_row_count: number
  knowledge_point_count: number
}

export interface SyllabusVersion {
  id: string
  source_name: string
  source_checksum: string
  row_count: number
  imported_at: string
}

export interface SyllabusTree {
  source_row_count: number
  knowledge_point_count: number
  exam_blueprint_count: number
  versions: SyllabusVersion[]
  subjects: SubjectSyllabus[]
}

export async function fetchSyllabusTree(): Promise<SyllabusTree> {
  const baseUrl = import.meta.env.VITE_API_BASE_URL ?? ''
  const response = await fetch(`${baseUrl}/api/syllabus`)

  if (!response.ok) {
    throw new Error(`Syllabus request failed with status ${response.status}`)
  }

  return (await response.json()) as SyllabusTree
}
