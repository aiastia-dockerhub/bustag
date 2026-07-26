/**
 * Aria2 RPC 推送功能 —— 浏览器直连用户的 Aria2 服务
 *
 * 拓扑：bustag 后端在公网无法访问家庭内网 NAS，但用户浏览器在家中
 * 可以直连 Aria2。因此本模块完全在浏览器端发起 RPC 请求。
 *
 * 流程：调 /api/magnet/<fanhao> 拿最大磁力链接 → 直接 fetch 到 Aria2 jsonrpc。
 * 配置（rpc_url / secret / dir）存在 localStorage，每个浏览器各自维护。
 *
 * 用户只需填 Aria2 根地址（如 https://example.com），本模块自动补 /jsonrpc。
 */

const LS_RPC_URL = 'bustag_aria2_rpc_url'
const LS_SECRET = 'bustag_aria2_secret'
const LS_DIR = 'bustag_aria2_dir'

/** 设置弹框显隐（全局状态，单实例，挂载在 layout 中） */
const settingsVisible = ref(false)

/** 打开/关闭设置弹框 */
export function useAria2Settings() {
  const openSettings = () => { settingsVisible.value = true }
  const closeSettings = () => { settingsVisible.value = false }
  return { settingsVisible, openSettings, closeSettings }
}

/**
 * 规范化 RPC 地址：用户只需填根域名（如 https://example.com），
 * 自动补全 /jsonrpc；若已带 /jsonrpc 则不重复追加。
 */
export function normalizeRpcUrl(input: string): string {
  let url = (input || '').trim()
  if (!url) return ''
  // 去掉末尾斜杠
  url = url.replace(/\/+$/, '')
  // 未带路径或只有 /，补 /jsonrpc
  if (/jsonrpc$/i.test(url)) return url
  return url + '/jsonrpc'
}

/** Aria2 配置（响应式，自动从 localStorage 读/写） */
export function useAria2Config() {
  const rpcUrl = ref('')
  const secret = ref('')
  const dir = ref('')
  // 仅在浏览器端读取 localStorage（SSR 时不存在，否则会报 500）
  if (import.meta.client) {
    rpcUrl.value = localStorage.getItem(LS_RPC_URL) || ''
    secret.value = localStorage.getItem(LS_SECRET) || ''
    dir.value = localStorage.getItem(LS_DIR) || ''
  }
  return { rpcUrl, secret, dir }
}

/** 保存配置到 localStorage（RPC 地址存规范化后的值） */
export function saveAria2Config(cfg: { rpcUrl: string; secret: string; dir: string }) {
  const normalized = normalizeRpcUrl(cfg.rpcUrl)
  localStorage.setItem(LS_RPC_URL, normalized)
  localStorage.setItem(LS_SECRET, cfg.secret.trim())
  localStorage.setItem(LS_DIR, cfg.dir.trim())
  return normalized
}

/**
 * 底层 Aria2 JSON-RPC 调用
 * Aria2 params 格式（顶层是扁平数组）：
 *   带认证：["token:<secret>", <arg1>, <arg2>, ...]
 *   无认证：[<arg1>, <arg2>, ...]
 */
async function aria2Call(rpcUrl: string, method: string, args: any[] = [], secret = '', timeoutMs = 10000) {
  const params: any[] = []
  if (secret) params.push('token:' + secret)
  params.push(...args)

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const resp = await fetch(rpcUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        jsonrpc: '2.0',
        id: 'bustag',
        method,
        params,
      }),
      signal: controller.signal,
    })
    const data = await resp.json()
    return data
  } finally {
    clearTimeout(timer)
  }
}

/** 测试与 Aria2 RPC 的连通性（aria2.getVersion） */
export async function testAria2Connection(rpcUrl: string, secret: string): Promise<{ ok: boolean; message: string }> {
  const url = normalizeRpcUrl(rpcUrl)
  if (!url) return { ok: false, message: '请填写 RPC 地址' }
  try {
    const data = await aria2Call(url, 'aria2.getVersion', [], secret, 10000)
    if (data.error) {
      return { ok: false, message: '认证失败或参数错误: ' + (data.error.message || JSON.stringify(data.error)) }
    }
    if (data.result && data.result.version) {
      return { ok: true, message: '连接成功！Aria2 版本: ' + data.result.version }
    }
    return { ok: false, message: '响应格式异常: ' + JSON.stringify(data) }
  } catch (e: any) {
    let detail = e.message || String(e)
    if (e.name === 'AbortError') detail = '请求超时（Aria2 未在 10 秒内响应）'
    else if (e.name === 'TypeError' || /fetch/i.test(detail)) {
      detail = '网络请求失败（可能 CORS 未开启、地址不通、或 HTTPS/HTTP 混合内容被浏览器拦截）'
    }
    return { ok: false, message: detail }
  }
}

/** Aria2 推送功能（按钮状态机） */
export function useAria2() {
  const aria2Loading = ref<Record<string, boolean | string>>({})

  /**
   * 发送番号对应的磁力链接到 Aria2
   * 返回 true 表示成功，false 表示失败（已弹提示）
   */
  const sendToAria2 = async (fanhao: string): Promise<boolean> => {
    if (aria2Loading.value[fanhao]) return false

    const { rpcUrl, secret, dir } = useAria2Config()
    if (!rpcUrl.value.trim()) {
      const { openSettings } = useAria2Settings()
      openSettings()
      alert('请先配置 Aria2 RPC 地址')
      return false
    }

    aria2Loading.value[fanhao] = true
    try {
      // 1. 通过 bustag 后端获取最大磁力链接
      const magnetRes = await $fetch<any>(`/api/magnet/${fanhao}`)
      if (magnetRes.error) {
        alert('获取磁力失败: ' + magnetRes.error)
        return false
      }
      const magnet = magnetRes.magnet
      if (!magnet) {
        alert('暂无磁力链接')
        return false
      }

      // 2. 直接调用 Aria2 RPC 添加任务
      //    aria2.addUri(uris[, options[, position]])
      //    args 传给 aria2Call 后会自动在前面拼上 token（如有）
      const rpcUrlNorm = normalizeRpcUrl(rpcUrl.value)
      const options: Record<string, string> = {}
      if (dir.value.trim()) options.dir = dir.value.trim()

      const data = await aria2Call(
        rpcUrlNorm,
        'aria2.addUri',
        [[magnet], options],
        secret.value.trim(),
        15000,
      )

      if (data.error) {
        alert('Aria2 拒绝任务: ' + (data.error.message || JSON.stringify(data.error)))
        return false
      }

      // 成功：data.result 是 GID
      aria2Loading.value[fanhao] = 'done'
      setTimeout(() => {
        aria2Loading.value[fanhao] = false
      }, 2000)
      return true
    } catch (e: any) {
      let detail = e.message || String(e)
      if (e.name === 'AbortError') detail = '请求超时'
      else if (e.name === 'TypeError' || /fetch/i.test(detail)) {
        detail = '无法连接到 Aria2（请检查 RPC 地址是否正确、网络是否可达、或 CORS 是否开启）'
      }
      alert('发送到 Aria2 失败: ' + detail)
      return false
    } finally {
      if (aria2Loading.value[fanhao] !== 'done') {
        aria2Loading.value[fanhao] = false
      }
    }
  }

  return { aria2Loading, sendToAria2 }
}
