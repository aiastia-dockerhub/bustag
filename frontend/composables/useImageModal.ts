/**
 * 图片放大模态框 — 替代原来 App.vue 中的 provide/inject
 */
export const useImageModal = () => {
  const showImage = (url: string) => {
    // 只在客户端执行（依赖 Bootstrap JS Modal）
    if (import.meta.client) {
      const imgEl = document.getElementById('modalImage') as HTMLImageElement
      if (imgEl) imgEl.src = url
      const modalEl = document.getElementById('imageModal')
      if (modalEl) {
        // eslint-disable-next-line no-undef
        const modal = new (window as any).bootstrap.Modal(modalEl)
        modal.show()
      }
    }
  }
  return { showImage }
}