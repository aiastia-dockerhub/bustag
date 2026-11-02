type NoticeKind = 'success' | 'error'
interface Notice { id: string; kind: NoticeKind; message: string }

/** Shared by download actions and the layout; survives client-side navigation. */
export function useNotifications() {
  const notices = useState<Notice[]>('download-notices', () => [])
  const dismiss = (id: string) => {
    notices.value = notices.value.filter(notice => notice.id !== id)
  }
  const notify = (kind: NoticeKind, message: string) => {
    const id = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`
    notices.value = [...notices.value.slice(-3), { id, kind, message }]
    setTimeout(() => dismiss(id), kind === 'success' ? 8000 : 12000)
  }
  return { notices, dismiss, notify }
}
