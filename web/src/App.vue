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
        <RouterLink to="/syllabus">
          考纲
        </RouterLink>
        <RouterLink to="/planning">
          规划配置
        </RouterLink>
      </nav>
      <span class="environment-label">P0-D</span>
    </header>
    <main>
      <RouterView />
    </main>
  </div>
</template>
