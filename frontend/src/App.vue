<template>
  <div>
    <!-- 导航栏 -->
    <nav class="navbar navbar-expand-lg navbar-light bg-light">
      <div class="container">
        <router-link class="navbar-brand" to="/">
          <img src="/logo.png" alt="Bustag" height="40" />
        </router-link>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
          <ul class="navbar-nav">
            <li class="nav-item">
              <router-link class="nav-link" :class="{ active: $route.path === '/' }" to="/">推荐</router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" :class="{ active: $route.path === '/tagit' }" to="/tagit">打标</router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" :class="{ active: $route.path === '/local' }" to="/local">本地</router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" :class="{ active: $route.path === '/model' }" to="/model">模型</router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" :class="{ active: $route.path === '/load_db' }" to="/load_db">数据</router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" :class="{ active: $route.path === '/search' }" to="/search">搜索</router-link>
            </li>
          </ul>
        </div>
      </div>
    </nav>

    <!-- 消息提示 -->
    <div class="container" v-if="globalMsg">
      <div class="row py-3">
        <div class="col-12">
          <div class="alert alert-success alert-dismissible fade show" role="alert">
            {{ globalMsg }}
            <button type="button" class="btn-close" @click="globalMsg = ''"></button>
          </div>
        </div>
      </div>
    </div>

    <!-- 页面内容 -->
    <router-view @message="globalMsg = $event" />

    <!-- 图片放大模态框 -->
    <div class="modal fade" id="imageModal" tabindex="-1">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-body">
            <button type="button" class="btn-close position-absolute top-0 end-0 m-2" data-bs-dismiss="modal"></button>
            <img :src="modalImageUrl" class="imagepreview" />
          </div>
        </div>
      </div>
    </div>

    <!-- 页脚 -->
    <footer class="my-3">
      <div class="container">
        <div class="col text-center">
          <p class="mb-1">
            <span class="badge bg-info rounded-pill">version : {{ version }}</span>
          </p>
          <p class="mb-0">
            Developed by 凤凰山@2019
            <a href="https://github.com/gxtrobot/bustag" target="_blank">github</a>
          </p>
        </div>
      </div>
    </footer>
  </div>
</template>

<script>
import { ref, onMounted, provide } from 'vue'
import { getVersion } from './assets/api.js'

export default {
  setup() {
    const version = ref('')
    const globalMsg = ref('')
    const modalImageUrl = ref('')

    onMounted(async () => {
      try {
        const res = await getVersion()
        version.value = res.data.version
      } catch (e) {
        version.value = 'unknown'
      }
    })

    // 提供图片放大方法给子组件
    const showImage = (url) => {
      modalImageUrl.value = url
      const modal = new bootstrap.Modal(document.getElementById('imageModal'))
      modal.show()
    }
    provide('showImage', showImage)

    return { version, globalMsg, modalImageUrl }
  }
}
</script>