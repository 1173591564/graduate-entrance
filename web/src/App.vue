<script setup lang="ts">
import { computed } from 'vue'

const EXAM_DATE = new Date('2026-12-26T00:00:00')

const daysLeft = computed(() => {
  const diff = EXAM_DATE.getTime() - Date.now()
  return Math.max(0, Math.ceil(diff / 86_400_000))
})

const today = computed(() => {
  const d = new Date()
  const weekdays = ['日', '一', '二', '三', '四', '五', '六']
  return {
    date: `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}`,
    weekday: `星期${weekdays[d.getDay()]}`,
  }
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
          今日
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
          回顾
        </span>
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
          素材
        </span>
        <RouterLink to="/problems">
          题库审核
        </RouterLink>
        <RouterLink to="/essay">
          作文素材
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

    <aside
      class="app-aside"
      aria-label="边际注记"
    >
      <div class="margin-note">
        <div class="margin-note-title">
          今日 · Today
        </div>
        <div class="margin-note-body">
          <div
            class="tabular"
            style="font-size:1.1rem;color:var(--deep);"
          >
            {{ today.date }}
          </div>
          <div style="margin-top:2px;">
            {{ today.weekday }}
          </div>
        </div>
      </div>

      <div class="margin-note">
        <div class="margin-note-title">
          节律 · Cadence
        </div>
        <div class="margin-note-body">
          晨间 · 数学一<br>
          午后 · 408<br>
          日暮 · 英语一<br>
          夜读 · 政治
        </div>
      </div>

      <div class="margin-note">
        <div class="margin-note-title">
          笺 · Marginalia
        </div>
        <blockquote class="margin-note-quote">
          &ldquo;不积跬步,无以至千里。&rdquo;
          <cite>
            — 荀子 · 劝学
          </cite>
        </blockquote>
      </div>
    </aside>
  </div>
</template>
