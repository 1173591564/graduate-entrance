<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import {
  addSolution,
  confirmProblem,
  extractProblem,
  fetchPendingProblems,
  fetchProblemImage,
  submitProblem,
  type ExtractedSolution,
  type Problem,
  type ProblemCause,
  type ProblemKind,
  type ProblemKnowledgePointInput,
} from '../services/problems'
import { fetchSyllabusTree } from '../services/syllabus'

interface KnowledgePointOption {
  id: string
  label: string
}

interface SubjectOption {
  id: string
  name: string
}

interface ReviewForm {
  content_md: string
  kind: ProblemKind
  cause: ProblemCause
  my_answer_md: string
  note: string
  source_ref: string
  mappings: ProblemKnowledgePointInput[]
}

const KIND_LABELS: Record<ProblemKind, string> = {
  wrong: '错题',
  hard: '难题',
  good: '好题',
}

const CAUSE_LABELS: Record<ProblemCause, string> = {
  '': '未标注',
  concept: '概念不清',
  calculation: '计算失误',
  method: '方法不会',
  memory: '记忆缺失',
  misread: '审题失误',
  other: '其他',
}

const pending = ref<Problem[]>([])
const knowledgePoints = ref<KnowledgePointOption[]>([])
const subjects = ref<SubjectOption[]>([])
const imageUrls = reactive<Record<string, string>>({})
const forms = reactive<Record<string, ReviewForm>>({})
const loading = ref(true)
const error = ref('')
const feedback = ref('')
const confirmErrors = reactive<Record<string, string>>({})
const extracting = reactive<Record<string, boolean>>({})
const extractErrors = reactive<Record<string, string>>({})
const aiSolutions = reactive<Record<string, ExtractedSolution>>({})

const intake = reactive({
  subjectId: '',
  kind: 'wrong' as ProblemKind,
  contentMd: '',
  sourceRef: '',
  submitting: false,
  error: '',
})
const intakeFiles = ref<File[]>([])

const pendingCount = computed(() => pending.value.length)

function ensureForm(problem: Problem): ReviewForm {
  const existing = forms[problem.id]
  if (existing) {
    return existing
  }
  const form: ReviewForm = {
    content_md: problem.content_md,
    kind: problem.kind,
    cause: problem.cause,
    my_answer_md: problem.my_answer_md,
    note: problem.note,
    source_ref: problem.source_ref,
    mappings: problem.knowledge_points.length
      ? problem.knowledge_points.map((entry) => ({
          knowledge_point_id: entry.knowledge_point_id,
          role: entry.role,
          weight: entry.weight,
        }))
      : [{ knowledge_point_id: '', role: 'primary', weight: 1 }],
  }
  forms[problem.id] = form
  return form
}

async function loadImages(problems: Problem[]): Promise<void> {
  for (const problem of problems) {
    for (const name of problem.images) {
      if (!imageUrls[name]) {
        try {
          imageUrls[name] = await fetchProblemImage(name)
        } catch {
          imageUrls[name] = ''
        }
      }
    }
  }
}

async function loadPending(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const [queue, tree] = await Promise.all([fetchPendingProblems(), fetchSyllabusTree()])
    pending.value = queue.problems
    for (const problem of queue.problems) {
      ensureForm(problem)
    }
    subjects.value = tree.subjects.map((subject) => ({ id: subject.id, name: subject.name }))
    knowledgePoints.value = tree.subjects.flatMap((subject) =>
      subject.modules.flatMap((module) =>
        module.chapters.flatMap((chapter) => [
          ...chapter.knowledge_points.map((point) => ({
            id: point.id,
            label: `${subject.name} · ${chapter.name} · ${point.name}`,
          })),
          ...chapter.sections.flatMap((section) =>
            section.knowledge_points.map((point) => ({
              id: point.id,
              label: `${subject.name} · ${chapter.name} · ${point.name}`,
            })),
          ),
        ]),
      ),
    )
    await loadImages(queue.problems)
  } catch {
    error.value = '待审核题目加载失败'
  } finally {
    loading.value = false
  }
}

function onFilesChange(event: Event): void {
  const input = event.target as HTMLInputElement
  intakeFiles.value = Array.from(input.files ?? [])
}

async function handleSubmitProblem(): Promise<void> {
  intake.error = ''
  if (!intake.contentMd.trim() && intakeFiles.value.length === 0) {
    intake.error = '题面文本与图片至少提供一个'
    return
  }
  intake.submitting = true
  try {
    await submitProblem({
      subjectId: intake.subjectId || undefined,
      kind: intake.kind,
      contentMd: intake.contentMd,
      sourceRef: intake.sourceRef,
      myAnswerMd: '',
      note: '',
      images: intakeFiles.value,
    })
    intake.contentMd = ''
    intake.sourceRef = ''
    intakeFiles.value = []
    feedback.value = '题目已录入待审核队列'
    await loadPending()
  } catch {
    intake.error = '录入失败，请重试'
  } finally {
    intake.submitting = false
  }
}

function addMapping(form: ReviewForm): void {
  form.mappings.push({ knowledge_point_id: '', role: 'secondary', weight: 0 })
}

function removeMapping(form: ReviewForm, index: number): void {
  form.mappings.splice(index, 1)
}

function weightTotal(form: ReviewForm): number {
  return Math.round(form.mappings.reduce((sum, entry) => sum + Number(entry.weight), 0) * 1000) / 1000
}

function validateForm(form: ReviewForm): string {
  if (!form.content_md.trim()) {
    return '题面不能为空'
  }
  if (form.mappings.some((entry) => !entry.knowledge_point_id)) {
    return '请为每条映射选择知识点'
  }
  const primaryCount = form.mappings.filter((entry) => entry.role === 'primary').length
  if (primaryCount !== 1) {
    return '必须且只能有一个主考点'
  }
  if (Math.abs(weightTotal(form) - 1) > 0.001) {
    return '知识点权重之和必须为 1'
  }
  return ''
}

async function handleConfirm(problem: Problem): Promise<void> {
  const form = ensureForm(problem)
  const message = validateForm(form)
  confirmErrors[problem.id] = message
  if (message) {
    return
  }
  try {
    await confirmProblem(problem.id, {
      content_md: form.content_md,
      kind: form.kind,
      cause: form.cause,
      my_answer_md: form.my_answer_md,
      note: form.note,
      source_ref: form.source_ref,
      knowledge_points: form.mappings.map((entry) => ({
        knowledge_point_id: entry.knowledge_point_id,
        role: entry.role,
        weight: Number(entry.weight),
      })),
    })
    pending.value = pending.value.filter((entry) => entry.id !== problem.id)
    delete forms[problem.id]
    feedback.value = '题目已定稿入库'
  } catch {
    confirmErrors[problem.id] = '定稿失败，请检查映射后重试'
  }
}

async function handleExtract(problem: Problem): Promise<void> {
  const form = ensureForm(problem)
  extractErrors[problem.id] = ''
  extracting[problem.id] = true
  try {
    const result = await extractProblem(problem.id)
    if (result.content_md.trim()) {
      form.content_md = result.content_md
    }
    if (result.knowledge_points.length) {
      form.mappings = result.knowledge_points.map((entry) => ({
        knowledge_point_id: entry.knowledge_point_id,
        role: entry.role,
        weight: entry.weight,
      }))
    }
    if (result.solution) {
      aiSolutions[problem.id] = result.solution
    }
    feedback.value = `AI 识别完成（${result.model}），请人工核对后定稿`
  } catch {
    extractErrors[problem.id] = 'AI 识别失败（请确认已配置 AI 服务）'
  } finally {
    extracting[problem.id] = false
  }
}

async function handleAdoptSolution(problem: Problem): Promise<void> {
  const solution = aiSolutions[problem.id]
  if (!solution) {
    return
  }
  try {
    await addSolution(problem.id, {
      content_md: solution.content_md,
      method_tag: solution.method_tag,
      source: 'gpt',
    })
    delete aiSolutions[problem.id]
    feedback.value = 'AI 解法已保存（待人工核验）'
  } catch {
    extractErrors[problem.id] = '解法保存失败，请重试'
  }
}

onMounted(() => loadPending())
</script>

<template>
  <section class="page problems-page">
    <header class="problems-hero">
      <div>
        <p class="eyebrow">
          P2-A · 题库审核
        </p>
        <h1>题目录入与审核台</h1>
        <p>录入错题/难题草稿，人工确认题面与知识点映射后定稿入库。</p>
      </div>
      <span class="pending-count">待审核 {{ pendingCount }}</span>
    </header>

    <form
      class="intake-card"
      @submit.prevent="handleSubmitProblem()"
    >
      <h2>录入新题</h2>
      <div class="intake-grid">
        <label>
          科目
          <select v-model="intake.subjectId">
            <option value="">
              未指定
            </option>
            <option
              v-for="subject in subjects"
              :key="subject.id"
              :value="subject.id"
            >
              {{ subject.name }}
            </option>
          </select>
        </label>
        <label>
          类型
          <select v-model="intake.kind">
            <option
              v-for="(label, value) in KIND_LABELS"
              :key="value"
              :value="value"
            >
              {{ label }}
            </option>
          </select>
        </label>
        <label>
          来源
          <input
            v-model="intake.sourceRef"
            type="text"
            placeholder="真题 2020-3 / 教材 P120"
          >
        </label>
        <label>
          题目图片
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            multiple
            @change="onFilesChange"
          >
        </label>
      </div>
      <label class="intake-content">
        题面（Markdown + LaTeX）
        <textarea
          v-model="intake.contentMd"
          rows="3"
          placeholder="可先只传图片，审核时再补题面"
        />
      </label>
      <p
        v-if="intake.error"
        class="feedback error"
      >
        {{ intake.error }}
      </p>
      <button
        type="submit"
        :disabled="intake.submitting"
      >
        {{ intake.submitting ? '录入中…' : '录入草稿' }}
      </button>
    </form>

    <p
      v-if="feedback"
      class="feedback success"
    >
      {{ feedback }}
    </p>

    <p
      v-if="error"
      class="feedback error"
    >
      {{ error }}
    </p>

    <p
      v-if="loading"
      class="loading-state"
    >
      正在加载待审核题目…
    </p>

    <template v-else>
      <div
        v-if="pending.length"
        class="review-list"
      >
        <article
          v-for="problem in pending"
          :key="problem.id"
          class="review-card"
        >
          <div class="review-heading">
            <h2>{{ KIND_LABELS[problem.kind] }} · {{ problem.subject_name ?? '未指定科目' }}</h2>
            <div class="heading-actions">
              <button
                type="button"
                class="ai-button"
                :disabled="extracting[problem.id]"
                @click="handleExtract(problem)"
              >
                {{ extracting[problem.id] ? 'AI 识别中…' : 'AI 识别' }}
              </button>
              <span class="draft-badge">草稿</span>
            </div>
          </div>
          <p
            v-if="extractErrors[problem.id]"
            class="feedback error"
          >
            {{ extractErrors[problem.id] }}
          </p>
          <div
            v-if="problem.images.length"
            class="image-strip"
          >
            <img
              v-for="name in problem.images"
              :key="name"
              :src="imageUrls[name]"
              :alt="`题目原图 ${name}`"
            >
          </div>
          <label>
            题面
            <textarea
              v-model="ensureForm(problem).content_md"
              rows="4"
            />
          </label>
          <div class="field-grid">
            <label>
              类型
              <select v-model="ensureForm(problem).kind">
                <option
                  v-for="(label, value) in KIND_LABELS"
                  :key="value"
                  :value="value"
                >
                  {{ label }}
                </option>
              </select>
            </label>
            <label>
              错因
              <select v-model="ensureForm(problem).cause">
                <option
                  v-for="(label, value) in CAUSE_LABELS"
                  :key="value"
                  :value="value"
                >
                  {{ label }}
                </option>
              </select>
            </label>
            <label>
              来源
              <input
                v-model="ensureForm(problem).source_ref"
                type="text"
              >
            </label>
          </div>
          <label>
            我的解答 / 错解
            <textarea
              v-model="ensureForm(problem).my_answer_md"
              rows="2"
            />
          </label>
          <label>
            备注
            <textarea
              v-model="ensureForm(problem).note"
              rows="2"
            />
          </label>

          <div class="mapping-editor">
            <div class="mapping-heading">
              <h3>知识点映射</h3>
              <span :class="['weight-total', { invalid: Math.abs(weightTotal(ensureForm(problem)) - 1) > 0.001 }]">
                权重合计 {{ weightTotal(ensureForm(problem)) }}
              </span>
            </div>
            <div
              v-for="(mapping, index) in ensureForm(problem).mappings"
              :key="index"
              class="mapping-row"
            >
              <select v-model="mapping.knowledge_point_id">
                <option value="">
                  选择知识点
                </option>
                <option
                  v-for="option in knowledgePoints"
                  :key="option.id"
                  :value="option.id"
                >
                  {{ option.label }}
                </option>
              </select>
              <select v-model="mapping.role">
                <option value="primary">
                  主考点
                </option>
                <option value="secondary">
                  次考点
                </option>
              </select>
              <input
                v-model.number="mapping.weight"
                type="number"
                min="0.01"
                max="1"
                step="0.05"
              >
              <button
                type="button"
                class="remove-button"
                :disabled="ensureForm(problem).mappings.length <= 1"
                @click="removeMapping(ensureForm(problem), index)"
              >
                移除
              </button>
            </div>
            <button
              type="button"
              class="add-button"
              @click="addMapping(ensureForm(problem))"
            >
              添加知识点
            </button>
          </div>

          <div
            v-if="aiSolutions[problem.id]"
            class="ai-solution"
          >
            <div class="mapping-heading">
              <h3>AI 建议解法</h3>
              <span
                v-if="aiSolutions[problem.id].method_tag"
                class="method-tag"
              >{{ aiSolutions[problem.id].method_tag }}</span>
            </div>
            <p class="ai-solution-content">
              {{ aiSolutions[problem.id].content_md }}
            </p>
            <button
              type="button"
              class="add-button"
              @click="handleAdoptSolution(problem)"
            >
              采纳为解法
            </button>
          </div>

          <p
            v-if="confirmErrors[problem.id]"
            class="feedback error"
          >
            {{ confirmErrors[problem.id] }}
          </p>
          <button
            type="button"
            class="confirm-button"
            @click="handleConfirm(problem)"
          >
            定稿入库
          </button>
        </article>
      </div>

      <p
        v-else
        class="empty-state"
      >
        暂无待审核题目。
      </p>
    </template>
  </section>
</template>

<style scoped>
.problems-page {
  display: grid;
  gap: 24px;
}

.problems-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
}

.eyebrow {
  margin: 0 0 8px;
  color: #2764e7;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.problems-hero h1 {
  margin: 0;
  font-size: clamp(32px, 5vw, 52px);
}

.problems-hero p:last-child {
  margin: 12px 0 0;
  color: #647087;
}

.pending-count {
  padding: 8px 14px;
  border-radius: 999px;
  color: #174cb7;
  background: #edf4ff;
  font-weight: 800;
  white-space: nowrap;
}

.intake-card {
  display: grid;
  gap: 14px;
  padding: 22px;
  border: 1px solid #dfe6f0;
  border-radius: 20px;
  background: white;
}

.intake-card h2 {
  margin: 0;
  font-size: 18px;
}

.intake-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.intake-card label,
.review-card label {
  display: grid;
  gap: 6px;
  color: #526077;
  font-size: 13px;
  font-weight: 750;
}

.intake-card input,
.intake-card select,
.intake-card textarea,
.review-card input,
.review-card select,
.review-card textarea {
  padding: 9px 10px;
  border: 1px solid #d7dfeb;
  border-radius: 10px;
  font: inherit;
}

.intake-card button[type='submit'],
.confirm-button {
  justify-self: start;
  padding: 10px 18px;
  border: 0;
  border-radius: 10px;
  color: white;
  background: #2764e7;
  cursor: pointer;
  font-weight: 800;
}

.intake-card button[type='submit']:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.review-list {
  display: grid;
  gap: 16px;
}

.review-card {
  display: grid;
  gap: 14px;
  padding: 22px;
  border: 1px solid #dfe6f0;
  border-radius: 20px;
  background: white;
}

.review-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.review-heading h2 {
  margin: 0;
  font-size: 18px;
}

.draft-badge {
  padding: 5px 9px;
  border-radius: 999px;
  color: #8a5b12;
  background: #fff3d6;
  font-size: 12px;
  font-weight: 750;
}

.heading-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ai-button {
  padding: 6px 14px;
  border: none;
  border-radius: 999px;
  color: white;
  background: #7048e8;
  font-size: 13px;
  font-weight: 750;
  cursor: pointer;
}

.ai-button:disabled {
  opacity: 0.6;
  cursor: wait;
}

.ai-solution {
  display: grid;
  gap: 8px;
  padding: 14px;
  border: 1px solid #d9ccff;
  border-radius: 14px;
  background: #f6f2ff;
}

.ai-solution-content {
  margin: 0;
  white-space: pre-wrap;
}

.method-tag {
  padding: 4px 10px;
  border-radius: 999px;
  color: #5f3dc4;
  background: #e5dbff;
  font-size: 12px;
  font-weight: 750;
}

.image-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.image-strip img {
  max-width: 240px;
  max-height: 180px;
  border: 1px solid #e0e6f0;
  border-radius: 12px;
  object-fit: contain;
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.mapping-editor {
  display: grid;
  gap: 10px;
  padding: 14px;
  border: 1px dashed #c9d4e5;
  border-radius: 14px;
}

.mapping-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.mapping-heading h3 {
  margin: 0;
  font-size: 15px;
}

.weight-total {
  padding: 4px 9px;
  border-radius: 999px;
  color: #17641e;
  background: #e9f8ec;
  font-size: 12px;
  font-weight: 750;
}

.weight-total.invalid {
  color: #8a2424;
  background: #fff0f0;
}

.mapping-row {
  display: grid;
  grid-template-columns: 1fr 120px 90px auto;
  gap: 8px;
}

.add-button,
.remove-button {
  padding: 8px 12px;
  border: 1px solid #c9d4e5;
  border-radius: 10px;
  color: #2c3a52;
  background: #f6f8fc;
  cursor: pointer;
  font-weight: 750;
}

.remove-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.feedback,
.loading-state,
.empty-state {
  margin: 0;
  padding: 16px 18px;
  border-radius: 14px;
}

.feedback.error {
  color: #8a2424;
  background: #fff0f0;
}

.feedback.success {
  color: #17641e;
  background: #e9f8ec;
}

.loading-state,
.empty-state {
  color: #718096;
  background: white;
}

@media (max-width: 820px) {
  .problems-hero {
    display: flex;
    align-items: stretch;
    flex-direction: column;
  }

  .intake-grid,
  .field-grid {
    grid-template-columns: 1fr;
  }

  .mapping-row {
    grid-template-columns: 1fr;
  }
}
</style>
