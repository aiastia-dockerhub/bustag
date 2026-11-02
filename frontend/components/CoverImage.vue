<template>
  <img class="img-fluid coverimg" :src="imgProxyUrl(src, 480, referer)"
       :srcset="`${imgProxyUrl(src, 480, referer)} 480w, ${imgProxyUrl(src, 960, referer)} 960w`"
       sizes="(max-width: 575px) 100vw, (max-width: 767px) 50vw, 400px"
       width="600" height="400" alt="cover" decoding="async"
       :loading="priority ? 'eager' : 'lazy'" :fetchpriority="priority ? 'high' : undefined" />
</template>

<script setup lang="ts">
defineProps<{ src: string; referer?: string; priority?: boolean }>()
</script>

<style scoped>
img { width: 100%; height: auto; aspect-ratio: 3 / 2; object-fit: contain; background: #f5f5f5; }
</style>
