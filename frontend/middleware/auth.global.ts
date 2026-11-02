/**
 * 全局路由守卫：BUSTAG_PASSWORD 启用且未登录时，跳转 /login
 *
 * 仅在浏览器端检查（SSR 期间 cookie 传递不可靠，客户端 hydration 后拦截即可）
 * /login 页自身跳过
 */
export default defineNuxtRouteMiddleware(async (to) => {
  if (import.meta.server) return
  if (to.path === '/login') return

  const auth = await fetchAuthStatus()
  if (auth.enabled && !auth.authed) {
    return navigateTo({ path: '/login', query: { redirect: to.fullPath } })
  }
})
