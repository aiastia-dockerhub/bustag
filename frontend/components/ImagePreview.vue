<template>
  <dialog
    ref="preview"
    class="image-preview img-modal-overlay"
    aria-label="影片封面大图"
    @cancel.prevent="hideImage"
    @close="hideImage"
    @click.self="hideImage"
  >
    <button class="image-modal-close" aria-label="关闭大图" @click="hideImage">
      <AppIcon name="close" />
    </button>
    <img v-if="modalUrl" :src="modalUrl" alt="影片封面大图" />
  </dialog>
</template>
<script setup lang="ts">
const { modalUrl, hideImage } = useImageModal();
const preview = ref<HTMLDialogElement>();
watch(modalUrl, async (url) => {
  await nextTick();
  if (url && !preview.value?.open) preview.value?.showModal();
  if (!url && preview.value?.open) preview.value?.close();
});
onBeforeUnmount(hideImage);
</script>
<style scoped>
.image-preview {
  width: 100vw;
  height: 100vh;
  height: 100dvh;
  max-width: none;
  max-height: none;
  margin: 0;
  border: 0;
}
.image-preview:not([open]) {
  display: none;
}
.image-preview::backdrop {
  background: rgb(10 21 29 / 65%);
}
</style>
