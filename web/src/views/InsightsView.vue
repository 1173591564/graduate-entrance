<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import {
  fetchProblemInsights,
  type ProblemCause,
  type ProblemInsights,
} from '../services/problems'

const insights = ref<ProblemInsights | null>(null)
const loading = ref(true)
const error = ref('')

const CAUSE_LABELS: Record<ProblemCause, string> = {
  '': '未标注',
  concept: '概念不清',
  calculation: '计算失误',
  method: '方法不会',
  memory: '记忆遗忘',
  misread: '审题偏差',
  other: '其他',
}

const RADAR_SIZE = 320
const RADAR_CENTER = RADAR_SIZE / 2
const RADAR_RADIUS = 110

const radarPoints = computed(() => (insights.value?.knowledge_points ?? []).slice(0, 6))

const radarMax = computed(() =>
  Math.max(1, ...radarPoints.value.map((point) => point.weakness_score)),
)

function radarCoord(index: number, ratio: number): { x: number; y: number } {
  const angle = (Math.PI * 2 * index) / Math.max(3, radarPoints.value.length) - Math.PI / 2
  return {
    x: RADAR_CENTER + Math.cos(angle) * RADAR_RADIUS * ratio,
    y: RADAR_CENTER + Math.sin(angle) * RADAR_RADIUS * ratio,
  }
}

const radarPolygon = computed(() =>
  radarPoints.value
    .map((point, index) => {
      const { x, y } = radarCoord(index, point.weakness_score / radarMax.value)
      return `${x},${y}`
    })
    .join(' '),
)

const radarGrid = computed(() =>
  [0.33, 0.66, 1].map((ratio) =>
    radarPoints.value
      .map((_, index) => {
        const { x, y } = radarCoord(index, ratio)
        return `${x},${y}`
      })
      .join(' '),
  ),
)

const radarLabels = computed(() =>
  radarPoints.value.map((point, index) => {
    const { x, y } = radarCoord(index, 1.22)
    return { point, x, y }
  }),
)

const causeTotal = computed(() =>
  (insights.value?.causes ?? []).reduce((sum, cause) => sum + cause.count, 0),
)

const trendMax = computed(() =>
  Math.max(1, ...(insights.value?.weekly_trend ?? []).map((week) => week.reviews)),
)

const trendNewMax = computed(() =>
  Math.max(1, ...(insights.value?.weekly_trend ?? []).map((week) => week.new_problems)),
)

function weekLabel(weekStart: string): string {
  return weekStart.slice(5).replace('-', '/')
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    insights.value = await fetchProblemInsights()
  } catch {
    error.value = '错因统计加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(() => load())
</script>

<template>
  <section class="page insights-page">
    <header class="insights-hero">
      <div>
        <p class="eyebrow">
          错因分析
        </p>
        <h1>弱点雷达与复习趋势</h1>
        <p>基于题库与复习记录，定位薄弱知识点、主要错因与近八周趋势。</p>
      </div>
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
      正在加载错因统计…
    </p>

    <template v-else-if="insights">
      <div class="summary-grid">
        <article>
          <span>题目总数</span>
          <strong>{{ insights.total_problems }}</strong>
        </article>
        <article>
          <span>已定稿</span>
          <strong>{{ insights.confirmed_problems }}</strong>
        </article>
        <article>
          <span>涉及知识点</span>
          <strong>{{ insights.knowledge_points.length }}</strong>
        </article>
        <article>
          <span>统计日期</span>
          <strong>{{ insights.as_of }}</strong>
        </article>
      </div>

      <div class="panel-grid">
        <article class="panel radar-panel">
          <h2>弱点雷达（Top {{ radarPoints.length }}）</h2>
          <p
            v-if="radarPoints.length < 3"
            class="empty-state"
          >
            知识点数据不足（至少 3 个）时暂不绘制雷达图，先积累一些定稿题目吧。
          </p>
          <svg
            v-else
            class="radar-chart"
            :viewBox="`0 0 ${RADAR_SIZE} ${RADAR_SIZE}`"
            role="img"
            aria-label="弱点雷达图"
          >
            <polygon
              v-for="grid in radarGrid"
              :key="grid"
              :points="grid"
              class="radar-grid"
            />
            <polygon
              :points="radarPolygon"
              class="radar-area"
            />
            <text
              v-for="label in radarLabels"
              :key="label.point.knowledge_point_id"
              :x="label.x"
              :y="label.y"
              text-anchor="middle"
              class="radar-label"
            >
              {{ label.point.knowledge_point_name }}
            </text>
          </svg>
          <ul class="weakness-list">
            <li
              v-for="point in radarPoints"
              :key="point.knowledge_point_id"
            >
              <span class="name">{{ point.knowledge_point_name }}</span>
              <span class="meta">
                {{ point.problem_count }} 题 ·
                遗忘 {{ point.forgot_reviews }}/{{ point.total_reviews }} ·
                弱点分 {{ point.weakness_score.toFixed(1) }}
              </span>
            </li>
          </ul>
        </article>

        <article class="panel">
          <h2>错因分布</h2>
          <p
            v-if="!insights.causes.length"
            class="empty-state"
          >
            暂无已标注错因的定稿题目。
          </p>
          <ul
            v-else
            class="cause-list"
          >
            <li
              v-for="cause in insights.causes"
              :key="cause.cause"
            >
              <div class="cause-heading">
                <span>{{ CAUSE_LABELS[cause.cause] }}</span>
                <span>{{ cause.count }} 题</span>
              </div>
              <div class="bar-track">
                <div
                  class="bar-fill"
                  :style="{ width: `${(cause.count / causeTotal) * 100}%` }"
                />
              </div>
            </li>
          </ul>

          <h2 class="subject-title">
            科目分布
          </h2>
          <ul class="subject-list">
            <li
              v-for="subject in insights.subjects"
              :key="subject.subject_id ?? 'none'"
            >
              <span>{{ subject.subject_name }}</span>
              <span class="meta">{{ subject.problem_count }} 题（错题 {{ subject.wrong_count }}）</span>
            </li>
          </ul>
        </article>
      </div>

      <article class="panel">
        <h2>近八周趋势</h2>
        <div class="trend-grid">
          <div
            v-for="week in insights.weekly_trend"
            :key="week.week_start"
            class="trend-column"
          >
            <div class="trend-bars">
              <div
                class="trend-bar reviews"
                :style="{ height: `${(week.reviews / trendMax) * 100}%` }"
                :title="`复习 ${week.reviews} 次（忘了 ${week.forgot} / 模糊 ${week.vague} / 掌握 ${week.mastered}）`"
              />
              <div
                class="trend-bar new-problems"
                :style="{ height: `${(week.new_problems / trendNewMax) * 100}%` }"
                :title="`新增 ${week.new_problems} 题`"
              />
            </div>
            <span class="trend-label">{{ weekLabel(week.week_start) }}</span>
          </div>
        </div>
        <div class="trend-legend">
          <span><i class="dot reviews" /> 复习次数</span>
          <span><i class="dot new-problems" /> 新增题目</span>
        </div>
      </article>
    </template>
  </section>
</template>

<style scoped>
.insights-page {
  display: grid;
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

.insights-hero h1 {
  margin: 0;
  font-size: clamp(24px, 2.5vw, 30px);
}

.insights-hero p:last-child {
  margin: 12px 0 0;
  color: var(--ink-soft);
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
  border-radius: var(--radius-md);
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

.panel-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.panel {
  display: grid;
  gap: 14px;
  padding: 22px;
  border: 1px solid var(--rule);
  border-radius: var(--radius-md);
  background: white;
}

.panel h2 {
  margin: 0;
  font-size: 18px;
}

.radar-chart {
  justify-self: center;
  width: min(100%, 360px);
}

.radar-grid {
  fill: none;
  stroke: var(--rule);
}

.radar-area {
  fill: rgb(62 90 130 / 25%);
  stroke: var(--deep);
  stroke-width: 2;
}

.radar-label {
  fill: var(--ink-soft);
  font-size: 11px;
  font-weight: 700;
}

.weakness-list,
.cause-list,
.subject-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.weakness-list li,
.subject-list li {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 6px;
}

.weakness-list .name {
  font-weight: 600;
}

.meta {
  color: var(--ink-soft);
  font-size: 13px;
}

.cause-heading {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
  color: var(--ink-soft);
  font-size: 13px;
  font-weight: 600;
}

.bar-track {
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--rule-soft);
}

.bar-fill {
  height: 100%;
  border-radius: 999px;
  background: var(--warn);
}

.subject-title {
  margin-top: 8px;
}

.trend-grid {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 10px;
  height: 160px;
}

.trend-column {
  display: grid;
  grid-template-rows: 1fr auto;
  gap: 6px;
}

.trend-bars {
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 4px;
}

.trend-bar {
  width: 14px;
  border-radius: 3px 6px 0 0;
  min-height: 2px;
}

.trend-bar.reviews {
  background: var(--deep);
}

.trend-bar.new-problems {
  background: var(--ok);
}

.trend-label {
  color: var(--ink-soft);
  font-size: 12px;
  text-align: center;
}

.trend-legend {
  display: flex;
  gap: 16px;
  color: var(--ink-soft);
  font-size: 13px;
}

.dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 999px;
}

.dot.reviews {
  background: var(--deep);
}

.dot.new-problems {
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

.loading-state,
.empty-state {
  color: var(--ink-soft);
  background: white;
}

@media (max-width: 820px) {
  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .panel-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 520px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
