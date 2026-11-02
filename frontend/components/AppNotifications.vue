<template>
  <div class="app-notifications" aria-live="polite" aria-relevant="additions">
    <div v-for="notice in notices" :key="notice.id" class="download-notice"
         :class="notice.kind === 'success' ? 'notice-success' : 'notice-error'">
      <span aria-hidden="true">{{ notice.kind === 'success' ? '✅' : '⚠️' }}</span>
      <span class="notice-message">{{ notice.message }}</span>
      <button type="button" class="btn-close" aria-label="关闭提醒" @click="dismiss(notice.id)"></button>
    </div>
  </div>
</template>

<script setup lang="ts">
const { notices, dismiss } = useNotifications()
</script>

<style scoped>
.app-notifications {
  position: fixed;
  right: max(1rem, env(safe-area-inset-right));
  bottom: max(1rem, env(safe-area-inset-bottom));
  z-index: 1100;
  display: grid;
  gap: 0.75rem;
  width: min(380px, calc(100vw - 2rem));
  pointer-events: none;
}
.download-notice {
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
  padding: 1rem;
  border: 1px solid;
  border-radius: 12px;
  box-shadow: 0 6px 24px rgb(0 0 0 / 14%);
  pointer-events: auto;
}
.notice-success { color: #0f5132; background: #e8f5ee; border-color: #a3cfbb; }
.notice-error { color: #842029; background: #fff0f1; border-color: #f1aeb5; }
.notice-message { flex: 1; min-width: 0; overflow-wrap: anywhere; line-height: 1.5; }
.btn-close { flex: 0 0 auto; padding: 0.5rem; margin: -0.2rem; }
</style>
