/**
 * 115 云下载推送功能 —— 全部经由 bustag 后端（token 服务端存储，前端永不接触）
 *
 * - 配置（AppID / 保存目录）存服务端 data/115_token.json，多设备共享
 * - 扫码授权一次，所有设备登录密码后即可推送
 * - 推送：POST /api/115/push/<fanhao>，后端自动取最大磁力并提交云下载
 *
 * 未授权/授权失效时自动弹出设置弹框引导扫码。
 */

/** 设置弹框显隐（全局状态，单实例，挂载在 layout 中） */
const settings115Visible = ref(false)

export function use115Settings() {
  const openSettings = () => { settings115Visible.value = true }
  const closeSettings = () => { settings115Visible.value = false }
  return { settings115Visible, openSettings, closeSettings }
}

/** 115 连接状态（弹框与状态展示用） */
export function use115Status() {
  const status = ref<any>(null)

  const refresh = async () => {
    try {
      status.value = await $fetch('/api/115/status')
    } catch (e: any) {
      handle401(e)
    }
    return status.value
  }

  return { status, refresh }
}

/** 115 推送功能（按钮状态机） */
export function use115Push() {
  const pushLoading = ref<Record<string, boolean | string>>({})

  /**
   * 推送番号对应的最大磁力到 115 云下载
   * 返回 true 表示成功（已弹提示）
   */
  const sendTo115 = async (fanhao: string): Promise<boolean> => {
    if (pushLoading.value[fanhao]) return false

    pushLoading.value[fanhao] = true
    try {
      const res = await $fetch<any>(`/api/115/push/${fanhao}`, { method: 'POST' })
        .catch(e => ({ error: e.data?.error || e.message, kind: e.data?.kind }))

      if (res.error) {
        // 授权类错误 → 弹出设置框引导扫码
        if (res.kind === 'not_authorized' || res.kind === 'need_reauth') {
          const { openSettings } = use115Settings()
          openSettings()
        }
        alert('推送到 115 失败: ' + res.error)
        return false
      }

      pushLoading.value[fanhao] = 'done'
      setTimeout(() => { pushLoading.value[fanhao] = false }, 2000)
      return true
    } finally {
      if (pushLoading.value[fanhao] !== 'done') {
        pushLoading.value[fanhao] = false
      }
    }
  }

  return { pushLoading, sendTo115 }
}
