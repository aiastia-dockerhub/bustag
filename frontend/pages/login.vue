<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-brand">
        <span class="brand-mark"><AppIcon name="library" /></span>Bustag
      </div>
      <span class="page-eyebrow">YOUR PRIVATE LIBRARY</span>
      <h1>欢迎回来</h1>
      <p>登录你的私人资料库，发现下一部喜欢的影片。</p>
      <form @submit.prevent="onLogin">
        <label for="login-password" class="form-label">访问密码</label>
        <div class="input-group mb-4">
          <input
            id="login-password"
            v-model="password"
            :type="showPwd ? 'text' : 'password'"
            class="form-control"
            placeholder="请输入访问密码"
            autocomplete="current-password"
            required
          /><button
            class="btn btn-quiet"
            type="button"
            :aria-label="showPwd ? '隐藏密码' : '显示密码'"
            @click="showPwd = !showPwd"
          >
            <AppIcon name="eye" />
          </button>
        </div>
        <div v-if="errorMsg" class="alert alert-danger" role="alert">
          {{ errorMsg }}
        </div>
        <button type="submit" class="btn btn-primary w-100" :disabled="loading">
          {{ loading ? "登录中…" : "登录" }}<AppIcon name="right" />
        </button>
      </form>
      <div class="login-footnote">只属于你的收藏与偏好。</div>
    </div>
  </div>
</template>

<script setup>
definePageMeta({ layout: false, middleware: [] });

const route = useRoute();
const router = useRouter();

const password = ref("");
const showPwd = ref(false);
const loading = ref(false);
const errorMsg = ref("");

// 认证关闭时直接放行（直接访问 /login 但服务端未启用密码）
onMounted(async () => {
  const auth = await fetchAuthStatus(true);
  if (!auth.enabled) router.replace("/");
});

const onLogin = async () => {
  if (!password.value.trim() || loading.value) return;
  loading.value = true;
  errorMsg.value = "";
  try {
    const res = await login(password.value);
    if (!res.ok) {
      errorMsg.value = res.error || "登录失败";
      return;
    }
    const redirect = String(route.query.redirect || "/");
    router.replace(redirect.startsWith("/") ? redirect : "/");
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  min-height: 100dvh;
  display: grid;
  place-items: center;
  padding: 24px;
  background: var(--canvas);
}
.login-card {
  width: 100%;
  max-width: 420px;
  padding: 40px;
  border: 1px solid var(--line);
  background: var(--surface);
  border-radius: 20px;
  box-shadow: 0 12px 48px rgb(28 52 64 / 5%);
}
.login-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 42px;
  font-size: 24px;
  font-weight: 650;
  letter-spacing: -1px;
}
h1 {
  margin: 12px 0;
  font-size: 29px;
  font-weight: 650;
  letter-spacing: -1px;
}
p {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.9;
  margin-bottom: 30px;
}
.login-footnote {
  border-top: 1px solid var(--line);
  margin-top: 30px;
  padding-top: 22px;
  text-align: center;
  color: var(--faint);
  font-size: 11px;
}
@media (max-width: 480px) {
  .login-card {
    padding: 28px;
  }
}
</style>
