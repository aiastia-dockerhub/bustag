/**
 * 磁力链接复制功能
 */
export function useMagnet() {
  const magnetLoading = ref<Record<string, boolean>>({})

  const copyMagnet = async (fanhao: string) => {
    if (magnetLoading.value[fanhao]) return

    magnetLoading.value[fanhao] = true
    try {
      const res = await $fetch<any>(`/api/magnet/${fanhao}`)
      if (res.error) {
        alert(res.error)
        return
      }
      const magnet = res.magnet
      if (!magnet) {
        alert('暂无磁力链接')
        return
      }
      await navigator.clipboard.writeText(magnet)
      // 显示成功状态 2 秒
      magnetLoading.value[fanhao] = 'done' as any
      setTimeout(() => {
        magnetLoading.value[fanhao] = false
      }, 2000)
    } catch (e: any) {
      alert('获取磁力失败: ' + (e.data?.error || e.message))
    } finally {
      if (magnetLoading.value[fanhao] !== 'done') {
        magnetLoading.value[fanhao] = false
      }
    }
  }

  return { magnetLoading, copyMagnet }
}