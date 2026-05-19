<template>
  <div class="container">
    <!-- Tab 切换 -->
    <div class="d-flex align-items-center py-3 border-bottom mb-3">
      <ul class="nav nav-tabs border-0 mb-0">
        <li class="nav-item">
          <a class="nav-link" :class="{ active: like === 1 }"
             href="#" @click.prevent="switchLike(1)">👍 喜欢</a>
        </li>
        <li class="nav-item">
          <a class="nav-link" :class="{ active: like === 0 }"
             href="#" @click.prevent="switchLike(0)">👎 不喜欢</a>
        </li>
      </ul>
      <div class="ms-auto d-flex align-items-center gap-3">
        <span v-if="todayUpdate > 0" class="badge bg-info text-dark">📥 今日更新 {{ todayUpdate }}</span>
        <span v-if="todayRecommend > 0" class="badge bg-success">🤖 今日推荐 {{ todayRecommend }}</span>
        <select class="form-select form-select-sm" style="width: auto;" v-model="movieType" @change="onTypeChange">
          <option v-for="mt in movieTypes" :key="mt" :value="mt">{{ mt === 'normal' ? '有码' : '无码' }}</option>
        </select>
      </div>
    </div>

    <!-- 列表 -->
    <div v-for="item in items" :key="item.fanhao" class="card-item">
      <div class="row g-3">
        <div class="col-12 col-sm-6 col-md-5 col-lg-4">
          <img class="img-fluid coverimg" :src="imgProxyUrl(item.cover_img_url)"
               @click="showImg(item.cover_img_url)" alt="cover" loading="lazy" />
        </div>
        <div class="col-12 col-sm-6 col-md-4 col-lg-5 d-flex flex-column">
          <h6 class="mb-1 fw-bold">{{ item.fanhao }}</h6>
          <a :href="item.url" target="_blank" class="text-decoration-none small mb-2 text-truncate d-inline-block" style="max-width: 100%;">
            {{ item.title || '' }}
          </a>
          <div class="small text-muted mb-1">
            <span class="me-3">📅 发行: {{ item.release_date || '-' }}</span>
            <span :class="isToday(item.add_date) ? 'text-success fw-bold' : 'text-muted'">📥 添加: {{ item.add_date || '-' }}</span>
          </div>
          <div class="mt-1" v-if="item.tags_dict?.genre?.length">
            <span v-for="t in item.tags_dict.genre" :key="t" class="badge bg-primary bg-opacity-75 badge-tag me-1 mb-1">{{ t }}</span>
          </div>
          <div class="mt-1" v-if="item.tags_dict?.star?.length">
            <span v-for="t in item.tags_dict.star" :key="t" class="badge bg-warning text-dark badge-tag me-1 mb-1">{{ t }}</span>
          </div>
        </div>
        <div class="col-12 col-sm-12 col-md-3 col-lg-3 d-flex align-items-center justify-content-md-end">
          <button class="btn btn-outline-info btn-sm me-2" @click="copyMagnet(item.fanhao)"
                  :disabled="!!magnetLoading[item.fanhao]">
            <template v-if="magnetLoading[item.fanhao] === 'done'">✅ 已复制</template>
            <template v-else-if="magnetLoading[item.fanhao]">⏳</template>
            <template v-else>🧲 磁力</template>
          </button>
          <button class="btn btn-outline-success btn-sm me-2" @click="correct(item.fanhao, true, $event)">
            ✅ 正确
          </button>
          <button class="btn btn-outline-danger btn-sm" @click="correct(item.fanhao, false, $event)">
            ❌ 错误
          </button>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="!items.length && !loading" class="text-center py-5 text-muted">
      <p class="fs-4">📭 暂无数据</p>
    </div>

    <!-- 分页 -->
    <Pagination :pageInfo="pageInfo" @go-page="goPage" />
  </div>
</template>

<script setup>
const { showImage } = useImageModal()
const { magnetLoading, copyMagnet } = useMagnet()

const items = ref([])
const pageInfo = ref(null)
const like = ref(1)
const movieTypes = ref(['normal'])
const movieType = ref('normal')
const loading = ref(false)
const todayUpdate = ref(0)
const todayRecommend = ref(0)

const showImg = (url) => showImage(imgProxyUrl(url))

const isToday = (dateStr) => {
  if (!dateStr) return false
  const today = new Date().toISOString().slice(0, 10)
  return String(dateStr).startsWith(today)
}

const loadData = async (page = 1, bustCache = false) => {
  loading.value = true
  try {
    const params = { like: like.value, page, type: movieType.value }
    if (bustCache) params._t = Date.now()
    const res = await $fetch('/api/index', { params })
    items.value = res.items
    pageInfo.value = res.page_info
    movieTypes.value = res.movie_types
    movieType.value = res.movie_type
    todayUpdate.value = res.today_update || 0
    todayRecommend.value = res.today_recommend || 0
  } catch (e) {
    console.error('加载推荐失败:', e)
  } finally {
    loading.value = false
  }
}

const switchLike = (lk) => {
  like.value = lk
  loadData(1)
}

const onTypeChange = () => loadData(1)
const goPage = (page) => loadData(page)

const correct = async (fanhao, isCorrect, event) => {
  const btn = event?.target
  if (btn) {
    btn.disabled = true
    btn.innerHTML = '⏳'
  }
  try {
    await $fetch(`/api/correct/${fanhao}`, {
      method: 'POST',
      body: { is_correct: isCorrect },
    })
    const page = pageInfo.value?.current_page || 1
    loadData(page, true)
  } catch (e) {
    console.error('反馈失败:', e)
    if (btn) {
      btn.disabled = false
      btn.textContent = isCorrect ? '✅ 正确' : '❌ 错误'
    }
    alert('反馈失败: ' + (e.data?.status || e.message))
  }
}

onMounted(() => loadData())
</script>