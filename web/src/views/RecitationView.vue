<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import {
  fetchRecitationToday,
  fetchRecitations,
  reciteItem,
  type RecitationGroup,
  type RecitationItem,
  type RecitationStats,
  type RecitationSubject,
} from '../services/recitation'

const SUBJECT_LABELS: Record<RecitationSubject, string> = {
  politics: '政治',
  english: '英语',
  math: '数学',
  cs408: '408',
}

const subject = ref<RecitationSubject>('politics')
const groups = ref<RecitationGroup[]>([])
const stats = ref<RecitationStats | null>(null)
const todayItem = ref<RecitationItem | null>(null)
const expanded = ref<Set<string>>(new Set())
const loading = ref(true)
const error = ref('')
const busy = ref(false)

const hasItems = computed(() => (stats.value?.total_count ?? 0) > 0)

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const [list, today] = await Promise.all([
      fetchRecitations(subject.value),
      fetchRecitationToday(subject.value),
    ])
    groups.value = list.groups
    stats.value = list.stats
    todayItem.value = today.item
  } catch {
    error.value = '背诵材料加载失败'
  } finally {
    loading.value = false
  }
}

async function recite(item: RecitationItem, undo = false): Promise<void> {
  busy.value = true
  error.value = ''
  try {
    await reciteItem(item.id, undo)
    await load()
  } catch {
    error.value = '打卡失败，请重试'
  } finally {
    busy.value = false
  }
}

function switchSubject(next: RecitationSubject): void {
  if (subject.value !== next) {
    subject.value = next
    void load()
  }
}

function toggleExpanded(id: string): void {
  const next = new Set(expanded.value)
  if (next.has(id)) {
    next.delete(id)
  } else {
    next.add(id)
  }
  expanded.value = next
}

onMounted(() => load())
</script>

<template>
  <section class="page recitation-page">
    <header class="recitation-hero">
      <div>
        <p class="eyebrow">
          每日一背 · 打卡
        </p>
        <h1>每日一背</h1>
        <p>每天推一条背诵材料，背完打卡；背得少的会优先再排上来。</p>
      </div>
      <div class="hero-side">
        <div class="subject-switch">
          <button
            v-for="(label, key) in SUBJECT_LABELS"
            :key="key"
            type="button"
            :class="{ active: subject === key }"
            @click="switchSubject(key as RecitationSubject)"
          >
            {{ label }}
          </button>
        </div>
        <div
          v-if="stats"
          class="recitation-stats"
        >
          <span>共 {{ stats.total_count }} 条</span>
          <span>今日已背 {{ stats.recited_today }}</span>
          <span>未背过 {{ stats.never_recited }}</span>
        </div>
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
      正在加载背诵材料…
    </p>

    <template v-else>
      <article
        v-if="todayItem"
        class="today-card"
        data-testid="today-card"
      >
        <p class="today-meta">
          <span class="pick-label">今日一背</span>
          <span>{{ todayItem.category }}</span>
          <span
            v-if="todayItem.recited_today"
            class="status-badge done"
          >已打卡</span>
          <span
            v-else
            class="status-badge"
          >待背诵</span>
          <span>已背 {{ todayItem.recite_count }} 次</span>
        </p>
        <h2>{{ todayItem.title }}</h2>
        <pre class="content">{{ todayItem.content_md }}</pre>
        <div class="card-actions">
          <button
            v-if="!todayItem.recited_today"
            type="button"
            :disabled="busy"
            @click="recite(todayItem)"
          >
            背完打卡
          </button>
          <button
            v-else
            type="button"
            class="ghost"
            :disabled="busy"
            @click="recite(todayItem, true)"
          >
            撤销打卡
          </button>
        </div>
      </article>

      <p
        v-else-if="!hasItems"
        class="empty-state"
      >
        背诵池是空的，重启后端会自动导入种子材料，或用导入接口添加。
      </p>

      <section
        v-for="group in groups"
        :key="group.category"
        class="recitation-group"
      >
        <h3>{{ group.category }}</h3>
        <ul class="recitation-list">
          <li
            v-for="item in group.items"
            :key="item.id"
            class="recitation-row"
          >
            <div class="row-head">
              <button
                type="button"
                class="title-toggle"
                @click="toggleExpanded(item.id)"
              >
                {{ item.title }}
              </button>
              <div class="row-actions">
                <span
                  v-if="item.recited_today"
                  class="status-badge done"
                >今日已背</span>
                <span class="count">{{ item.recite_count }} 次</span>
                <button
                  v-if="!item.recited_today"
                  type="button"
                  :disabled="busy"
                  @click="recite(item)"
                >
                  打卡
                </button>
                <button
                  v-else
                  type="button"
                  class="ghost"
                  :disabled="busy"
                  @click="recite(item, true)"
                >
                  撤销
                </button>
              </div>
            </div>
            <pre
              v-if="expanded.has(item.id)"
              class="content"
            >{{ item.content_md }}</pre>
          </li>
        </ul>
      </section>
    </template>
  </section>
</template>

<style scoped>
.recitation-page {
  display: grid;
  gap: 22px;
}

.recitation-hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 20px;
  flex-wrap: wrap;
}

.hero-side {
  display: grid;
  gap: 10px;
  justify-items: end;
}

.subject-switch {
  display: flex;
  gap: 6px;
}

.subject-switch button {
  padding: 6px 16px;
  border: 1px solid var(--rule);
  border-radius: 999px;
  background: white;
  font-weight: 600;
  cursor: pointer;
  color: var(--ink-soft);
}

.subject-switch button.active {
  background: var(--brand);
  color: white;
  border-color: var(--deep);
}

.recitation-stats {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.recitation-stats span {
  padding: 6px 12px;
  border: 1px solid var(--rule);
  border-radius: 999px;
  background: white;
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-soft);
}

.today-card {
  display: grid;
  gap: 16px;
  padding: 32px 28px;
  border: 1px solid var(--rule);
  border-radius: var(--radius-md);
  background: white;
}

.today-meta {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
  color: var(--ink-muted);
  font-size: 13px;
}

.pick-label {
  font-weight: 600;
  color: var(--deep);
}

.today-card h2 {
  margin: 0;
  font-size: 24px;
  line-height: 1.5;
}

.content {
  margin: 0;
  padding: 16px;
  border: 1px solid var(--rule);
  border-radius: var(--radius-md);
  background: var(--paper-warm);
  font-family: inherit;
  font-size: 15px;
  line-height: 1.9;
  white-space: pre-wrap;
  word-break: break-word;
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
  border-radius: var(--radius-md);
  background: var(--paper-warm);
  font-weight: 600;
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

.recitation-group {
  display: grid;
  gap: 12px;
}

.recitation-group h3 {
  margin: 0;
  font-size: 15px;
  color: var(--ink-soft);
}

.recitation-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
}

.recitation-row {
  display: grid;
  gap: 12px;
  padding: 12px 16px;
  border: 1px solid var(--rule);
  border-radius: var(--radius-md);
  background: white;
}

.row-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.title-toggle {
  border: none;
  background: none;
  padding: 0;
  font-size: 15px;
  font-weight: 650;
  color: var(--ink);
  cursor: pointer;
  text-align: left;
}

.count {
  font-size: 12px;
  color: var(--ink-muted);
}

.status-badge {
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid var(--rule);
  color: var(--ink-muted);
}

.status-badge.done {
  color: var(--ok);
}

.empty-state {
  padding: 48px;
  text-align: center;
  color: var(--ink-muted);
  border: 1px dashed var(--rule);
  border-radius: var(--radius-md);
}

.feedback.error {
  color: var(--danger);
}

.loading-state {
  color: var(--ink-muted);
}
</style>
