/** Same-origin API proxy, including the incoming authentication cookie during SSR. */
export default defineEventHandler(event => {
  const config = useRuntimeConfig(event)
  return proxyRequest(event, `${config.apiBase}${event.path}`)
})
