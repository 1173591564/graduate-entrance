<script setup lang="ts">
import { onMounted, ref } from 'vue'

import StatusBadge from '../components/StatusBadge.vue'
import { fetchServiceStatus } from '../services/health'

const status = ref<'checking' | 'online' | 'offline'>('checking')

onMounted(async () => {
  try {
    await fetchServiceStatus()
    status.value = 'online'
  } catch {
    status.value = 'offline'
  }
})
</script>

<template>
  <section class="page hero">
    <div class="hero-copy">
      <StatusBadge :state="status" />
      <p class="eyebrow">
        数学一 · 408 · 英语一 · 政治
      </p>
      <h1>让每天的备考任务清晰、可执行、可复盘。</h1>
      <p class="summary">
        工程骨架已覆盖 Web、API、Android、数据库和部署入口，后续功能将按考纲和阶段计划逐步交付。
      </p>
      <div class="hero-actions">
        <RouterLink
          class="primary-link"
          to="/planning"
        >
          配置学习计划
        </RouterLink>
        <RouterLink
          class="secondary-link"
          to="/syllabus"
        >
          查看考纲树
        </RouterLink>
      </div>
    </div>
    <div
      class="module-grid"
      aria-label="规划中的核心模块"
    >
      <article>
        <span>01</span>
        <h2>任务规划</h2>
        <p>
          考纲、阶段、可用时段与确定性排程。
        </p>
      </article>
      <article>
        <span>02</span>
        <h2>题库复习</h2>
        <p>知识点映射、错题记录与 SM-2 复习。</p>
      </article>
      <article>
        <span>03</span>
        <h2>学习分析</h2>
        <p>进度、掌握度、周报与调整建议。</p>
      </article>
      <article>
        <span>04</span>
        <h2>多端同步</h2>
        <p>Web 管理、Android 日用与离线事件同步。</p>
      </article>
    </div>
  </section>
</template>

<style scoped>
.hero {
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(420px, 0.92fr);
  gap: 72px;
  align-items: center;
}

.eyebrow {
  margin: 26px 0 10px;
  color: #2764e7;
  font-size: 14px;
  font-weight: 750;
  letter-spacing: 0.08em;
}

h1 {
  max-width: 680px;
  margin: 0;
  font-size: clamp(40px, 5vw, 68px);
  line-height: 1.08;
  letter-spacing: -0.045em;
}

.summary {
  max-width: 620px;
  margin: 26px 0 0;
  color: #647087;
  font-size: 18px;
  line-height: 1.8;
}

.primary-link {
  display: inline-flex;
  padding: 12px 18px;
  border-radius: 999px;
  color: white;
  background: #2764e7;
  font-weight: 800;
}

.hero-actions {
  display: flex;
  gap: 12px;
  margin-top: 28px;
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

.module-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

article {
  min-height: 190px;
  padding: 24px;
  border: 1px solid #e1e7f0;
  border-radius: 20px;
  background: white;
  box-shadow: 0 18px 45px rgb(40 55 90 / 8%);
}

article span {
  color: #8b96aa;
  font-size: 13px;
  font-weight: 750;
}

article h2 {
  margin: 30px 0 8px;
  font-size: 20px;
}

article p {
  margin: 0;
  color: #738097;
  line-height: 1.7;
}

@media (max-width: 920px) {
  .hero {
    grid-template-columns: 1fr;
    gap: 48px;
  }
}

@media (max-width: 540px) {
  .module-grid {
    grid-template-columns: 1fr;
  }
}
</style>
