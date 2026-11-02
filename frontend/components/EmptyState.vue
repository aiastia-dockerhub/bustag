<template>
  <div class="empty-state" role="status">
    <span class="empty-state-icon"><AppIcon :name="icon || 'library'" /></span>
    <h2>{{ title }}</h2>
    <p>{{ description }}</p>
    <slot />
  </div>
</template>
<script setup lang="ts">
defineProps<{ title: string; description: string; icon?: string }>();
</script>
