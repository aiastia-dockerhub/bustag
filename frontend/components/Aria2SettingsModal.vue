<template>
  <!-- Aria2 设置弹框 — 纯 Vue 实现，不依赖 Bootstrap JS -->
  <ClientOnly>
    <div v-if="settingsVisible" class="aria2-modal-overlay" @click.self="closeSettings">
      <div class="aria2-modal">
        <div class="aria2-modal-header">
          <h5 class="mb-0">⚙️ Aria2 RPC 设置</h5>
          <button type="button" class="btn-close btn-close-white" @click="closeSettings"></button>
        </div>

        <div class="aria2-modal-body">
          <form @submit.prevent>
            <div class="mb-3">
              <label class="form-label fw-bold">RPC 地址</label>
              <input v-model="form.rpcUrl" type="text" class="form-control"
                     placeholder="https://your-domain.com （只需填根地址，/jsonrpc 会自动补全）"
                     autocomplete="off" />
              <div class="form-text">
                只需填 Aria2 服务的根地址，<code>/jsonrpc</code> 路径会自动补全。
                HTTPS 页面只能调 HTTPS 接口（否则会被浏览器拦截）。
              </div>
            </div>

            <div class="mb-3">
              <label class="form-label fw-bold">Secret Token <span class="text-muted fw-normal">(可选)</span></label>
              <div class="input-group">
                <input v-model="form.secret" :type="showSecret ? 'text' : 'password'" class="form-control"
                       placeholder="Aria2 启动的 --rpc-secret 值" autocomplete="new-password" />
                <button class="btn btn-outline-secondary" type="button" @click="showSecret = !showSecret"
                        :title="showSecret ? '隐藏' : '显示'">
                  {{ showSecret ? '🙈' : '👁️' }}
                </button>
              </div>
              <div class="form-text">Aria2 配置了 rpc-secret 时填写，留空表示无认证。</div>
            </div>

            <div class="mb-3">
              <label class="form-label fw-bold">下载目录 <span class="text-muted fw-normal">(可选)</span></label>
              <input v-model="form.dir" type="text" class="form-control"
                     placeholder="留空则用 Aria2 默认目录" autocomplete="off" />
              <div class="form-text">推送任务时指定的保存路径，如 <code>/downloads</code>。</div>
            </div>
          </form>

          <!-- 测试连接反馈 -->
          <div v-if="testResult" class="alert"
               :class="testResult.ok ? 'alert-success' : 'alert-danger'" role="alert">
            <span v-if="testResult.ok">✅</span><span v-else>❌</span>
            {{ testResult.message }}
          </div>
        </div>

        <div class="aria2-modal-footer">
          <button class="btn btn-outline-secondary btn-sm" @click="closeSettings">取消</button>
          <button class="btn btn-outline-info btn-sm" :disabled="testing" @click="onTest">
            <span v-if="testing">⏳ 测试中...</span>
            <span v-else>🔌 测试连接</span>
          </button>
          <button class="btn btn-primary btn-sm" @click="onSave">💾 保存</button>
        </div>
      </div>
    </div>
  </ClientOnly>
</template>

<script setup>
import { useAria2Config, useAria2Settings, saveAria2Config, testAria2Connection } from '~/composables/useAria2'

const { settingsVisible, closeSettings } = useAria2Settings()
const { rpcUrl, secret, dir } = useAria2Config()

// 表单本地副本，编辑时不直接改全局响应式状态，保存时才写入
const form = reactive({
  rpcUrl: rpcUrl.value,
  secret: secret.value,
  dir: dir.value,
})

// 密码显隐切换
const showSecret = ref(false)

// 打开弹框时同步最新配置
watch(settingsVisible, (v) => {
  if (v) {
    form.rpcUrl = rpcUrl.value
    form.secret = secret.value
    form.dir = dir.value
    testResult.value = null
  }
})

const testing = ref(false)
const testResult = ref(null)

const onTest = async () => {
  testing.value = true
  testResult.value = null
  try {
    testResult.value = await testAria2Connection(form.rpcUrl, form.secret)
  } finally {
    testing.value = false
  }
}

const onSave = () => {
  // saveAria2Config 返回规范化后的 RPC 地址（自动补 /jsonrpc）
  const normalized = saveAria2Config({
    rpcUrl: form.rpcUrl,
    secret: form.secret,
    dir: form.dir,
  })
  // 同步到全局响应式状态（当前页面立即生效）
  rpcUrl.value = normalized
  secret.value = form.secret.trim()
  dir.value = form.dir.trim()
  closeSettings()
}
</script>

<style scoped>
.aria2-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1080;
  padding: 1rem;
}

.aria2-modal {
  background: #fff;
  border-radius: 12px;
  width: 100%;
  max-width: 520px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.aria2-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  background: #212529;
  color: #fff;
  border-radius: 12px 12px 0 0;
}

.aria2-modal-body {
  padding: 1.25rem;
}

.aria2-modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 1rem 1.25rem;
  border-top: 1px solid #e9ecef;
}
</style>
