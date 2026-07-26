/**
 * Aria2 RPC 推送功能 —— 浏览器直连用户的 Aria2 服务
 *
 * 拓扑：bustag 后端在公网无法访问家庭内网 NAS，但用户浏览器在家中
 * 可以直连 Aria2。因此本模块完全在浏览器端发起 RPC 请求。
 *
 * 流程：调 /api/magnet/<fanhao> 拿最大磁力链接 → 直接 fetch 到 Aria2 jsonrpc。
 * 配置（rpc_url / secret / dir）存在 localStorage，每个浏览器各自维护。
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

/** Aria2 配置（响应式，自动从 localStorage 读/写） */
export function useAria2Config() {
  const rpcUrl = ref(localStorage.getItem(LS_RPC_URL) || '')
  const secret = ref(localStorage.getItem(LS_SECRET) || '')
  const dir = ref(localStorage.getItem(LS_DIR) || '')
  return { rpcUrl, secret, dir }
}

/** 保存配置到 localStorage */
export function saveAria2Config(cfg: { rpcUrl: string; secret: string; dir: string }) {
  localStorage.setItem(LS_RPC_URL, cfg.rpcUrl.trim())
  localStorage.setItem(LS_SECRET, cfg.secret.trim())
  localStorage.setItem(LS_DIR, cfg.dir.trim())
}

/** 测试与 Aria2 RPC 的连通性（aria2.getVersion） */
export async function testAria2Connection(rpcUrl: string, secret: string): Promise<{ ok: boolean; message: string }> {
  const url = (rpcUrl || '').trim()
  if (!url) return { ok: false, message: '请填写 RPC 地址' }
  try {
    const params = secret ? [['token:' + secret]] : []
    const res = await $fetch.raw<any>(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: {
        jsonrpc: '2.0',
        id: 'test',
        method: 'aria2.getVersion',
        params,
      },
      timeout: 10000,
    })
    const data = res._data || {}
    if (data.error) {
      return { ok: false, message: '认证失败或参数错误: ' + (data.error.message || JSON.stringify(data.error)) }
    }
    if (data.result && data.result.version) {
      return { ok: true, message: '连接成功！Aria2 版本: ' + data.result.version }
    }
    return { ok: false, message: '响应格式异常: ' + JSON.stringify(data) }
  } catch (e: any) {
    let detail = e.message || String(e)
    // CORS / 网络错误通常表现为 "Failed to fetch" 或 TypeError
    if (e.name === 'TypeError' || /fetch/i.test(detail)) {
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
      const rpcParams = secret.value ? [['token:' + secret.value]] : []
      // aria2.addUri 参数: [uris, options, position]
      const options: Record<string, string> = {}
      if (dir.value.trim()) options.dir = dir.value.trim()
      rpcParams[0].push([magnet])
      rpcParams[0].push(options)

      const res = await $fetch.raw<any>(rpcUrl.value.trim(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: {
          jsonrpc: '2.0',
          id: fanhao,
          method: 'aria2.addUri',
          params: rpcParams,
        },
        timeout: 15000,
      })

      const data = res._data || {}
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
      if (e.name === 'TypeError' || /fetch/i.test(detail)) {
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
