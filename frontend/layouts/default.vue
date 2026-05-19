<template>
  <div class="d-flex flex-column min-vh-100">
    <!-- 导航栏 -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
      <div class="container">
        <NuxtLink class="navbar-brand d-flex align-items-center" to="/">
          <img src="/logo.png" alt="Bustag" height="32" class="me-2" />
          <strong>Bustag</strong>
        </NuxtLink>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
          <ul class="navbar-nav ms-auto">
            <li class="nav-item">
              <NuxtLink class="nav-link" :class="{ active: $route.path === '/' }" to="/">🏠 推荐</NuxtLink>
            </li>
            <li class="nav-item">
              <NuxtLink class="nav-link" :class="{ active: $route.path === '/tagit' }" to="/tagit">🏷️ 打标</NuxtLink>
            </li>
            <li class="nav-item">
              <NuxtLink class="nav-link" :class="{ active: $route.path === '/local' || $route.path === '/local_fanhao' }" to="/local">📂 本地</NuxtLink>
            </li>
            <li class="nav-item">
              <NuxtLink class="nav-link" :class="{ active: $route.path === '/model' }" to="/model">🤖 模型</NuxtLink>
            </li>
            <li class="nav-item">
              <NuxtLink class="nav-link" :class="{ active: $route.path === '/load_db' }" to="/load_db">💾 数据</NuxtLink>
            </li>
            <li class="nav-item">
              <NuxtLink class="nav-link" :class="{ active: $route.path === '/search' }" to="/search">🔍 搜索</NuxtLink>
            </li>
          </ul>
        </div>
      </div>
    </nav>

    <!-- 消息提示 -->
    <div class="container mt-3" v-if="globalMsg">
      <div class="alert alert-success alert-dismissible fade show" role="alert">
        ✅ {{ globalMsg }}
        <button type="button" class="btn-close" @click="globalMsg = ''"></button>
      </div>
    </div>

    <!-- 页面内容 -->
    <main class="flex-grow-1">
      <NuxtPage @message="globalMsg = $event" />
    </main>

    <!-- 图片放大模态框（纯 Vue，不依赖 Bootstrap JS） -->
    <ClientOnly>
      <div v-if="modalUrl" class="img-modal-overlay" @click="hideImage">
        <img :src="modalUrl" alt="preview" />
      </div>
    </ClientOnly>

    <!-- 页脚 -->
    <footer class="py-3 mt-4">
      <div class="container">
        <div class="text-center">
          <p class="mb-1">
            <span class="badge bg-secondary rounded-pill">v{{ version }}</span>
          </p>
          <p class="mb-0 small">
            Developed by 凤凰山@2019 ·
            <a href="https://github.com/aiastia-dockerhub/bustag" target="_blank">GitHub</a>
            · 2026 Nuxt Edition
          </p>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
const globalMsg = ref('')
const config = useRuntimeConfig()
const version = config.public.appVersion || 'dev'
const { modalUrl, hideImage } = useImageModal()
</script>
