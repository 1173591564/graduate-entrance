<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'

import {
  confirmNextWeekPlan,
  fetchRetroSession,
  type RetroConfirmResult,
  type RetroContext,
  type RetroMessage,
  sendRetroMessage,
} from '../services/retro'

const context = ref<RetroContext | null>(null)
const messages = ref<RetroMessage[]>([])
const loading = ref(true)
const error = ref('')
const draft = ref('')
const sending = ref(false)
const confirming = ref(false)
const confirmed = ref<RetroConfirmResult | null>(null)
const messageList = ref<HTMLElement | null>(null)

function formatMinutes(minutes: number): string {
  const hours = minutes / 60
  return hours >= 1 ? `${hours.toFixed(1)}h` : `${minutes}min`
}

async function scrollToBottom(): Promise<void> {
  await nextTick()
  messageList.value?.scrollTo({ top: messageList.value.scrollHeight })
}

async function submitMessage(): Promise<void> {
  const content = draft.value.trim()
  if (!content || sending.value) {
    return
  }
  sending.value = true
  error.value = ''
  try {
    const response = await sendRetroMessage(content)
    messages.value = response.messages
    draft.value = ''
    await scrollToBottom()
  } catch {
    error.value = '发送失败，请重试'
  } finally {
    sending.value = false
  }
}

async function confirmPlan(): Promise<void> {
  if (confirming.value) {
    return
  }
  confirming.value = true
  error.value = ''
  try {
    confirmed.value = await confirmNextWeekPlan()
  } catch {
    error.value = '下周计划生成失败，请重试'
  } finally {
    confirming.value = false
  }
}

onMounted(async () => {
  try {
    const session = await fetchRetroSession()
    context.value = session.context
    messages.value = session.messages
    await scrollToBottom()
  } catch {
    error.value = '复盘数据加载失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <section class="page retro-page">
    <header class="retro-hero">
      <div>
        <p class="eyebrow">
          周日复盘
        </p>
        <h1>和教练聊聊这一周</h1>
        <p class="summary">
          先看数据，再聊取舍，聊完一键生成下周计划。
        </p>
      </div>
      <button
        class="confirm-button"
        type="button"
        :disabled="confirming"
        data-testid="confirm-plan"
        @click="confirmPlan"
      >
        {{ confirming ? '生成中…' : '生成下周计划' }}
      </button>
    </header>

    <p
      v-if="loading"
      class="state-card"
    >
      正在加载本周数据…
    </p>

    <template v-else-if="context">
      <div
        class="context-card"
        data-testid="retro-context"
      >
        <div class="context-metrics">
          <div>
            <span>本周执行率</span>
            <strong>{{ Math.round(context.execution_rate * 100) }}%</strong>
            <small>{{ context.completed_tasks }}/{{ context.total_tasks }} 个任务</small>
          </div>
          <div>
            <span>学习时长</span>
            <strong>{{ formatMinutes(context.completed_minutes) }}</strong>
            <small>计划 {{ formatMinutes(context.planned_minutes) }}</small>
          </div>
          <div>
            <span>考研倒计时</span>
            <strong>{{ context.days_to_exam }} 天</strong>
            <small>{{ context.week_start }} ~ {{ context.week_end }}</small>
          </div>
        </div>
        <div
          v-if="context.weak_points.length > 0"
          class="weak-points"
        >
          <span>本周薄弱点</span>
          <ul>
            <li
              v-for="point in context.weak_points"
              :key="point"
            >
              {{ point }}
            </li>
          </ul>
        </div>
        <div
          v-if="context.gap_suggestions.length > 0"
          class="gap-suggestions"
          data-testid="gap-suggestions"
        >
          <span>掌握缺口 Top{{ context.gap_suggestions.length }} · 下周建议</span>
          <ul>
            <li
              v-for="item in context.gap_suggestions"
              :key="item.knowledge_point_id"
            >
              <span class="gap-subject">{{ item.subject_name }}</span>
              <span class="gap-text">{{ item.suggestion }}</span>
              <span class="gap-score">缺口 {{ item.gap }}</span>
            </li>
          </ul>
        </div>
      </div>

      <div
        ref="messageList"
        class="message-list"
        data-testid="message-list"
      >
        <p
          v-if="messages.length === 0"
          class="empty-hint"
        >
          说说这周的感受吧，比如哪科吃力、下周时间有什么变化。
        </p>
        <div
          v-for="message in messages"
          :key="message.id"
          class="message"
          :class="message.role"
        >
          <p>{{ message.content }}</p>
        </div>
        <div
          v-if="sending"
          class="message assistant pending"
        >
          <p>教练思考中…</p>
        </div>
      </div>

      <p
        v-if="error"
        class="feedback error"
      >
        {{ error }}
      </p>

      <form
        class="composer"
        @submit.prevent="submitMessage"
      >
        <textarea
          v-model="draft"
          rows="2"
          placeholder="这周学得怎么样？"
          data-testid="retro-input"
          @keydown.enter.exact.prevent="submitMessage"
        />
        <button
          type="submit"
          :disabled="sending || !draft.trim()"
          data-testid="retro-send"
        >
          发送
        </button>
      </form>

      <div
        v-if="confirmed"
        class="plan-card"
        data-testid="confirmed-plan"
      >
        <h2>下周计划已生成</h2>
        <p>{{ confirmed.plan.advice.summary }}</p>
        <ul>
          <li
            v-for="entry in confirmed.plan.advice.daily_focus"
            :key="entry.date"
          >
            <strong>{{ entry.date }}</strong>
            {{ entry.focus }}
          </li>
        </ul>
        <RouterLink to="/today">
          去看今日任务
        </RouterLink>
      </div>
    </template>

    <p
      v-else
      class="state-card error"
    >
      {{ error }}
    </p>
  </section>
</template>

<style scoped>
.retro-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 860px;
}

.retro-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  flex-wrap: wrap;
}

.eyebrow {
  margin: 0 0 8px;
  color: var(--deep);
  font-size: 14px;
  font-weight: 750;
  letter-spacing: 0.08em;
}

.retro-hero h1 {
  margin: 0;
  font-size: clamp(28px, 3.2vw, 40px);
  letter-spacing: -0.03em;
}

.summary {
  margin: 10px 0 0;
  color: var(--ink-soft);
}

.confirm-button {
  padding: 12px 20px;
  border: none;
  border-radius: 999px;
  color: white;
  background: linear-gradient(90deg, var(--deep), var(--accent-cs));
  font-weight: 800;
  cursor: pointer;
}

.state-card {
  padding: 28px;
  border: 1px solid var(--rule);
  border-radius: 3px;
  background: white;
  color: var(--ink-soft);
}

.state-card.error,
.feedback.error {
  color: var(--danger);
}

.context-card {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 22px;
  border: 1px solid var(--rule);
  border-radius: 3px;
  background: white;
}

.context-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 16px;
}

.context-metrics span {
  display: block;
  color: var(--ink-muted);
  font-size: 13px;
  font-weight: 750;
}

.context-metrics strong {
  display: block;
  margin-top: 4px;
  font-size: 24px;
}

.context-metrics small {
  color: var(--ink-muted);
}

.weak-points span {
  color: var(--ink-muted);
  font-size: 13px;
  font-weight: 750;
}

.weak-points ul {
  margin: 8px 0 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.weak-points li {
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--paper-warm);
  color: var(--danger);
  font-size: 13px;
}

.gap-suggestions {
  margin-top: 14px;
}

.gap-suggestions > span {
  color: var(--ink-muted);
  font-size: 13px;
  font-weight: 750;
}

.gap-suggestions ul {
  margin: 8px 0 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 8px;
}

.gap-suggestions li {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 8px 12px;
  border: 1px solid var(--rule);
  border-left: 3px solid var(--deep);
  border-radius: 3px;
  background: var(--paper-warm);
  font-size: 13px;
}

.gap-subject {
  flex-shrink: 0;
  font-weight: 800;
  color: var(--deep);
}

.gap-text {
  flex: 1;
}

.gap-score {
  flex-shrink: 0;
  color: var(--danger);
  font-weight: 750;
}

.message-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 220px;
  max-height: 440px;
  overflow-y: auto;
  padding: 20px;
  border: 1px solid var(--rule);
  border-radius: 3px;
  background: white;
}

.empty-hint {
  margin: auto;
  color: var(--ink-muted);
}

.message {
  max-width: 78%;
}

.message p {
  margin: 0;
  padding: 12px 16px;
  border-radius: 3px;
  line-height: 1.7;
  white-space: pre-wrap;
}

.message.user {
  align-self: flex-end;
}

.message.user p {
  background: var(--deep);
  color: white;
  border-bottom-right-radius: 4px;
}

.message.assistant p {
  background: var(--paper-warm);
  color: var(--ink);
  border-bottom-left-radius: 4px;
}

.message.pending p {
  color: var(--ink-muted);
}

.composer {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.composer textarea {
  flex: 1;
  padding: 12px 14px;
  border: 1px solid var(--rule);
  border-radius: 3px;
  font: inherit;
  resize: vertical;
}

.composer button {
  padding: 12px 22px;
  border: none;
  border-radius: 999px;
  color: white;
  background: var(--deep);
  font-weight: 800;
  cursor: pointer;
}

.composer button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.plan-card {
  padding: 22px;
  border: 1px solid var(--rule);
  border-radius: 3px;
  background: var(--paper-warm);
}

.plan-card h2 {
  margin: 0 0 8px;
  font-size: 18px;
}

.plan-card ul {
  margin: 12px 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: var(--ink-soft);
  font-size: 14px;
}

.plan-card a {
  font-weight: 700;
  color: var(--deep);
}
</style>
