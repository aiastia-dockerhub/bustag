<template>
  <div class="container">
    <!-- Tab 切换 -->
    <div class="d-flex align-items-center py-3 border-bottom mb-3">
      <ul class="nav nav-tabs border-0 mb-0">
        <li class="nav-item">
          <a class="nav-link" :class="{ active: like === null }"
             href="#" @click.prevent="switchTab(null)">未打标</a>
        </li>
        <li class="nav-item">
          <a class="nav-link" :class="{ active: like === 1 }"
             href="#" @click.prevent="switchTab(1)">👍 喜欢</a>
        </li>
        <li class="nav-item">
          <a class="nav-link" :class="{ active: like === 0 }"
             href="#" @click.prevent="switchTab(0)">👎 不喜欢</a>
        </li>
      </ul>
      <div class="ms-auto">
        <select class="form-select form-select-sm" style="width: auto;" v-model="movieType" @change="onTypeChange">
          <option v-for="mt in movieTypes" :key="mt" :value="mt">{{ mt === 'normal' ? '有码' : '无码' }}</option>
        </select>
      </div>
    </div>

    <!-- 列表 -->
    <div v-for="item in items" :key="item.fanhao" class="card-item">
      <div class="row g-3">
        <div class="col-12 col-sm-5 col-md-4 col-lg-3">
          <img class="img-fluid coverimg" :src="imgProxyUrl(item.cover_img_url)"
               @click="showImg(item.cover_img_url)" alt="cover" loading="lazy" />
        </div>
        <div class="col-12 col-sm-7 col-md-5 col-lg-6 d-flex flex-column">
          <h6 class="mb-1 fw-bold">{{ item.fanhao }}</h6>
          <a :href="item.url" target="_blank" class="text-decoration-none small mb-2 text-truncate d-inline-block" style="max-width: 100%;">
            {{ item.title || '' }}
          </a>
          <div class="small text-muted mb-1">
            <span class="me-3">📅 发行: {{ item.release_date || '-' }}</span>
            <span>📥 添加: {{ item.add_date || '-' }}</span>
          </div>
          <div class="mt-1" v-if="item.tags_dict?.genre?.length">
            <span v-for="t in item.tags_dict.genre" :key="t" class="badge bg-primary bg-opacity-75 badge-tag me-1 mb-1">{{ t }}</span>
          </div>
          <div class="mt-1" v-if="item.tags_dict?.star?.length">
            <span v-for="t in item.tags_dict.star" :key="t" class="badge bg-warning text-dark badge-tag me-1 mb-1">{{ t }}</span>
          </div>
        </div>
        <div class="col-12 col-sm-12 col-md-3 col-lg-3 d-flex align-items-center justify-content-md-end">
          <button class="btn btn-outline-success btn-sm me-2" @click="tag(item.fanhao, 1, $event)">👍 喜欢</button>
          <button class="btn btn-outline-danger btn-sm" @click="tag(item.fanhao, 0, $event)">👎 不喜欢</button>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="!items.length" class="text-center py-5 text-muted">
      <p class="fs-4">📭 暂无数据</p>
    </div>

    <!-- 分页 -->
    <Pagination :pageInfo="pageInfo" @go-page="goPage" />
  </div>
</template>

<script setup>
const { showImage } = useImageModal()

const items = ref([])
const pageInfo = ref(null)
const like = ref(null)
const movieTypes = ref(['normal'])
const movieType = ref('normal')

const showImg = (url) => showImage(imgProxyUrl(url))

const loadData = async (page = 1) => {
  try {
    const params = { page, type: movieType.value }
    if (like.value !== null) params.like = like.value
    const res = await $fetch('/api/tagit', { params })
    items.value = res.items
    pageInfo.value = res.page_info
    movieTypes.value = res.movie_types
    movieType.value = res.movie_type
  } catch (e) {
    console.error('加载打标数据失败:', e)
  }
}

const switchTab = (lk) => {
  like.value = lk
  loadData(1)
}

const onTypeChange = () => loadData(1)
const goPage = (page) => loadData(page)

const tag = async (fanhao, rateValue, event) => {
  const btn = event?.target
  if (btn) {
    btn.disabled = true
    btn.innerHTML = '⏳'
  }
  try {
    await $fetch(`/api/tag/${fanhao}`, {
      method: 'POST',
      body: { rate_value: rateValue },
    })
    const page = pageInfo.value?.current_page || 1
    loadData(page)
  } catch (e) {
    console.error('打标失败:', e)
    if (btn) {
      btn.disabled = false
      btn.textContent = rateValue === 1 ? '👍 喜欢' : '👎 不喜欢'
    }
    alert('打标失败: ' + (e.data?.status || e.message))
  }
}

onMounted(() => loadData())
</script>