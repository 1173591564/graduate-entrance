<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import StatusBadge from '../components/StatusBadge.vue'
import { fetchWeeklyStats, type WeeklyStatsSummary } from '../services/daily'
import { fetchServiceStatus } from '../services/health'
import { fetchStudyProfile, type StudyProfile } from '../services/profile'

const status = ref<'checking' | 'online' | 'offline'>('checking')
const profile = ref<StudyProfile | null>(null)
const weekly = ref<WeeklyStatsSummary | null>(null)
const loading = ref(true)
const error = ref('')

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
            v-if="subject.weak_points.length > 0"
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
        </article>
      </div>
    </template>
  </section>
</template>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 28px;
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
  font-size: clamp(30px, 3.6vw, 44px);
  letter-spacing: -0.03em;
}

.summary {
  max-width: 560px;
  margin: 12px 0 0;
  color: #647087;
  font-size: 16px;
  line-height: 1.8;
}

.hero-actions {
  display: flex;
  gap: 12px;
}

.primary-link {
  display: inline-flex;
  padding: 12px 18px;
  border-radius: 999px;
  color: white;
  background: #2764e7;
  font-weight: 800;
}

.secondary-link {
  display: inline-flex;
  padding: 12px 18px;
  border: 1px solid #dbe3ef;
  border-radius: 999px;
  color: #465269;
  background: white;
  font-weight: 800;
}

.state-card {
  padding: 28px;
  border: 1px solid #e1e7f0;
  border-radius: 18px;
  background: white;
  color: #647087;
}

.state-card.error {
  color: #b3261e;
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
  border: 1px solid #e1e7f0;
  border-radius: 18px;
  background: white;
}

.metric-card span {
  color: #8b96aa;
  font-size: 13px;
  font-weight: 750;
}

.metric-card strong {
  font-size: 30px;
  letter-spacing: -0.02em;
}

.metric-card small {
  color: #738097;
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
  border: 1px solid #e1e7f0;
  border-radius: 20px;
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
  color: #2764e7;
  font-size: 14px;
}

.bar-row {
  display: grid;
  gap: 6px;
  color: #647087;
  font-size: 13px;
}

.bar {
  height: 8px;
  border-radius: 999px;
  background: #edf1f8;
  overflow: hidden;
}

.bar i {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #2764e7, #6d47d9);
}

.bar i.coverage {
  background: #34a370;
}

.subject-meta {
  margin: 0;
  color: #738097;
  font-size: 13px;
}

.weak-list span {
  color: #8b96aa;
  font-size: 13px;
  font-weight: 750;
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
  color: #526077;
  font-size: 13px;
}

.weak-list em {
  font-style: normal;
  color: #b3261e;
  font-weight: 700;
}
</style>
