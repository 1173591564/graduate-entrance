<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import {
  completeTodayTask,
  fetchToday,
  type TodaySummary,
  type TodayTask,
} from '../services/daily'

const summary = ref<TodaySummary | null>(null)
const selectedDate = ref('')
const actualMinutes = reactive<Record<string, number>>({})
const loading = ref(true)
const busyTaskId = ref('')
const error = ref('')
const notice = ref('')

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

onMounted(() => loadToday())
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
  color: #2764e7;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.today-hero h1 {
  margin: 0;
  font-size: clamp(32px, 5vw, 52px);
}

.today-hero p:last-child {
  margin: 12px 0 0;
  color: #647087;
}

.date-control {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 14px;
  border: 1px solid #dfe6f0;
  border-radius: 16px;
  background: white;
}

.date-control label,
.check-in-control label {
  display: grid;
  gap: 6px;
  color: #526077;
  font-size: 13px;
  font-weight: 750;
}

.date-control button,
.complete-button {
  padding: 10px 16px;
  border: 0;
  border-radius: 10px;
  color: white;
  background: #2764e7;
  cursor: pointer;
  font-weight: 800;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

.summary-grid article {
  display: grid;
  gap: 8px;
  padding: 20px;
  border: 1px solid #e0e6f0;
  border-radius: 18px;
  background: white;
}

.summary-grid span {
  color: #718096;
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
  border: 1px solid #dfe6f0;
  border-radius: 20px;
  background: white;
}

.task-card.completed {
  border-color: #cbe9d4;
  background: #f7fcf8;
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
  font-weight: 750;
}

.subject-badge {
  color: #174cb7;
  background: #edf4ff;
}

.status-badge {
  color: #7b5b11;
  background: #fff6d8;
}

.status-badge.completed {
  color: #236438;
  background: #e2f6e8;
}

.status-badge.skipped {
  color: #687386;
  background: #edf0f4;
}

.task-card h2 {
  margin: 14px 0 4px;
  font-size: 20px;
}

.task-card p {
  margin: 0;
  color: #647087;
}

.task-meta {
  margin-top: 14px;
}

.task-meta span {
  border-radius: 8px;
  color: #526077;
  background: #f0f3f8;
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
  border-radius: 14px;
}

.feedback.error {
  color: #8a2424;
  background: #fff0f0;
}

.feedback.notice {
  color: #236438;
  background: #e9f8ee;
}

.loading-state,
.empty-state {
  color: #718096;
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
