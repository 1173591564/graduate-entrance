<script setup lang="ts">
defineProps<{
  state: 'checking' | 'online' | 'offline'
}>()
</script>

<template>
  <span
    class="status-badge"
    :class="`status-${state}`"
  >
    <span
      class="status-dot"
      aria-hidden="true"
    />
    {{
      {
        checking: '正在检查',
        online: '后端已连接',
        offline: '后端未连接',
      }[state]
    }}
  </span>
</template>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 650;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: currentcolor;
}

.status-checking {
  color: #536076;
  background: #edf1f7;
}

.status-online {
  color: #087f5b;
  background: #dcfce7;
}

.status-offline {
  color: #b42318;
  background: #fee4e2;
}
</style>
