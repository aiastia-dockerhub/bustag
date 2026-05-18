<template>
  <div class="container">
    <!-- Tab 切换 -->
    <div class="row py-3">
      <div class="col-12">
        <ul class="nav nav-tabs">
          <li class="nav-item">
            <a class="nav-link" :class="{ active: like === 1 }"
               href="#" @click.prevent="switchLike(1)">喜欢</a>
          </li>
          <li class="nav-item">
            <a class="nav-link" :class="{ active: like === 0 }"
               href="#" @click.prevent="switchLike(0)">不喜欢</a>
          </li>
          <li class="nav-item ms-auto">
            <select class="form-select form-select-sm" style="width: auto;" v-model="movieType" @change="onTypeChange">
              <option v-for="mt in movieTypes" :key="mt" :value="mt">{{ mt === 'normal' ? '有码' : '无码' }}</option>
            </select>
          </li>
        </ul>
      </div>
    </div>

    <!-- 列表 -->
    <div v-for="item in items" :key="item.fanhao" class="row py-3 card-item">
      <div class="col-12 col-md-4">
        <img class="img-fluid img-thumbnail coverimg" :src="imgProxyUrl(item.cover_img_url)"
             @click="showImg(item.cover_img_url)" alt="cover" loading="lazy" />
      </div>
      <div class="col-7 col-md-5">
        <div class="small text-muted">id: {{ item.id }}</div>
        <div class="small text-muted">发行日期: {{ item.release_date }}</div>
        <div class="small" :class="isToday(item.add_date) ? 'text-success' : 'text-muted'">添加日期: {{ item.add_date }}</div>
        <h6>{{ item.fanhao }}</h6>
        <a :href="item.url" target="_blank">{{ (item.title || '').substring(0, 30) }}</a>
        <div class="mt-1">
          <span v-for="t in (item.tags_dict?.genre || [])" :key="t" class="badge bg-primary me-1">{{ t }}</span>
        </div>
        <div class="mt-1">
          <span v-for="t in (item.tags_dict?.star || [])" :key="t" class="badge bg-warning text-dark me-1">{{ t }}</span>
        </div>
      </div>
      <div class="col-5 col-md-3 d-flex align-self-center justify-content-center">
        <button class="btn btn-primary mx-1" @click="correct(item.fanhao, true, $event)">正确</button>
        <button class="btn btn-danger" @click="correct(item.fanhao, false, $event)">错误</button>
      </div>
    </div>

    <!-- 分页 -->
    <Pagination :pageInfo="pageInfo" @go-page="goPage" />
  </div>
</template>

<script setup>
const { showImage } = useImageModal()

const items = ref([])
const pageInfo = ref(null)
const like = ref(1)
const movieTypes = ref(['normal'])
const movieType = ref('normal')

const showImg = (url) => showImage(imgProxyUrl(url))

const isToday = (dateStr) => {
  if (!dateStr) return false
  const today = new Date().toISOString().slice(0, 10)
  return String(dateStr).startsWith(today)
}

const loadData = async (page = 1, bustCache = false) => {
  try {
    const params = { like: like.value, page, type: movieType.value }
    if (bustCache) params._t = Date.now()
    const res = await $fetch('/api/index', { params })
    items.value = res.items
    pageInfo.value = res.page_info
    movieTypes.value = res.movie_types
    movieType.value = res.movie_type
  } catch (e) {
    console.error('加载推荐失败:', e)
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
    btn.textContent = '...'
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
      btn.textContent = isCorrect ? '正确' : '错误'
    }
    alert('反馈失败: ' + (e.data?.status || e.message))
  }
}

onMounted(() => loadData())
</script>