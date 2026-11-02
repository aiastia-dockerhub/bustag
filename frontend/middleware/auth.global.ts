/**
 * 全局路由守卫：BUSTAG_PASSWORD 启用且未登录时，跳转 /login
 *
 * useRequestFetch 在 SSR 期间转发 cookie，首屏渲染前完成认证
 * /login 页自身跳过
 */
export default defineNuxtRouteMiddleware(async (to) => {
  if (to.path === '/login') return

  const auth = await fetchAuthStatus()
  if (auth.enabled && !auth.authed) {
    return navigateTo({ path: '/login', query: { redirect: to.fullPath } })
  }
})
