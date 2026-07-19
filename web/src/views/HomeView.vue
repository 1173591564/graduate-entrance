<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import StatusBadge from '../components/StatusBadge.vue'
import {
  confirmAiWeekPlan,
  fetchAiWeekAdvice,
  fetchAutomationRuns,
  fetchWeeklyStats,
  type AiWeekAdvice,
  type AutomationRun,
  type WeeklyStatsSummary,
} from '../services/daily'
import { fetchServiceStatus } from '../services/health'
import { fetchStudyProfile, type StudyProfile } from '../services/profile'

const status = ref<'checking' | 'online' | 'offline'>('checking')
const profile = ref<StudyProfile | null>(null)
const weekly = ref<WeeklyStatsSummary | null>(null)
const loading = ref(true)
const error = ref('')
const automationRuns = ref<AutomationRun[]>([])
const draftAdvice = ref<AiWeekAdvice | null>(null)
const confirming = ref(false)

const JOB_LABELS: Record<string, string> = {
  weekly_plan_draft: '周计划草稿',
  daily_mastery_watch: '掌握度监控',
  daily_backlog_check: '欠账检查',
}

const STATUS_LABELS: Record<string, string> = {
  success: '成功',
  skipped: '无需动作',
  failed: '失败',
}

function runSummary(run: AutomationRun): string {
  const detail = run.detail
  const alerts = detail.alerts
  if (Array.isArray(alerts) && alerts.length > 0) {
    return alerts.join('；')
  }
  const inserted = detail.inserted
  if (Array.isArray(inserted) && inserted.length > 0) {
    return `自动插入复习：${inserted.join('、')}`
  }
  if (typeof detail.reason === 'string') {
    return detail.reason
  }
  if (typeof detail.error === 'string') {
    return detail.error
  }
  return ''
}

async function confirmDraft(): Promise<void> {
  if (!draftAdvice.value || confirming.value) {
    return
  }
  confirming.value = true
  try {
    const result = await confirmAiWeekPlan(draftAdvice.value.week_start)
    draftAdvice.value = result.advice.status === 'draft' ? result.advice : null
  } catch {
    // 保留草稿状态，用户可重试
  } finally {
    confirming.value = false
  }
}

const hasGoals = computed(
  () => profile.value?.subjects.some((subject) => subject.target_score !== null) ?? false,
)

const currentWeek = computed(() => {
  const weeks = weekly.value?.weeks ?? []
  return weeks.length > 0 ? weeks[weeks.length - 1] : null
})

const targetTotal = computed(() =>
  (profile.value?.subjects ?? []).reduce(
    (total, subject) => total + (subject.target_score ?? 0),
    0,
  ),
)

const estimatedTotal = computed(() =>
  Math.round(
    (profile.value?.subjects ?? []).reduce(
      (total, subject) => total + (subject.estimated_score ?? 0),
      0,
    ),
  ),
)

function isoDate(day: Date): string {
  return day.toISOString().slice(0, 10)
}

function formatMinutes(minutes: number): string {
  const hours = minutes / 60
  return hours >= 1 ? `${hours.toFixed(1)}h` : `${minutes}min`
}

onMounted(async () => {
  try {
    await fetchServiceStatus()
    status.value = 'online'
  } catch {
    status.value = 'offline'
  }
  try {
    const today = new Date()
    const monday = new Date(today)
    monday.setDate(today.getDate() - ((today.getDay() + 6) % 7))
    const sunday = new Date(monday)
    sunday.setDate(monday.getDate() + 6)
    const [profileData, weeklyData] = await Promise.all([
      fetchStudyProfile(),
      fetchWeeklyStats({ start: isoDate(monday), end: isoDate(sunday) }),
    ])
    profile.value = profileData
    weekly.value = weeklyData
    const nextMonday = new Date(monday)
    nextMonday.setDate(monday.getDate() + 7)
    const [runsResult, adviceResult] = await Promise.allSettled([
      fetchAutomationRuns(8),
      fetchAiWeekAdvice(isoDate(nextMonday)),
    ])
    if (runsResult.status === 'fulfilled') {
      automationRuns.value = runsResult.value.runs ?? []
    }
    if (
      adviceResult.status === 'fulfilled' &&
      adviceResult.value.status === 'draft'
    ) {
      draftAdvice.value = adviceResult.value
    }
  } catch {
    error.value = '备考画像加载失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <section class="page dashboard">
    <header class="dash-hero">
      <div>
        <StatusBadge :state="status" />
        <h1>备考驾驶舱</h1>
        <p class="summary">
          周一到周六照着今日任务学，周日复盘定下周；这里随时看离目标还差多少。
        </p>
      </div>
      <div class="hero-actions">
        <RouterLink
          class="primary-link"
          to="/today"
        >
          进入今日任务
        </RouterLink>
        <RouterLink
          class="secondary-link"
          to="/stats"
        >
          查看周统计
        </RouterLink>
      </div>
    </header>

    <p
      v-if="loading"
      class="state-card"
    >
      正在加载备考画像…
    </p>
    <p
      v-else-if="error"
      class="state-card error"
    >
      {{ error }}
    </p>

    <template v-else-if="profile">
      <div
        class="metric-grid"
        data-testid="metric-grid"
      >
        <article class="metric-card">
          <span>考研倒计时</span>
          <strong>{{ profile.days_to_exam }} 天</strong>
          <small>{{ profile.exam_date }} 初试</small>
        </article>
        <article class="metric-card">
          <span>总体掌握度</span>
          <strong>{{ profile.overall_mastery }}%</strong>
          <small>考纲覆盖 {{ Math.round(profile.overall_coverage * 100) }}%</small>
        </article>
        <article class="metric-card">
          <span>本周执行率</span>
          <strong>
            {{ currentWeek ? Math.round(currentWeek.execution_rate * 100) : 0 }}%
          </strong>
          <small>
            已学 {{ formatMinutes(currentWeek?.completed_minutes ?? 0) }} /
            计划 {{ formatMinutes(currentWeek?.planned_minutes ?? 0) }}
          </small>
        </article>
        <article class="metric-card">
          <span>预估总分</span>
          <strong v-if="hasGoals">{{ estimatedTotal }} / {{ targetTotal }}</strong>
          <strong v-else>--</strong>
          <small v-if="hasGoals">按当前掌握度折算 / 目标分</small>
          <RouterLink
            v-else
            to="/planning#goals"
          >
            先去设置各科目标分
          </RouterLink>
        </article>
      </div>

      <div class="subject-grid">
        <article
          v-for="subject in profile.subjects"
          :key="subject.subject_id"
          class="subject-card"
          :data-testid="`subject-card-${subject.subject_name}`"
        >
          <header>
            <h2>{{ subject.subject_name }}</h2>
            <strong v-if="subject.target_score !== null">
              预估 {{ subject.estimated_score }} / 目标 {{ subject.target_score }}
            </strong>
            <strong v-else>未设目标</strong>
          </header>
          <div class="bar-row">
            <span>掌握度 {{ subject.mastery }}%</span>
            <div class="bar">
              <i :style="{ width: `${subject.mastery}%` }" />
            </div>
          </div>
          <div class="bar-row">
            <span>
              覆盖 {{ subject.studied_points }}/{{ subject.knowledge_point_total }}
            </span>
            <div class="bar">
              <i
                class="coverage"
                :style="{ width: `${Math.round(subject.coverage * 100)}%` }"
              />
            </div>
          </div>
          <p class="subject-meta">
            已学 {{ formatMinutes(subject.studied_minutes) }} · 错题 {{ subject.wrong_count }} 道
          </p>
          <div
            v-if="subject.weak_points.length > 0 && subject.studied_points > 0"
            class="weak-list"
          >
            <span>薄弱点</span>
            <ul>
              <li
                v-for="point in subject.weak_points"
                :key="point.knowledge_point_id"
              >
                {{ point.knowledge_point_name }}
                <em>{{ point.mastery }}%</em>
              </li>
            </ul>
          </div>
          <p
            v-else
            class="weak-empty"
          >
            暂无掌握度数据，先打卡积累。
          </p>
        </article>
      </div>

      <article
        v-if="draftAdvice"
        class="automation-card draft-card"
      >
        <header>
          <h2>待确认：下周 AI 计划草稿（{{ draftAdvice.week_start }} 起）</h2>
          <button
            type="button"
            class="confirm-btn"
            :disabled="confirming"
            @click="confirmDraft"
          >
            {{ confirming ? '确认中…' : '确认并落入计划' }}
          </button>
        </header>
        <p>{{ draftAdvice.summary }}</p>
      </article>

      <article
        v-if="automationRuns.length"
        class="automation-card"
      >
        <h2>自动化状态</h2>
        <ul class="run-list">
          <li
            v-for="run in automationRuns"
            :key="run.id"
          >
            <span
              class="run-status"
              :class="`run-${run.status}`"
            >{{ STATUS_LABELS[run.status] ?? run.status }}</span>
            <span class="run-name">{{ JOB_LABELS[run.job_name] ?? run.job_name }}</span>
            <span class="run-detail">{{ runSummary(run) }}</span>
            <time>{{ run.run_at.slice(0, 16).replace('T', ' ') }}</time>
          </li>
        </ul>
      </article>
    </template>
  </section>
</template>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.automation-card {
  background: var(--card, #fff);
  border: 1px solid var(--rule, #ececf0);
  border-radius: var(--radius-lg, 14px);
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.automation-card h2 {
  margin: 0;
  font-size: 1rem;
}

.draft-card {
  border-color: var(--brand, #3b5bfd);
  background: var(--brand-soft, #eef1ff);
}

.draft-card header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.draft-card p {
  margin: 0;
  color: var(--ink-soft, #4b4f58);
}

.confirm-btn {
  padding: 8px 16px;
  border: none;
  border-radius: var(--radius-sm, 8px);
  background: var(--brand, #3b5bfd);
  color: white;
  font-weight: 600;
  cursor: pointer;
}

.confirm-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.run-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.run-list li {
  display: flex;
  align-items: baseline;
  gap: 10px;
  font-size: 0.88rem;
}

.run-status {
  flex-shrink: 0;
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 0.75rem;
  background: var(--surface-soft, #f0f1f4);
  color: var(--ink-soft, #4b4f58);
}

.run-success {
  background: color-mix(in srgb, var(--ok, #0da678) 12%, white);
  color: var(--ok, #0da678);
}

.run-failed {
  background: color-mix(in srgb, var(--danger, #e5484d) 12%, white);
  color: var(--danger, #e5484d);
}

.run-name {
  flex-shrink: 0;
  font-weight: 600;
}

.run-detail {
  color: var(--ink-soft, #4b4f58);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.run-list time {
  margin-left: auto;
  flex-shrink: 0;
  color: var(--ink-muted, #9ca0a8);
  font-size: 0.78rem;
}

.dash-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
}

.dash-hero h1 {
  margin: 14px 0 0;
  font-size: clamp(24px, 2.5vw, 30px);
  letter-spacing: -0.03em;
}

.summary {
  max-width: 560px;
  margin: 12px 0 0;
  color: var(--ink-soft);
  font-size: 16px;
  line-height: 1.8;
}

.hero-actions {
  display: flex;
  gap: 12px;
}

.primary-link {
  display: inline-flex;
  padding: 10px 18px;
  border-radius: var(--radius-sm, 8px);
  color: white;
  background: var(--brand, var(--deep));
  font-weight: 600;
}

.secondary-link {
  display: inline-flex;
  padding: 10px 18px;
  border: 1px solid var(--rule);
  border-radius: var(--radius-sm, 8px);
  color: var(--ink-soft);
  background: white;
  font-weight: 500;
}

.state-card {
  padding: 28px;
  border: 1px solid var(--rule);
  border-radius: var(--radius-md);
  background: white;
  color: var(--ink-soft);
}

.state-card.error {
  color: var(--danger);
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.metric-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 22px;
  border: 1px solid var(--rule);
  border-radius: var(--radius-md);
  background: white;
}

.metric-card span {
  color: var(--ink-muted);
  font-size: 13px;
  font-weight: 600;
}

.metric-card strong {
  font-size: 30px;
  letter-spacing: -0.02em;
}

.metric-card small {
  color: var(--ink-muted);
}

.subject-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}

.subject-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 24px;
  border: 1px solid var(--rule);
  border-radius: var(--radius-md);
  background: white;
}

.subject-card header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.subject-card h2 {
  margin: 0;
  font-size: 20px;
}

.subject-card header strong {
  color: var(--deep);
  font-size: 14px;
}

.bar-row {
  display: grid;
  gap: 6px;
  color: var(--ink-soft);
  font-size: 13px;
}

.bar {
  height: 8px;
  border-radius: 999px;
  background: var(--paper-warm);
  overflow: hidden;
}

.bar i {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: var(--brand, var(--deep));
}

.bar i.coverage {
  background: var(--ok);
}

.subject-meta {
  margin: 0;
  color: var(--ink-muted);
  font-size: 13px;
}

.weak-empty {
  margin: 0;
  color: var(--ink-muted);
  font-size: 13px;
}

.weak-list span {
  color: var(--ink-muted);
  font-size: 13px;
  font-weight: 600;
}

.weak-list ul {
  margin: 8px 0 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.weak-list li {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: var(--ink-soft);
  font-size: 13px;
}

.weak-list em {
  font-style: normal;
  color: var(--danger);
  font-weight: 700;
}
</style>
