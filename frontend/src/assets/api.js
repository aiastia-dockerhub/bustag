import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// 推荐列表
export const getIndex = (params) => api.get('/index', { params })
// 推荐反馈
export const postCorrect = (fanhao, data) => api.post(`/correct/${fanhao}`, data)
// 打标列表
export const getTagit = (params) => api.get('/tagit', { params })
// 打标操作
export const postTag = (fanhao, data) => api.post(`/tag/${fanhao}`, data)
// 本地文件
export const getLocal = (params) => api.get('/local', { params })
// 上传番号
export const postLocalFanhao = (data) => api.post('/local_fanhao', data)
// 模型信息
export const getModel = () => api.get('/model')
// 训练模型（5分钟超时，GridSearchCV 训练较慢）
export const doTraining = () => api.get('/do-training', { timeout: 300000 })
// 上传数据库
export const postLoadDb = (formData) => api.post('/load_db', formData, {
  headers: { 'Content-Type': 'multipart/form-data' },
})
// 搜索
export const getSearch = (params) => api.get('/search', { params })
// 版本
export const getVersion = () => api.get('/version')

// 图片代理 URL
export const imgProxyUrl = (url) => `/img_proxy?url=${encodeURIComponent(url)}`

export default api