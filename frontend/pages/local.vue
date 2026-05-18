<template>
  <div class="container">
    <!-- 子页面 Tab -->
    <div class="d-flex align-items-center py-3 border-bottom mb-3">
      <ul class="nav nav-tabs border-0 mb-0">
        <li class="nav-item">
          <NuxtLink class="nav-link active" to="/local">📂 本地文件</NuxtLink>
        </li>
        <li class="nav-item">
          <NuxtLink class="nav-link" to="/local_fanhao">📤 上传番号</NuxtLink>
        </li>
      </ul>
    </div>

    <div v-for="localItem in items" :key="localItem.id" class="card-item">
      <div class="row g-3">
        <div class="col-12 col-sm-5 col-md-4 col-lg-3">
          <img class="img-fluid coverimg" :src="imgProxyUrl(localItem.item.cover_img_url)"
               @click="showImg(localItem.item.cover_img_url)" alt="cover" loading="lazy" />
        </div>
        <div class="col-12 col-sm-7 col-md-5 col-lg-6 d-flex flex-column">
          <h6 class="mb-1 fw-bold">{{ localItem.item.fanhao }}</h6>
          <a :href="localItem.item.url" target="_blank" class="text-decoration-none small mb-2 text-truncate d-inline-block" style="max-width: 100%;">
            {{ localItem.item.title || '' }}
          </a>
          <div class="small text-muted mb-1">
            <span class="me-3">📅 发行: {{ localItem.item.release_date || '-' }}</span>
          </div>
          <div class="small text-muted mb-1">
            <span class="me-3">👁️ 观看: {{ localItem.view_times || 0 }} 次</span>
            <span>🕐 上次: {{ localItem.last_view_date || '-' }}</span>
          </div>
          <div class="mt-1" v-if="localItem.item.tags_dict?.genre?.length">
            <span v-for="t in localItem.item.tags_dict.genre" :key="t" class="badge bg-primary bg-opacity-75 badge-tag me-1 mb-1">{{ t }}</span>
          </div>
          <div class="mt-1" v-if="localItem.item.tags_dict?.star?.length">
            <span v-for="t in localItem.item.tags_dict.star" :key="t" class="badge bg-warning text-dark badge-tag me-1 mb-1">{{ t }}</span>
          </div>
        </div>
        <div class="col-12 col-sm-12 col-md-3 col-lg-3 d-flex align-items-center justify-content-md-end">
          <a class="btn btn-primary btn-sm" :href="'/api/local_play/' + localItem.id" target="_blank">▶️ 播放</a>
        </div>
      </div>
    </div>

    <div v-if="!items.length" class="text-center py-5 text-muted">
      <p class="fs-4">📭 暂无本地文件</p>
    </div>

    <Pagination :pageInfo="pageInfo" @go-page="goPage" />
  </div>
</template>

<script setup>
const { showImage } = useImageModal()

const items = ref([])
const pageInfo = ref(null)

const showImg = (url) => showImage(imgProxyUrl(url))

const loadData = async (page = 1) => {
  try {
    const res = await $fetch('/api/local', { params: { page } })
    items.value = res.items
    pageInfo.value = res.page_info
  } catch (e) {
    console.error('加载本地文件失败:', e)
  }
}

const goPage = (page) => loadData(page)

onMounted(() => loadData())
</script>