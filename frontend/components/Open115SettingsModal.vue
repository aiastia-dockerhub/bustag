<template>
  <!-- 115 开放平台设置弹框 — 纯 Vue 实现，不依赖 Bootstrap JS -->
  <ClientOnly>
    <div v-if="settings115Visible" class="w115-modal-overlay" @click.self="onClose">
      <div class="w115-modal">
        <div class="w115-modal-header">
          <h5 class="mb-0">☁️ 115 云下载设置</h5>
          <button type="button" class="btn-close btn-close-white" @click="onClose"></button>
        </div>

        <div class="w115-modal-body">
          <!-- 连接状态卡 -->
          <div v-if="status" class="alert mb-3" :class="statusClass" role="alert">
            <template v-if="status.need_reauth">
              ⚠️ <strong>授权已失效</strong> —— refresh_token 已永久失效，请重新扫码授权
            </template>
            <template v-else-if="status.connected">
              ✅ <strong>已连接</strong>
              <div class="small mt-1" v-if="status.expires_at">
                access_token 到期: {{ formatTime(status.expires_at) }}
              </div>
              <div class="small" v-if="status.refresh_token_expires_at">
                需重新扫码授权的期限: {{ formatDate(status.refresh_token_expires_at) }}
              </div>
              <div class="small" v-if="quota">
                云下载配额: 剩余 {{ quota.surplus }} / 已用 {{ quota.used }} / 总量 {{ quota.count }}
              </div>
            </template>
            <template v-else-if="status.configured">
              ⏳ 已填写 AppID，<strong>尚未扫码授权</strong>
            </template>
            <template v-else>
              ⛔ 尚未配置 —— 填写 AppID 后扫码授权
            </template>
          </div>

          <!-- 应用配置表单 -->
          <form @submit.prevent>
            <div class="mb-3">
              <label class="form-label fw-bold">AppID</label>
              <input v-model="form.clientId" type="text" class="form-control"
                     placeholder="115 开放平台「应用管理」中的应用 ID" autocomplete="off" />
              <div class="form-text">
                在 <a href="https://open.115.com/" target="_blank">open.115.com</a> 创建应用后获取。
                扫码授权（PKCE）无需 AppSecret。配置保存在服务端，所有设备共享。
              </div>
            </div>

            <div class="mb-3">
              <label class="form-label fw-bold">保存目录 ID <span class="text-muted fw-normal">(可选)</span></label>
              <input v-model="form.wpPathId" type="text" class="form-control"
                     placeholder="留空或 0 = 保存到 115 根目录" autocomplete="off" />
              <div class="form-text">云下载任务的保存位置（115 网盘目录 ID）。</div>
            </div>
          </form>

          <!-- 扫码授权区 -->
          <div v-if="authPhase !== 'idle' && authPhase !== 'authorized'" class="qr-box mb-3">
            <div class="text-center">
              <img v-if="qrUid" :src="qrSrc" alt="115 扫码授权" class="qr-img" />
              <div class="small mt-2">
                <span v-if="authPhase === 'waiting'">请用 <strong>115 客户端 App</strong> 扫码</span>
                <span v-else-if="authPhase === 'scanned'" class="text-success">✅ 已扫码，请在手机上确认授权</span>
                <span v-else-if="authPhase === 'expired'" class="text-danger">❌ 二维码已过期</span>
              </div>
              <button v-if="authPhase === 'expired'" class="btn btn-outline-primary btn-sm mt-2"
                      @click="startAuth">🔄 刷新二维码</button>
            </div>
          </div>

          <div v-if="authPhase === 'authorized'" class="alert alert-success py-2 small mb-3">
            🎉 授权成功！所有设备登录密码后即可直接推送（无需重复扫码）
          </div>

          <!-- 操作反馈 -->
          <div v-if="actionMsg" class="alert py-2 small" :class="actionOk ? 'alert-success' : 'alert-danger'">
            {{ actionOk ? '✅' : '❌' }} {{ actionMsg }}
          </div>
        </div>

        <div class="w115-modal-footer">
          <button v-if="status && status.connected" class="btn btn-outline-danger btn-sm me-auto"
                  :disabled="busy" @click="onUnbind">
            🔓 解除授权
          </button>
          <button class="btn btn-outline-secondary btn-sm" @click="onClose">关闭</button>
          <button class="btn btn-outline-info btn-sm" :disabled="busy || !form.clientId.trim()"
                  @click="onSaveConfig">
            <span v-if="busy">⏳ ...</span>
            <span v-else>💾 保存配置</span>
          </button>
          <button class="btn btn-primary btn-sm" :disabled="busy || !form.clientId.trim() || polling"
                  @click="startAuth">
            <span v-if="polling">⏳ 等待扫码...</span>
            <span v-else>📱 扫码授权</span>
          </button>
        </div>
      </div>
    </div>
  </ClientOnly>
</template>

<script setup>
import { use115Settings, use115Status } from '~/composables/use115'

const { settings115Visible, closeSettings } = use115Settings()
const { status, refresh } = use115Status()

const form = reactive({ clientId: '', wpPathId: '' })
const busy = ref(false)
const actionMsg = ref('')
const actionOk = ref(false)
const quota = ref<any>(null)

// 扫码授权状态机: idle → waiting → scanned → authorized / expired
const authPhase = ref('idle')
const qrUid = ref('')
const polling = ref(false)
let pollAborted = false

const qrSrc = computed(() => qrUid.value ? `/api/115/auth/qr.svg?uid=${encodeURIComponent(qrUid.value)}` : '')

const statusClass = computed(() => {
  if (!status.value) return 'alert-secondary'
  if (status.value.need_reauth) return 'alert-warning'
  if (status.value.connected) return 'alert-success'
  return 'alert-light text-dark border'
})

const formatTime = (ts) => ts ? new Date(ts * 1000).toLocaleString('zh-CN') : ''
const formatDate = (ts) => ts ? new Date(ts * 1000).toLocaleDateString('zh-CN') : ''

// 打开弹框时加载最新状态
watch(settings115Visible, async (v) => {
  if (v) {
    actionMsg.value = ''
    authPhase.value = 'idle'
    qrUid.value = ''
    quota.value = null
    const s = await refresh()
    if (s) {
      form.clientId = s.client_id || ''
      form.wpPathId = s.wp_path_id === '0' ? '' : (s.wp_path_id || '')
    }
    // 已连接时顺带取配额
    if (s?.connected) {
      try { quota.value = await $fetch('/api/115/quota') } catch { /* 配额失败不影响设置 */ }
    }
  } else {
    stopPoll()
  }
})

const showMsg = (ok, msg) => {
  actionOk.value = ok
  actionMsg.value = msg
}

const onSaveConfig = async () => {
  busy.value = true
  try {
    const res = await $fetch<any>('/api/115/config', {
      method: 'POST',
      body: { client_id: form.clientId.trim(), wp_path_id: form.wpPathId.trim() || '0' },
    }).catch(e => ({ error: e.data?.error || e.message }))
    if (res.error) {
      showMsg(false, res.error)
      return
    }
    await refresh()
    showMsg(true, '配置已保存（服务端存储，多设备共享）')
  } finally {
    busy.value = false
  }
}

const startAuth = async () => {
  // 先保存当前表单里的 AppID，保证 start 用的是最新值
  busy.value = true
  try {
    await $fetch('/api/115/config', {
      method: 'POST',
      body: { client_id: form.clientId.trim(), wp_path_id: form.wpPathId.trim() || '0' },
    }).catch(() => {})
    const res = await $fetch<any>('/api/115/auth/start', { method: 'POST' })
      .catch(e => ({ error: e.data?.error || e.message }))
    if (res.error) {
      showMsg(false, res.error)
      return
    }
    qrUid.value = res.uid
    authPhase.value = 'waiting'
    await refresh()
    pollLoop(res.uid)
  } finally {
    busy.value = false
  }
}

const sleep = (ms) => new Promise(r => setTimeout(r, ms))

const stopPoll = () => { pollAborted = true }

const pollLoop = async (uid) => {
  pollAborted = false
  polling.value = true
  while (!pollAborted) {
    try {
      // 后端对 115 做长轮询（约 25s），前端每次调用带 40s 超时
      const res = await $fetch<any>('/api/115/auth/poll', {
        params: { uid }, timeout: 40000,
      })
      if (res.status === 'authorized') {
        authPhase.value = 'authorized'
        await refresh()
        try { quota.value = await $fetch('/api/115/quota') } catch { /* 忽略 */ }
        break
      }
      if (res.status === 'expired') {
        authPhase.value = 'expired'
        break
      }
      if (res.status === 'error') {
        authPhase.value = 'expired'
        showMsg(false, res.error || '授权轮询出错')
        break
      }
      if (res.status === 'scanned') authPhase.value = 'scanned'
      // waiting → 继续轮询
    } catch (e) {
      if (handle401(e)) break
      await sleep(1500) // 网络抖动，稍后重试
    }
  }
  polling.value = false
}

const onUnbind = async () => {
  if (!confirm('确定解除 115 授权吗？解除后需重新扫码。')) return
  busy.value = true
  try {
    await $fetch('/api/115/auth/logout', { method: 'POST' })
    quota.value = null
    authPhase.value = 'idle'
    await refresh()
    showMsg(true, '已解除授权')
  } finally {
    busy.value = false
  }
}

const onClose = () => {
  stopPoll()
  closeSettings()
}
</script>

<style scoped>
.w115-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1080;
  padding: 1rem;
}

.w115-modal {
  background: #fff;
  border-radius: 12px;
  width: 100%;
  max-width: 520px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.w115-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  background: #212529;
  color: #fff;
  border-radius: 12px 12px 0 0;
}

.w115-modal-body {
  padding: 1.25rem;
}

.w115-modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 1rem 1.25rem;
  border-top: 1px solid #e9ecef;
}

.qr-box {
  background: #f8f9fa;
  border: 1px dashed #ced4da;
  border-radius: 12px;
  padding: 1rem;
}

.qr-img {
  width: 200px;
  height: 200px;
  background: #fff;
  border-radius: 8px;
  padding: 6px;
}
</style>
