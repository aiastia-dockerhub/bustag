/**
 * 认证状态管理 —— 服务端密码登录（BUSTAG_PASSWORD）
 *
 * - 后端 BUSTAG_PASSWORD 未设置时 enabled=false，等同无登录（向后兼容）
 * - 会话为 HttpOnly cookie，前端只保存「是否已登录」的布尔态
 * - 任何 API 返回 401 → 清空登录态并跳转 /login
 */

export function useAuthState() {
  return useState<{ checked: boolean; enabled: boolean; authed: boolean }>('auth', () => ({
    checked: false,
    enabled: false,
    authed: false,
  }))
}

/** 查询后端认证状态（中间件/布局初始化时调用） */
export async function fetchAuthStatus(force = false) {
  const auth = useAuthState()
  if (auth.value.checked && !force) return auth.value
  try {
    const res = await $fetch<{ enabled: boolean; authed: boolean }>('/api/auth/status')
    auth.value = { checked: true, enabled: !!res.enabled, authed: !!res.authed }
  } catch {
    // 后端不可达时视为未登录（enabled 未知不跳转，避免误伤）
    auth.value = { checked: true, enabled: auth.value.enabled, authed: false }
  }
  return auth.value
}

/** 登录：成功后刷新状态 */
export async function login(password: string): Promise<{ ok: boolean; error?: string }> {
  try {
    await $fetch('/api/auth/login', { method: 'POST', body: { password } })
    const auth = useAuthState()
    auth.value = { checked: true, enabled: true, authed: true }
    return { ok: true }
  } catch (e: any) {
    return { ok: false, error: e.data?.error || e.message || '登录失败' }
  }
}

/** 登出 */
export async function logout() {
  try {
    await $fetch('/api/auth/logout', { method: 'POST' })
  } finally {
    const auth = useAuthState()
    auth.value = { checked: true, enabled: true, authed: false }
    await navigateTo('/login')
  }
}

/**
 * 统一处理 API 401：会话过期/未登录 → 清态并跳登录页
 * 各 composable 的 catch 块调用；返回 true 表示已按未登录处理
 */
export function handle401(e: any): boolean {
  const status = e?.status || e?.response?.status
  if (status !== 401) return false
  const auth = useAuthState()
  auth.value = { checked: true, enabled: true, authed: false }
  navigateTo('/login')
  return true
}
