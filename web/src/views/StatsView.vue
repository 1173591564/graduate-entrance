<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { fetchWeeklyStats, type WeeklyStat, type WeeklyStatsSummary } from '../services/daily'

const summary = ref<WeeklyStatsSummary | null>(null)
const startDate = ref('')
const endDate = ref('')
const loading = ref(true)
const error = ref('')

function formatMinutes(minutes: number): string {
  if (minutes < 60) {
    return `${minutes} 分钟`
  }
  const hours = Math.floor(minutes / 60)
  const remainder = minutes % 60
  return remainder === 0 ? `${hours} 小时` : `${hours} 小时 ${remainder} 分钟`
}

function formatRate(rate: number): string {
  return `${Math.round(rate * 1000) / 10}%`
}

function targetStatus(week: WeeklyStat): string {
  if (week.target_minutes === null) {
    return ''
  }
  if (week.planned_minutes < week.target_minutes) {
    return 'below-target'
  }
  return 'on-target'
}

async function loadStats(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    summary.value = await fetchWeeklyStats({
      start: startDate.value || undefined,
      end: endDate.value || undefined,
    })
  } catch {
    error.value = '周统计加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(() => loadStats())
</script>

<template>
  <section class="page stats-page">
    <header class="stats-hero">
      <div>
        <p class="eyebrow">
          P0-E · 执行统计
        </p>
        <h1>周时长与执行率</h1>
        <p>按周对比计划与实际学习时长，检查执行率与周目标。</p>
      </div>
      <form
        class="range-control"
        @submit.prevent="loadStats()"
      >
        <label>
          开始日期
          <input
            v-model="startDate"
            type="date"
          >
        </label>
        <label>
          结束日期
          <input
            v-model="endDate"
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
      v-if="loading"
      class="loading-state"
    >
      正在加载周统计…
    </p>

    <template v-else-if="summary">
      <div class="summary-grid">
        <article>
          <span>统计范围</span>
          <strong>{{ summary.start_date }} ~ {{ summary.end_date }}</strong>
        </article>
        <article>
          <span>计划总时长</span>
          <strong>{{ formatMinutes(summary.total_planned_minutes) }}</strong>
        </article>
        <article>
          <span>完成总时长</span>
          <strong>{{ formatMinutes(summary.total_completed_minutes) }}</strong>
        </article>
        <article>
          <span>总执行率</span>
          <strong>{{ formatRate(summary.overall_execution_rate) }}</strong>
        </article>
      </div>

      <div
        v-if="summary.weeks.length"
        class="week-list"
      >
        <article
          v-for="week in summary.weeks"
          :key="week.week_start"
          class="week-card"
          :class="targetStatus(week)"
        >
          <div class="week-heading">
            <h2>{{ week.week_start }} ~ {{ week.week_end }}</h2>
            <span class="rate-badge">执行率 {{ formatRate(week.execution_rate) }}</span>
          </div>
          <div class="week-meta">
            <span>计划 {{ formatMinutes(week.planned_minutes) }}</span>
            <span>完成 {{ formatMinutes(week.completed_minutes) }}</span>
            <span>任务 {{ week.completed_tasks }} / {{ week.total_tasks }}</span>
            <span v-if="week.target_minutes !== null">
              周目标 {{ formatMinutes(week.target_minutes) }}
            </span>
            <span
              v-if="week.target_minutes !== null && week.planned_minutes < week.target_minutes"
              class="warning-badge"
            >
              低于周目标
            </span>
          </div>
          <div class="progress-track">
            <div
              class="progress-fill"
              :style="{ width: `${Math.min(week.execution_rate, 1) * 100}%` }"
            />
          </div>
        </article>
      </div>

      <p
        v-else
        class="empty-state"
      >
        当前范围内暂无已排任务。
      </p>
    </template>
  </section>
</template>

<style scoped>
.stats-page {
  display: grid;
  gap: 24px;
}

.stats-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
}

.eyebrow {
  margin: 0 0 8px;
  color: var(--deep);
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.stats-hero h1 {
  margin: 0;
  font-size: clamp(32px, 5vw, 52px);
}

.stats-hero p:last-child {
  margin: 12px 0 0;
  color: var(--ink-soft);
}

.range-control {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 14px;
  border: 1px solid var(--rule);
  border-radius: 3px;
  background: white;
}

.range-control label {
  display: grid;
  gap: 6px;
  color: var(--ink-soft);
  font-size: 13px;
  font-weight: 750;
}

.range-control button {
  padding: 10px 16px;
  border: 0;
  border-radius: 3px;
  color: white;
  background: var(--deep);
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
  border: 1px solid var(--rule);
  border-radius: 3px;
  background: white;
}

.summary-grid span {
  color: var(--ink-soft);
  font-size: 13px;
  font-weight: 700;
}

.summary-grid strong {
  font-size: 20px;
}

.week-list {
  display: grid;
  gap: 14px;
}

.week-card {
  display: grid;
  gap: 12px;
  padding: 22px;
  border: 1px solid var(--rule);
  border-radius: 3px;
  background: white;
}

.week-card.below-target {
  border-color: var(--warn);
  background: var(--paper-warm);
}

.week-heading {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.week-heading h2 {
  margin: 0;
  font-size: 18px;
}

.rate-badge {
  padding: 5px 9px;
  border-radius: 999px;
  color: var(--deep);
  background: var(--paper-warm);
  font-size: 12px;
  font-weight: 750;
}

.week-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.week-meta span {
  padding: 5px 9px;
  border-radius: 3px;
  color: var(--ink-soft);
  background: var(--paper-warm);
  font-size: 12px;
  font-weight: 750;
}

.week-meta .warning-badge {
  color: var(--warn);
  background: var(--paper-warm);
}

.progress-track {
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--rule-soft);
}

.progress-fill {
  height: 100%;
  border-radius: 999px;
  background: var(--deep);
}

.feedback,
.loading-state,
.empty-state {
  margin: 0;
  padding: 16px 18px;
  border-radius: 3px;
}

.feedback.error {
  color: var(--danger);
  background: var(--paper-warm);
}

.loading-state,
.empty-state {
  color: var(--ink-soft);
  background: white;
}

@media (max-width: 820px) {
  .stats-hero {
    display: flex;
    align-items: stretch;
    flex-direction: column;
  }

  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 520px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .range-control {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
