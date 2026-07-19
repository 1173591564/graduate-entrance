<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import {
  ApiError,
  completeTodayTask,
  fetchAiWeekAdvice,
  fetchToday,
  generateAiWeekPlan,
  reschedulePlan,
  type AiWeekAdvice,
  type TodaySummary,
  type TodayTask,
} from '../services/daily'

const summary = ref<TodaySummary | null>(null)
const selectedDate = ref('')
const actualMinutes = reactive<Record<string, number>>({})
const loading = ref(true)
const busyTaskId = ref('')
const rescheduling = ref(false)
const error = ref('')
const notice = ref('')
const aiAdvice = ref<AiWeekAdvice | null>(null)
const aiGenerating = ref(false)
const aiError = ref('')
const aiExpanded = ref(false)

const completedCount = computed(
  () => summary.value?.tasks.filter((task) => task.status === 'completed').length ?? 0,
)

function formatMinutes(minutes: number): string {
  if (minutes < 60) {
    return `${minutes} 分钟`
  }
  const hours = Math.floor(minutes / 60)
  const remainder = minutes % 60
  return remainder === 0 ? `${hours} 小时` : `${hours} 小时 ${remainder} 分钟`
}

function taskStatus(task: TodayTask): string {
  if (task.status === 'completed') {
    return `已完成 ${task.actual_minutes ?? task.est_minutes} 分钟`
  }
  if (task.status === 'skipped') {
    return '已跳过'
  }
  return '待完成'
}

function applySummary(payload: TodaySummary): void {
  summary.value = payload
  selectedDate.value = payload.date
  for (const task of payload.tasks) {
    actualMinutes[task.id] = task.actual_minutes ?? task.est_minutes
  }
}

async function loadToday(date?: string): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    applySummary(await fetchToday(date))
  } catch {
    error.value = '今日任务加载失败'
  } finally {
    loading.value = false
  }
}

async function complete(task: TodayTask): Promise<void> {
  busyTaskId.value = task.id
  error.value = ''
  notice.value = ''
  try {
    await completeTodayTask(task.id, Number(actualMinutes[task.id]))
    await loadToday(selectedDate.value)
    notice.value = `${task.title} 已打卡`
  } catch {
    error.value = '打卡失败，请稍后重试'
  } finally {
    busyTaskId.value = ''
  }
}

async function reschedule(leave: boolean): Promise<void> {
  if (!selectedDate.value) {
    return
  }
  rescheduling.value = true
  error.value = ''
  notice.value = ''
  try {
    const result = await reschedulePlan({
      startDate: selectedDate.value,
      leaveDates: leave ? [selectedDate.value] : [],
    })
    await loadToday(selectedDate.value)
    notice.value = leave
      ? `${result.start_date} 已请假，顺延 ${result.carried_over} 项任务并重排至 ${result.end_date}`
      : `已从 ${result.start_date} 重排至 ${result.end_date}，顺延 ${result.carried_over} 项任务`
  } catch {
    error.value = '重排失败，请稍后重试'
  } finally {
    rescheduling.value = false
  }
}

const todayFocus = computed(() => {
  if (!aiAdvice.value || !summary.value) {
    return null
  }
  return (
    aiAdvice.value.daily_focus.find((entry) => entry.date === summary.value?.date) ?? null
  )
})

async function loadAiAdvice(): Promise<void> {
  try {
    aiAdvice.value = await fetchAiWeekAdvice(selectedDate.value || undefined)
  } catch {
    aiAdvice.value = null
  }
}

async function generateWeekPlan(): Promise<void> {
  aiGenerating.value = true
  aiError.value = ''
  try {
    const result = await generateAiWeekPlan()
    aiAdvice.value = result.advice
    aiExpanded.value = true
    notice.value = `已生成 ${result.plan.start_date} ~ ${result.plan.end_date} 计划并排入日历`
    await loadToday(selectedDate.value)
  } catch (error) {
    aiError.value =
      error instanceof ApiError && error.status === 409
        ? error.message
        : 'AI 生成失败，请确认已配置 AI 或稍后重试'
  } finally {
    aiGenerating.value = false
  }
}

onMounted(async () => {
  await loadToday()
  await loadAiAdvice()
})
</script>

<template>
  <section class="page today-page">
    <header class="today-hero">
      <div>
        <p class="eyebrow">
          P0-D · 每日执行层
        </p>
        <h1>今日任务</h1>
        <p>按排程完成当天学习任务，打卡时记录真实耗时。</p>
      </div>
      <form
        class="date-control"
        @submit.prevent="loadToday(selectedDate)"
      >
        <label>
          查看日期
          <input
            v-model="selectedDate"
            type="date"
          >
        </label>
        <button type="submit">
          查看
        </button>
      </form>
    </header>

    <div class="plan-actions">
      <button
        class="reschedule-button"
        type="button"
        :disabled="rescheduling"
        @click="reschedule(false)"
      >
        {{ rescheduling ? '重排中…' : '一键从当前日期重排' }}
      </button>
      <button
        class="leave-button"
        type="button"
        :disabled="rescheduling"
        @click="reschedule(true)"
      >
        请假并重排
      </button>
      <button
        class="ai-week-button"
        type="button"
        :disabled="aiGenerating"
        @click="generateWeekPlan()"
      >
        {{ aiGenerating ? 'AI 生成中…' : 'AI 一键生成下周计划' }}
      </button>
    </div>

    <p
      v-if="aiError"
      class="feedback error"
    >
      {{ aiError }}
    </p>

    <article
      v-if="aiAdvice"
      class="ai-advice-card"
    >
      <div class="ai-advice-heading">
        <h2>AI 周计划建议（{{ aiAdvice.week_start }} 起）</h2>
        <button
          type="button"
          class="toggle-button"
          @click="aiExpanded = !aiExpanded"
        >
          {{ aiExpanded ? '收起' : '展开每日重点' }}
        </button>
      </div>
      <p class="ai-summary">
        {{ aiAdvice.summary }}
      </p>
      <p
        v-if="todayFocus"
        class="ai-today-focus"
      >
        今日重点：{{ todayFocus.focus }}
      </p>
      <template v-if="aiExpanded">
        <ul class="ai-focus-list">
          <li
            v-for="entry in aiAdvice.daily_focus"
            :key="entry.date"
          >
            <span class="focus-date">{{ entry.date }}</span>
            <span>{{ entry.focus }}</span>
          </li>
        </ul>
        <ul
          v-if="aiAdvice.review_suggestions.length"
          class="ai-suggestion-list"
        >
          <li
            v-for="suggestion in aiAdvice.review_suggestions"
            :key="suggestion"
          >
            {{ suggestion }}
          </li>
        </ul>
      </template>
    </article>

    <p
      v-if="error"
      class="feedback error"
    >
      {{ error }}
    </p>
    <p
      v-if="notice"
      class="feedback notice"
    >
      {{ notice }}
    </p>

    <p
      v-if="loading"
      class="loading-state"
    >
      正在加载今日任务…
    </p>

    <template v-else-if="summary">
      <div class="summary-grid">
        <article>
          <span>计划时长</span>
          <strong>{{ formatMinutes(summary.planned_minutes) }}</strong>
        </article>
        <article>
          <span>已完成</span>
          <strong>{{ formatMinutes(summary.completed_minutes) }}</strong>
        </article>
        <article>
          <span>剩余任务</span>
          <strong>{{ formatMinutes(summary.remaining_minutes) }}</strong>
        </article>
        <article>
          <span>完成进度</span>
          <strong>{{ completedCount }} / {{ summary.tasks.length }}</strong>
        </article>
        <article
          v-if="summary.due_review_count > 0"
          class="due-review-card"
        >
          <span>到期复习</span>
          <strong>{{ summary.due_review_count }} 项</strong>
          <RouterLink to="/reviews">
            去复习
          </RouterLink>
        </article>
      </div>

      <div
        v-if="summary.tasks.length"
        class="task-list"
      >
        <article
          v-for="task in summary.tasks"
          :key="task.id"
          class="task-card"
          :class="{ completed: task.status === 'completed' }"
        >
          <div class="task-main">
            <div class="task-heading">
              <span class="subject-badge">{{ task.subject_name }}</span>
              <span
                class="status-badge"
                :class="task.status"
              >
                {{ taskStatus(task) }}
              </span>
            </div>
            <h2>{{ task.title }}</h2>
            <p>{{ task.knowledge_point_name }}</p>
            <div class="task-meta">
              <span>预计 {{ formatMinutes(task.est_minutes) }}</span>
              <span v-if="task.material_name">{{ task.material_name }}</span>
              <span v-if="task.carry_count">已顺延 {{ task.carry_count }} 次</span>
              <span
                v-if="task.status === 'planned' && task.priority_score > 0"
                class="priority-badge"
                title="优先级 = 知识点分值权重 × 掌握缺口 × 时间性价比"
              >
                优先级 {{ task.priority_score.toFixed(2) }}
              </span>
            </div>
          </div>

          <div
            v-if="task.status === 'planned'"
            class="check-in-control"
          >
            <label>
              实际耗时（分钟）
              <input
                v-model.number="actualMinutes[task.id]"
                type="number"
                min="0"
                max="1440"
              >
            </label>
            <button
              class="complete-button"
              type="button"
              :disabled="busyTaskId === task.id"
              @click="complete(task)"
            >
              {{ busyTaskId === task.id ? '提交中…' : '完成打卡' }}
            </button>
          </div>
        </article>
      </div>

      <p
        v-else
        class="empty-state"
      >
        {{ summary.date }} 暂无已排任务。
      </p>
    </template>
  </section>
</template>

<style scoped>
.today-page {
  display: grid;
  gap: 24px;
}

.today-hero {
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

.today-hero h1 {
  margin: 0;
  font-size: clamp(24px, 2.5vw, 30px);
}

.today-hero p:last-child {
  margin: 12px 0 0;
  color: var(--ink-soft);
}

.date-control {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 14px;
  border: 1px solid var(--rule);
  border-radius: var(--radius-md);
  background: white;
}

.date-control label,
.check-in-control label {
  display: grid;
  gap: 6px;
  color: var(--ink-soft);
  font-size: 13px;
  font-weight: 600;
}

.date-control button,
.complete-button {
  padding: 10px 16px;
  border: 0;
  border-radius: var(--radius-md);
  color: white;
  background: var(--brand);
  cursor: pointer;
  font-weight: 700;
}

.plan-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.reschedule-button,
.leave-button {
  padding: 10px 16px;
  border: 1px solid var(--deep);
  border-radius: var(--radius-md);
  color: var(--deep);
  background: white;
  cursor: pointer;
  font-weight: 700;
}

.leave-button {
  border-color: var(--warn);
  color: var(--warn);
}

.ai-week-button {
  padding: 10px 16px;
  border: 0;
  border-radius: var(--radius-md);
  color: white;
  background: var(--brand);
  cursor: pointer;
  font-weight: 700;
}

.ai-advice-card {
  display: grid;
  gap: 12px;
  padding: 22px;
  border: 1px solid var(--rule);
  border-radius: var(--radius-md);
  background: linear-gradient(150deg, var(--paper-warm), var(--card));
}

.ai-advice-heading {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.ai-advice-heading h2 {
  margin: 0;
  font-size: 18px;
}

.toggle-button {
  padding: 6px 12px;
  border: 1px solid var(--accent-cs);
  border-radius: 999px;
  color: var(--accent-cs);
  background: white;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
}

.ai-summary {
  margin: 0;
  color: var(--ink);
}

.ai-today-focus {
  margin: 0;
  padding: 10px 14px;
  border-radius: var(--radius-md);
  color: var(--accent-cs);
  background: var(--paper-warm);
  font-weight: 600;
}

.ai-focus-list,
.ai-suggestion-list {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.ai-focus-list li {
  display: flex;
  gap: 10px;
  color: var(--ink);
  font-size: 14px;
}

.focus-date {
  flex-shrink: 0;
  color: var(--accent-cs);
  font-weight: 600;
}

.ai-suggestion-list li {
  padding: 8px 12px;
  border-radius: var(--radius-md);
  color: var(--ink);
  background: white;
  font-size: 14px;
}

.reschedule-button:disabled,
.leave-button:disabled,
.ai-week-button:disabled {
  opacity: 0.6;
  cursor: wait;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 14px;
}

.due-review-card {
  border-left: 3px solid var(--deep);
}

.due-review-card a {
  color: var(--deep);
  font-size: 13px;
  font-weight: 700;
}

.summary-grid article {
  display: grid;
  gap: 8px;
  padding: 20px;
  border: 1px solid var(--rule);
  border-radius: var(--radius-md);
  background: white;
}

.summary-grid span {
  color: var(--ink-soft);
  font-size: 13px;
  font-weight: 700;
}

.summary-grid strong {
  font-size: 24px;
}

.task-list {
  display: grid;
  gap: 14px;
}

.task-card {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 24px;
  padding: 22px;
  border: 1px solid var(--rule);
  border-radius: var(--radius-md);
  background: white;
}

.task-card.completed {
  border-color: var(--ok);
  background: var(--paper-warm);
}

.task-heading,
.task-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.subject-badge,
.status-badge,
.task-meta span {
  padding: 5px 9px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.subject-badge {
  color: var(--deep);
  background: var(--paper-warm);
}

.status-badge {
  color: var(--warn);
  background: var(--paper-warm);
}

.status-badge.completed {
  color: var(--ok);
  background: var(--paper-warm);
}

.status-badge.skipped {
  color: var(--ink-soft);
  background: var(--rule-soft);
}

.task-card h2 {
  margin: 14px 0 4px;
  font-size: 20px;
}

.task-card p {
  margin: 0;
  color: var(--ink-soft);
}

.task-meta {
  margin-top: 14px;
}

.task-meta span {
  border-radius: var(--radius-md);
  color: var(--ink-soft);
  background: var(--paper-warm);
}

.task-meta .priority-badge {
  color: var(--deep);
  background: white;
  border: 1px solid var(--rule);
  cursor: help;
}

.check-in-control {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  min-width: 280px;
}

.check-in-control input {
  width: 130px;
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

.feedback.notice {
  color: var(--ok);
  background: var(--paper-warm);
}

.loading-state,
.empty-state {
  color: var(--ink-soft);
  background: white;
}

@media (max-width: 820px) {
  .today-hero,
  .task-card,
  .check-in-control {
    align-items: stretch;
    flex-direction: column;
  }

  .today-hero,
  .check-in-control {
    display: flex;
  }

  .task-card {
    grid-template-columns: 1fr;
  }

  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .check-in-control input {
    width: 100%;
  }
}

@media (max-width: 520px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .date-control {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
