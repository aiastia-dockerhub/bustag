<template>
  <div class="login-page d-flex align-items-center justify-content-center">
    <div class="login-card">
      <div class="text-center mb-4">
        <img src="/logo.png" alt="Bustag" height="56" class="mb-3" />
        <h5 class="fw-bold mb-0">Bustag 管理登录</h5>
        <p class="text-muted small mt-1">密码由服务端环境变量 BUSTAG_PASSWORD 设置</p>
      </div>

      <form @submit.prevent="onLogin">
        <div class="mb-3">
          <label class="form-label fw-bold">密码</label>
          <div class="input-group">
            <input v-model="password" :type="showPwd ? 'text' : 'password'"
                   class="form-control" placeholder="请输入访问密码"
                   autocomplete="current-password" autofocus />
            <button class="btn btn-outline-secondary" type="button"
                    @click="showPwd = !showPwd">{{ showPwd ? '🙈' : '👁️' }}</button>
          </div>
        </div>

        <div v-if="errorMsg" class="alert alert-danger py-2 small" role="alert">❌ {{ errorMsg }}</div>

        <button type="submit" class="btn btn-primary w-100" :disabled="loading">
          <span v-if="loading">⏳ 登录中...</span>
          <span v-else>🔐 登录</span>
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
definePageMeta({ layout: false, middleware: [] })

const route = useRoute()
const router = useRouter()

const password = ref('')
const showPwd = ref(false)
const loading = ref(false)
const errorMsg = ref('')

// 认证关闭时直接放行（直接访问 /login 但服务端未启用密码）
onMounted(async () => {
  const auth = await fetchAuthStatus(true)
  if (!auth.enabled) router.replace('/')
})

const onLogin = async () => {
  if (!password.value.trim() || loading.value) return
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await login(password.value)
    if (!res.ok) {
      errorMsg.value = res.error || '登录失败'
      return
    }
    const redirect = String(route.query.redirect || '/')
    router.replace(redirect.startsWith('/') ? redirect : '/')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%);
}

.login-card {
  background: #fff;
  border-radius: 16px;
  padding: 2.5rem 2rem;
  width: 100%;
  max-width: 380px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.35);
}
</style>
