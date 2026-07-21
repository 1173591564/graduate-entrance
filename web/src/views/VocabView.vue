<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import {
  fetchVocabToday,
  gradeVocabWord,
  type VocabGrade,
  type VocabTodayResponse,
  type VocabWord,
} from '../services/vocab'

const GRADE_LABELS: Record<VocabGrade, string> = {
  forgot: '忘了',
  vague: '模糊',
  mastered: '掌握',
}

const GRADES: VocabGrade[] = ['forgot', 'vague', 'mastered']

const summary = ref<VocabTodayResponse | null>(null)
const queue = ref<VocabWord[]>([])
const revealed = ref(false)
const loading = ref(true)
const error = ref('')
const grading = ref(false)
const gradedCount = ref(0)

const current = computed(() => queue.value[0] ?? null)
const dueRemaining = computed(
  () => queue.value.filter((word) => word.due_date !== null).length,
)

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const response = await fetchVocabToday()
    summary.value = response
    queue.value = [...response.due_words, ...response.new_words]
    revealed.value = false
    gradedCount.value = 0
  } catch {
    error.value = '词汇加载失败'
  } finally {
    loading.value = false
  }
}

function playPronunciation(word: string): void {
  try {
    const audio = new Audio(
      `https://dict.youdao.com/dictvoice?audio=${encodeURIComponent(word)}&type=2`,
    )
    void Promise.resolve(audio.play()).catch(() => {})
  } catch {
    // 环境不支持音频播放时静默忽略
  }
}

function reveal(word: VocabWord): void {
  revealed.value = true
  playPronunciation(word.word)
}

async function handleGrade(word: VocabWord, grade: VocabGrade): Promise<void> {
  grading.value = true
  try {
    await gradeVocabWord(word.id, grade)
    queue.value = queue.value.filter((entry) => entry.id !== word.id)
    revealed.value = false
    gradedCount.value += 1
  } catch {
    error.value = '评级提交失败，请重试'
  } finally {
    grading.value = false
  }
}

onMounted(() => load())
</script>

<template>
  <section class="page vocab-page">
    <header class="vocab-hero">
      <div>
        <p class="eyebrow">
          英语一 · 考纲词汇
        </p>
        <h1>背单词</h1>
        <p>红宝书顺序过新词，SM-2 间隔调度复习，评级后自动安排下次出现。</p>
      </div>
      <div
        v-if="summary"
        class="vocab-stats"
      >
        <span>已学 {{ summary.learned_count }} / {{ summary.total_count }}</span>
        <span>今日到期 {{ summary.due_count }}</span>
        <span>本轮已背 {{ gradedCount }}</span>
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
      正在加载词汇…
    </p>

    <template v-else>
      <article
        v-if="current"
        class="word-card"
        data-testid="word-card"
      >
        <p class="word-meta">
          <span v-if="current.due_date">到期复习 · 第 {{ current.reps }} 轮</span>
          <span v-else>新词 · 红宝书 P{{ current.book_page }}</span>
          <span v-if="dueRemaining">队列中还有 {{ dueRemaining }} 个到期词</span>
        </p>
        <h2>{{ current.word }}</h2>
        <button
          v-if="!revealed"
          type="button"
          class="reveal-button"
          @click="reveal(current)"
        >
          显示释义
        </button>
        <p
          v-else
          class="meaning"
          data-testid="meaning"
        >
          {{ current.meaning }}
        </p>
        <div
          v-if="revealed"
          class="grade-buttons"
        >
          <button
            v-for="grade in GRADES"
            :key="grade"
            type="button"
            :class="['grade-button', grade]"
            :disabled="grading"
            @click="handleGrade(current, grade)"
          >
            {{ GRADE_LABELS[grade] }}
          </button>
        </div>
      </article>

      <p
        v-else
        class="empty-state"
      >
        今天的词背完了，明天见。
      </p>
    </template>
  </section>
</template>

<style scoped>
.vocab-page {
  display: grid;
  gap: 22px;
}

.vocab-hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 20px;
  flex-wrap: wrap;
}

.vocab-stats {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.vocab-stats span {
  padding: 6px 12px;
  border: 1px solid var(--rule);
  border-radius: 999px;
  background: white;
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-soft);
}

.word-card {
  display: grid;
  gap: 18px;
  justify-items: center;
  text-align: center;
  padding: 48px 28px;
  border: 1px solid var(--rule);
  border-radius: var(--radius-md);
  background: white;
}

.word-meta {
  margin: 0;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  color: var(--ink-muted);
  font-size: 13px;
}

.word-card h2 {
  margin: 0;
  font-size: 44px;
  letter-spacing: 0.02em;
}

.meaning {
  margin: 0;
  max-width: 560px;
  color: var(--ink-soft);
  font-size: 17px;
  line-height: 1.7;
}

.reveal-button {
  padding: 10px 26px;
  border: 1px solid var(--rule);
  border-radius: var(--radius-md);
  background: var(--paper-warm);
  font-weight: 600;
  cursor: pointer;
}

.grade-buttons {
  display: flex;
  gap: 12px;
}

.grade-button {
  padding: 10px 26px;
  border: 1px solid var(--rule);
  border-radius: var(--radius-md);
  background: white;
  font-weight: 600;
  cursor: pointer;
}

.grade-button.forgot {
  color: var(--danger);
}

.grade-button.vague {
  color: var(--warn);
}

.grade-button.mastered {
  color: var(--ok);
}

.grade-button:disabled {
  opacity: 0.6;
  cursor: wait;
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
