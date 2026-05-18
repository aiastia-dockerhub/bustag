import { ref } from 'vue'

/**
 * 图片放大模态框 — 纯 Vue 实现，不依赖 Bootstrap JS
 */
const modalUrl = ref<string>('')

export const useImageModal = () => {
  const showImage = (url: string) => {
    modalUrl.value = url
  }
  const hideImage = () => {
    modalUrl.value = ''
  }
  return { modalUrl, showImage, hideImage }
}