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
      <span class="environment-label">工程骨架</span>
    </header>
    <main>
      <RouterView />
    </main>
  </div>
</template>
