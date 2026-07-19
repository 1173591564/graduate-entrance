<script setup lang="ts">
import { computed } from 'vue'

const EXAM_DATE = new Date('2026-12-26T00:00:00')

const daysLeft = computed(() => {
  const diff = EXAM_DATE.getTime() - Date.now()
  return Math.max(0, Math.ceil(diff / 86_400_000))
})
</script>

<template>
  <div class="app-shell">
    <aside class="app-sidebar">
      <RouterLink
        class="brand"
        to="/"
      >
        <span class="brand-mark">
          习
        </span>
        <span>
          <strong>
            时习
          </strong>
          <small>
            学而时习之
          </small>
        </span>
      </RouterLink>

      <nav class="app-nav">
        <span class="app-nav-label">
          回顾
        </span>
        <RouterLink to="/">
          备考驾驶舱
        </RouterLink>
        <RouterLink to="/stats">
          周统计
        </RouterLink>
        <RouterLink to="/retro">
          周复盘
        </RouterLink>
        <RouterLink to="/insights">
          错因分析
        </RouterLink>
      </nav>

      <nav class="app-nav">
        <span class="app-nav-label">
          规划
        </span>
        <RouterLink to="/planning">
          规划配置
        </RouterLink>
        <RouterLink to="/syllabus">
          考纲
        </RouterLink>
      </nav>

      <nav class="app-nav">
        <span class="app-nav-label">
          素材
        </span>
        <RouterLink to="/problems">
          题库审核
        </RouterLink>
        <RouterLink to="/essay">
          作文素材
        </RouterLink>
      </nav>

      <nav class="app-nav">
        <span class="app-nav-label">
          执行
        </span>
        <RouterLink to="/today">
          今日任务
        </RouterLink>
        <RouterLink to="/reviews">
          复习
        </RouterLink>
        <RouterLink to="/vocab">
          背单词
        </RouterLink>
        <RouterLink to="/papers">
          英语阅读训练
        </RouterLink>
        <RouterLink to="/recitation">
          每日一背
        </RouterLink>
      </nav>

      <div class="app-sidebar-foot">
        <span class="environment-label">
          <small>
            距 11408 初试
          </small>
          <strong>
            {{ daysLeft }}
          </strong>
          <small>
            天
          </small>
        </span>
      </div>
    </aside>

    <main class="app-main">
      <RouterView />
    </main>
  </div>
</template>
