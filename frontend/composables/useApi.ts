/**
 * API 调用封装 — 基于 Nuxt useFetch / $fetch
 */

const API_BASE = '/api'

// ---------- 通用辅助 ----------

/** 图片代理 URL */
export const imgProxyUrl = (url: string) =>
  `/img_proxy?url=${encodeURIComponent(url)}`

/** GET 请求（带缓存，SSR 友好） */
function apiGet<T>(path: string, params?: Record<string, any>) {
  return useFetch<T>(API_BASE + path, {
    params,
    // 服务端也发起请求
    server: true,
  })
}

/** POST 请求（不走 useFetch，用 $fetch） */
async function apiPost<T>(path: string, body?: any) {
  return await $fetch<T>(API_BASE + path, {
    method: 'POST',
    body,
  })
}

// ---------- 具体接口 ----------

/** 推荐列表 */
export const getIndex = (params?: Record<string, any>) =>
  apiGet('/index', params)

/** 推荐反馈 */
export const postCorrect = (fanhao: string, data: { is_correct: boolean }) =>
  apiPost(`/correct/${fanhao}`, data)

/** 打标列表 */
export const getTagit = (params?: Record<string, any>) =>
  apiGet('/tagit', params)

/** 打标操作 */
export const postTag = (fanhao: string, data: { rate_value: number }) =>
  apiPost(`/tag/${fanhao}`, data)

/** 本地文件 */
export const getLocal = (params?: Record<string, any>) =>
  apiGet('/local', params)

/** 上传番号 */
export const postLocalFanhao = (data: any) =>
  apiPost('/local_fanhao', data)

/** 模型信息 */
export const getModel = () =>
  apiGet('/model')

/** 训练模型（5 分钟超时） */
export const doTraining = () =>
  $fetch(API_BASE + '/do-training', { timeout: 300000 }) as Promise<any>

/** 上传数据库 */
export const postLoadDb = (formData: FormData) =>
  $fetch(API_BASE + '/load_db', {
    method: 'POST',
    body: formData,
  }) as Promise<any>

/** 搜索 */
export const getSearch = (params?: Record<string, any>) =>
  apiGet('/search', params)

/** 版本 */
export const getVersion = () =>
  apiGet('/version')