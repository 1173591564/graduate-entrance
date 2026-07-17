<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import {
  fetchPaperToday,
  fetchPapers,
  openPaperFile,
  setPaperStatus,
  type Paper,
  type PaperGroup,
  type PaperStats,
  type PaperStatus,
} from '../services/papers'

const STATUS_LABELS: Record<PaperStatus, string> = {
  unread: '未读',
  reading: '在读',
  done: '已读',
}

const groups = ref<PaperGroup[]>([])
const stats = ref<PaperStats | null>(null)
const todayPaper = ref<Paper | null>(null)
const loading = ref(true)
const error = ref('')
const busy = ref(false)

const hasPapers = computed(() => (stats.value?.total_count ?? 0) > 0)

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const [list, today] = await Promise.all([fetchPapers(), fetchPaperToday()])
    groups.value = list.groups
    stats.value = list.stats
    todayPaper.value = today.paper
  } catch {
    error.value = '论文列表加载失败'
  } finally {
    loading.value = false
  }
}

async function changeStatus(paper: Paper, status: PaperStatus): Promise<void> {
  busy.value = true
  error.value = ''
  try {
    await setPaperStatus(paper.id, status)
    await load()
  } catch {
    error.value = '状态更新失败，请重试'
  } finally {
    busy.value = false
  }
}

async function open(paper: Paper): Promise<void> {
  try {
    await openPaperFile(paper.id)
  } catch {
    error.value = '该论文 PDF 尚未上传，无法在线打开'
  }
}

onMounted(() => load())
</script>

<template>
  <section class="page papers-page">
    <header class="papers-hero">
      <div>
        <p class="eyebrow">
          英语一 · 阅读训练
        </p>
        <h1>论文阅读</h1>
        <p>把 LLM 论文当英语阅读素材，每天挑一篇读完打卡，练语感与长难句。</p>
      </div>
      <div
        v-if="stats"
        class="papers-stats"
      >
        <span>共 {{ stats.total_count }} 篇</span>
        <span>在读 {{ stats.reading_count }}</span>
        <span>已读 {{ stats.done_count }}</span>
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
      正在加载论文…
    </p>

    <template v-else>
      <article
        v-if="todayPaper"
        class="today-card"
        data-testid="today-card"
      >
        <p class="today-meta">
          <span class="pick-label">今日一篇</span>
          <span>{{ todayPaper.category }}</span>
          <span :class="['status-badge', todayPaper.status]">
            {{ STATUS_LABELS[todayPaper.status] }}
          </span>
        </p>
        <h2>{{ todayPaper.title }}</h2>
        <div class="card-actions">
          <button
            v-if="todayPaper.status !== 'reading'"
            type="button"
            :disabled="busy"
            @click="changeStatus(todayPaper, 'reading')"
          >
            开始阅读
          </button>
          <button
            v-if="todayPaper.status !== 'done'"
            type="button"
            :disabled="busy"
            @click="changeStatus(todayPaper, 'done')"
          >
            标记已读
          </button>
          <button
            v-if="todayPaper.has_file"
            type="button"
            class="ghost"
            @click="open(todayPaper)"
          >
            打开 PDF
          </button>
        </div>
      </article>

      <p
        v-else-if="!hasPapers"
        class="empty-state"
      >
        论文池还是空的，先同步桌面上的论文文件夹。
      </p>
      <p
        v-else
        class="empty-state"
      >
        全部读完了，明天见。
      </p>

      <section
        v-for="group in groups"
        :key="group.category"
        class="paper-group"
      >
        <h3>{{ group.category }}</h3>
        <ul class="paper-list">
          <li
            v-for="paper in group.papers"
            :key="paper.id"
            class="paper-row"
          >
            <div class="paper-title">
              <span :class="['status-dot', paper.status]" />
              <span>{{ paper.title }}</span>
            </div>
            <div class="row-actions">
              <span :class="['status-badge', paper.status]">
                {{ STATUS_LABELS[paper.status] }}
              </span>
              <button
                v-if="paper.status !== 'reading'"
                type="button"
                :disabled="busy"
                @click="changeStatus(paper, 'reading')"
              >
                在读
              </button>
              <button
                v-if="paper.status !== 'done'"
                type="button"
                :disabled="busy"
                @click="changeStatus(paper, 'done')"
              >
                已读
              </button>
              <button
                v-if="paper.status !== 'unread'"
                type="button"
                class="ghost"
                :disabled="busy"
                @click="changeStatus(paper, 'unread')"
              >
                重置
              </button>
              <button
                v-if="paper.has_file"
                type="button"
                class="ghost"
                @click="open(paper)"
              >
                PDF
              </button>
            </div>
          </li>
        </ul>
      </section>
    </template>
  </section>
</template>

<style scoped>
.papers-page {
  display: grid;
  gap: 22px;
}

.papers-hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 20px;
  flex-wrap: wrap;
}

.papers-stats {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.papers-stats span {
  padding: 6px 12px;
  border: 1px solid var(--rule);
  border-radius: 999px;
  background: white;
  font-size: 13px;
  font-weight: 750;
  color: var(--ink-soft);
}

.today-card {
  display: grid;
  gap: 16px;
  padding: 32px 28px;
  border: 1px solid var(--rule);
  border-radius: 3px;
  background: white;
}

.today-meta,
.paper-title {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
  color: var(--ink-muted);
  font-size: 13px;
}

.pick-label {
  font-weight: 750;
  color: var(--deep);
}

.today-card h2 {
  margin: 0;
  font-size: 24px;
  line-height: 1.5;
}

.card-actions,
.row-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}

.card-actions button,
.row-actions button {
  padding: 8px 18px;
  border: 1px solid var(--rule);
  border-radius: 3px;
  background: var(--paper-warm);
  font-weight: 750;
  cursor: pointer;
}

.card-actions button.ghost,
.row-actions button.ghost {
  background: white;
}

.card-actions button:disabled,
.row-actions button:disabled {
  opacity: 0.6;
  cursor: wait;
}

.paper-group {
  display: grid;
  gap: 12px;
}

.paper-group h3 {
  margin: 0;
  font-size: 15px;
  color: var(--ink-soft);
}

.paper-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
}

.paper-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  border: 1px solid var(--rule);
  border-radius: 3px;
  background: white;
  flex-wrap: wrap;
}

.paper-title {
  color: var(--ink);
  font-size: 15px;
  font-weight: 650;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: var(--rule);
}

.status-dot.reading {
  background: var(--warn);
}

.status-dot.done {
  background: var(--ok);
}

.status-badge {
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 750;
  border: 1px solid var(--rule);
  color: var(--ink-muted);
}

.status-badge.reading {
  color: var(--warn);
}

.status-badge.done {
  color: var(--ok);
}

.empty-state {
  padding: 48px;
  text-align: center;
  color: var(--ink-muted);
  border: 1px dashed var(--rule);
  border-radius: 3px;
}

.feedback.error {
  color: var(--danger);
}

.loading-state {
  color: var(--ink-muted);
}
</style>
