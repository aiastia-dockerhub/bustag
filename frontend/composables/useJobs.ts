export interface BackgroundJob {
  id: string
  kind: string
  state: 'queued' | 'running' | 'succeeded' | 'failed'
  progress: { stage?: string; processed?: number; recommended?: number }
  result: any
  error: string | null
}

/** One polling loop per page; navigation cancels the request and timer. */
export function useJobs() {
  const jobs = ref<BackgroundJob[]>([])
  const error = ref('')
  const active = computed(() => jobs.value.filter(job => ['queued', 'running'].includes(job.state)))
  let timer: ReturnType<typeof setTimeout> | undefined
  let stopped = false
  let controller: AbortController | undefined

  const refresh = async () => {
    controller?.abort()
    controller = new AbortController()
    try {
      const result = await $fetch<{ jobs: BackgroundJob[] }>('/api/jobs', { signal: controller.signal })
      jobs.value = result.jobs
      error.value = ''
    } catch (e: any) {
      if (e?.name !== 'AbortError') error.value = e.data?.error || '无法读取后台任务状态'
      handle401(e)
    }
  }
  const poll = async () => {
    await refresh()
    if (!stopped) timer = setTimeout(poll, active.value.length ? 1500 : 10000)
  }
  const submit = async (url: string, payload?: any) => {
    const result = await $fetch<{ job: BackgroundJob }>(url, { method: 'POST', body: payload })
    jobs.value = [result.job, ...jobs.value.filter(job => job.id !== result.job.id)]
    clearTimeout(timer)
    if (!stopped) timer = setTimeout(poll, 1000)
    return result.job
  }
  onMounted(poll)
  onBeforeUnmount(() => {
    stopped = true
    clearTimeout(timer)
    controller?.abort()
  })
  return { jobs, active, error, submit }
}
