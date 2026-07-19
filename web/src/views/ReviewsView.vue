<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import {
  fetchDueReviews,
  fetchProblemImage,
  reviewProblem,
  type Problem,
  type ProblemKind,
  type ReviewGrade,
} from '../services/problems'

const KIND_LABELS: Record<ProblemKind, string> = {
  wrong: '错题',
  hard: '难题',
  good: '好题',
}

const GRADE_LABELS: Record<ReviewGrade, string> = {
  forgot: '忘了',
  vague: '模糊',
  mastered: '掌握',
}

const GRADES: ReviewGrade[] = ['forgot', 'vague', 'mastered']

const due = ref<Problem[]>([])
const imageUrls = reactive<Record<string, string>>({})
const revealed = reactive<Record<string, boolean>>({})
const loading = ref(true)
const error = ref('')
const feedback = ref('')
const includeDrafts = ref(true)
const grading = reactive<Record<string, boolean>>({})

const dueCount = computed(() => due.value.length)

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

async function loadDue(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const response = await fetchDueReviews(includeDrafts.value)
    due.value = response.problems
    await loadImages(response.problems)
  } catch {
    error.value = '到期复习卡片加载失败'
  } finally {
    loading.value = false
  }
}

function toggleReveal(problemId: string): void {
  revealed[problemId] = !revealed[problemId]
}

async function handleGrade(problem: Problem, grade: ReviewGrade): Promise<void> {
  grading[problem.id] = true
  try {
    const result = await reviewProblem(problem.id, grade)
    due.value = due.value.filter((entry) => entry.id !== problem.id)
    delete revealed[problem.id]
    feedback.value = `已评级「${GRADE_LABELS[grade]}」，下次复习 ${result.due_date}（间隔 ${result.interval_days} 天）`
  } catch {
    error.value = '复习反馈提交失败，请重试'
  } finally {
    grading[problem.id] = false
  }
}

async function handleToggleDrafts(): Promise<void> {
  includeDrafts.value = !includeDrafts.value
  await loadDue()
}

onMounted(() => loadDue())
</script>

<template>
  <section class="page reviews-page">
    <header class="reviews-hero">
      <div>
        <p class="eyebrow">
          P2-B · SM-2 复习
        </p>
        <h1>到期复习卡片</h1>
        <p>按 SM-2 间隔重复调度，按掌握程度评级后自动更新下次复习时间。草稿题也参与复习。</p>
      </div>
      <span class="due-count">到期 {{ dueCount }}</span>
    </header>

    <div class="toolbar">
      <label class="drafts-toggle">
        <input
          type="checkbox"
          :checked="includeDrafts"
          @change="handleToggleDrafts"
        >
        包含草稿题
      </label>
      <button
        type="button"
        class="refresh-button"
        @click="loadDue"
      >
        刷新
      </button>
    </div>

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
      正在加载到期卡片…
    </p>

    <template v-else>
      <div
        v-if="due.length"
        class="review-deck"
      >
        <article
          v-for="problem in due"
          :key="problem.id"
          class="review-card"
        >
          <div class="review-heading">
            <h2>{{ KIND_LABELS[problem.kind] }} · {{ problem.subject_name ?? '未指定科目' }}</h2>
            <span :class="['status-badge', problem.status]">
              {{ problem.status === 'draft' ? '草稿' : '已定稿' }}
            </span>
          </div>

          <p class="meta">
            复习次数 {{ problem.reps }} · 到期 {{ problem.due_date ?? '—' }}
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

          <div
            v-if="problem.content_md"
            class="content-body"
          >
            {{ problem.content_md }}
          </div>

          <ul
            v-if="problem.knowledge_points.length"
            class="kp-list"
          >
            <li
              v-for="kp in problem.knowledge_points"
              :key="kp.knowledge_point_id"
              :class="{ primary: kp.role === 'primary' }"
            >
              {{ kp.knowledge_point_name }} · {{ kp.role === 'primary' ? '主' : '次' }}
              {{ kp.weight }}
            </li>
          </ul>

          <button
            v-if="!revealed[problem.id] && problem.solutions.length"
            type="button"
            class="reveal-button"
            @click="toggleReveal(problem.id)"
          >
            显示解法
          </button>
          <div
            v-else-if="problem.solutions.length"
            class="solutions"
          >
            <article
              v-for="solution in problem.solutions"
              :key="solution.id"
              class="solution"
            >
              <p class="solution-tag">
                {{ solution.method_tag || '解法' }}
              </p>
              <p>{{ solution.content_md }}</p>
            </article>
          </div>

          <div class="grade-row">
            <button
              v-for="grade in GRADES"
              :key="grade"
              type="button"
              :class="['grade-button', grade]"
              :disabled="grading[problem.id]"
              @click="handleGrade(problem, grade)"
            >
              {{ GRADE_LABELS[grade] }}
            </button>
          </div>
        </article>
      </div>

      <p
        v-else
        class="empty-state"
      >
        今天没有到期复习卡片，休息一下 🎉
      </p>
    </template>
  </section>
</template>

<style scoped>
.reviews-page {
  display: grid;
  gap: 24px;
}

.reviews-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
}

.eyebrow {
  margin: 0 0 8px;
  color: var(--deep);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.reviews-hero h1 {
  margin: 0;
  font-size: clamp(24px, 2.5vw, 30px);
}

.reviews-hero p:last-child {
  margin: 12px 0 0;
  color: var(--ink-soft);
}

.due-count {
  padding: 8px 14px;
  border-radius: 999px;
  color: var(--deep);
  background: var(--paper-warm);
  font-weight: 700;
  white-space: nowrap;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
}

.drafts-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--ink-soft);
  font-weight: 600;
}

.refresh-button {
  padding: 8px 14px;
  border: 1px solid var(--rule);
  border-radius: var(--radius-md);
  color: var(--ink);
  background: var(--paper-warm);
  cursor: pointer;
  font-weight: 600;
}

.review-deck {
  display: grid;
  gap: 16px;
}

.review-card {
  display: grid;
  gap: 12px;
  padding: 22px;
  border: 1px solid var(--rule);
  border-radius: var(--radius-md);
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

.status-badge {
  padding: 5px 9px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.status-badge.draft {
  color: var(--warn);
  background: var(--paper-warm);
}

.status-badge.confirmed {
  color: var(--ok);
  background: var(--paper-warm);
}

.meta {
  margin: 0;
  color: var(--ink-soft);
  font-size: 13px;
  font-weight: 700;
}

.image-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.image-strip img {
  max-width: 240px;
  max-height: 180px;
  border: 1px solid var(--rule);
  border-radius: var(--radius-md);
  object-fit: contain;
}

.content-body {
  padding: 14px;
  border-radius: var(--radius-md);
  background: var(--paper-warm);
  white-space: pre-wrap;
}

.kp-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.kp-list li {
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--rule-soft);
  color: var(--ink-soft);
  font-size: 12px;
  font-weight: 700;
}

.kp-list li.primary {
  background: var(--paper-warm);
  color: var(--deep);
}

.reveal-button {
  justify-self: start;
  padding: 8px 14px;
  border: 1px dashed var(--rule);
  border-radius: var(--radius-md);
  color: var(--ink);
  background: var(--paper-warm);
  cursor: pointer;
  font-weight: 600;
}

.solutions {
  display: grid;
  gap: 10px;
}

.solution {
  padding: 12px 14px;
  border-radius: var(--radius-md);
  border: 1px solid var(--rule);
}

.solution-tag {
  margin: 0 0 4px;
  color: var(--deep);
  font-size: 12px;
  font-weight: 700;
}

.solution p {
  margin: 0;
}

.grade-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.grade-button {
  padding: 12px;
  border: 0;
  border-radius: var(--radius-md);
  color: white;
  cursor: pointer;
  font-weight: 700;
}

.grade-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.grade-button.forgot {
  background: var(--danger);
}

.grade-button.vague {
  background: var(--warn);
}

.grade-button.mastered {
  background: var(--ok);
}

.feedback,
.loading-state,
.empty-state {
  margin: 0;
  padding: 16px 18px;
  border-radius: var(--radius-md);
}

.feedback.error {
  color: var(--danger);
  background: var(--paper-warm);
}

.feedback.success {
  color: var(--ok);
  background: var(--paper-warm);
}

.loading-state,
.empty-state {
  color: var(--ink-soft);
  background: white;
}

@media (max-width: 820px) {
  .reviews-hero {
    display: flex;
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
