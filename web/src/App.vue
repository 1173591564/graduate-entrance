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
    <header class="app-header">
      <RouterLink
        class="brand"
        to="/"
      >
        <span class="brand-mark">GE</span>
        <span>
          <strong>11408 备考系统</strong>
          <small>Graduate Entrance</small>
        </span>
      </RouterLink>
      <nav class="app-nav">
        <RouterLink to="/today">
          今日任务
        </RouterLink>
        <RouterLink to="/stats">
          周统计
        </RouterLink>
        <RouterLink to="/problems">
          题库审核
        </RouterLink>
        <RouterLink to="/reviews">
          复习
        </RouterLink>
        <RouterLink to="/insights">
          错因分析
        </RouterLink>
        <RouterLink to="/essay">
          作文素材
        </RouterLink>
        <RouterLink to="/syllabus">
          考纲
        </RouterLink>
        <RouterLink to="/planning">
          规划配置
        </RouterLink>
      </nav>
      <span class="environment-label">考研倒计时 {{ daysLeft }} 天</span>
    </header>
    <main>
      <RouterView />
    </main>
  </div>
</template>
