<template>
  <div class="container">
    <!-- 搜索区域 -->
    <div class="card-item mt-3">
      <div class="row g-3 align-items-end">
        <div class="col-12 col-md-5">
          <label class="form-label small fw-bold">🔍 番号搜索</label>
          <form @submit.prevent="doSearch" class="input-group">
            <input class="form-control search-input" v-model="query" placeholder="输入番号，如 SSIS-001" />
            <button class="btn btn-primary" type="submit">搜索</button>
          </form>
        </div>
        <div class="col-12 col-md-5">
          <label class="form-label small fw-bold">🏷️ 标签搜索</label>
          <form @submit.prevent="doTagSearch" class="input-group">
            <select class="form-select" v-model="currentTagId">
              <option value="">-- 选择标签类型 --</option>
              <option v-for="tag in genreTags" :key="tag.id" :value="tag.id">{{ tag.value }}</option>
            </select>
            <button class="btn btn-outline-secondary" type="submit">搜索</button>
          </form>
        </div>
        <div class="col-12 col-md-5">
          <label class="form-label small fw-bold">👩 女优搜索</label>
          <form @submit.prevent="doStarSearch" class="input-group">
            <select class="form-select" v-model="currentStarId">
              <option value="">-- 选择女优 --</option>
              <option v-for="star in starTags" :key="star.id" :value="star.id">{{ star.value }}</option>
            </select>
            <button class="btn btn-outline-secondary" type="submit">搜索</button>
          </form>
        </div>
      </div>
    </div>

    <!-- 番号搜索结果 -->
    <div v-if="item" class="card-item">
      <div class="row g-3">
        <div class="col-12 col-sm-6 col-md-5 col-lg-4">
          <img class="img-fluid coverimg" :src="imgProxyUrl(item.cover_img_url)"
               @click="showImg(item.cover_img_url)" alt="cover" />
        </div>
        <div class="col-12 col-sm-6 col-md-4 col-lg-5 d-flex flex-column">
          <div class="d-flex align-items-center gap-2 mb-1">
            <h5 class="mb-0 fw-bold">{{ item.fanhao }}</h5>
            <span v-if="item.rate_type === 1 && item.rate_value === 1" class="badge bg-success">🟢 喜欢</span>
            <span v-else-if="item.rate_type === 1 && item.rate_value === 0" class="badge bg-danger">🔴 不喜欢</span>
            <span v-else-if="item.rate_type === 2" class="badge bg-info">🤖 推荐</span>
            <span v-else class="badge bg-secondary">⚪ 未打标</span>
          </div>
          <a :href="item.url" target="_blank" class="text-decoration-none small mb-2">{{ item.title || '' }}</a>
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
          <button class="btn btn-outline-info btn-sm me-2" @click="copyMagnet(item.fanhao)"
                  :disabled="!!magnetLoading[item.fanhao]">
            <template v-if="magnetLoading[item.fanhao] === 'done'">✅ 已复制</template>
            <template v-else-if="magnetLoading[item.fanhao]">⏳</template>
            <template v-else>🧲 磁力</template>
          </button>
          <button class="btn btn-outline-success btn-sm me-2" @click="tagItem(item.fanhao, 1, $event)">👍 喜欢</button>
          <button class="btn btn-outline-danger btn-sm" @click="tagItem(item.fanhao, 0, $event)">👎 不喜欢</button>
        </div>
      </div>
    </div>

    <!-- 番号搜索无结果 -->
    <div v-if="searched && !item && query && !currentTag" class="text-center py-4">
      <div class="alert alert-warning d-inline-block">未找到番号「{{ query }}」的相关信息</div>
    </div>

    <!-- 标签/女优搜索结果 -->
    <template v-if="tagItems.length > 0">
      <div class="py-2">
        <h6 class="fw-bold">
          {{ searchType === 'star' ? '👩 女优' : '🏷️ 标签' }}「{{ currentTag }}」共 {{ tagPageInfo?.total_items || 0 }} 条
        </h6>
      </div>
      <div v-for="tItem in tagItems" :key="tItem.fanhao" class="card-item">
        <div class="row g-3">
          <div class="col-12 col-sm-6 col-md-5 col-lg-4">
            <img class="img-fluid coverimg" :src="imgProxyUrl(tItem.cover_img_url)"
                 @click="showImg(tItem.cover_img_url)" alt="cover" loading="lazy" />
          </div>
          <div class="col-12 col-sm-6 col-md-4 col-lg-5 d-flex flex-column">
            <div class="d-flex align-items-center gap-2 mb-1">
              <h6 class="mb-0 fw-bold">{{ tItem.fanhao }}</h6>
              <span v-if="tItem.rate_type === 1 && tItem.rate_value === 1" class="badge bg-success">🟢 喜欢</span>
              <span v-else-if="tItem.rate_type === 1 && tItem.rate_value === 0" class="badge bg-danger">🔴 不喜欢</span>
              <span v-else-if="tItem.rate_type === 2" class="badge bg-info">🤖 推荐</span>
              <span v-else class="badge bg-secondary">⚪ 未打标</span>
            </div>
            <a :href="tItem.url" target="_blank" class="text-decoration-none small mb-2 text-truncate d-inline-block" style="max-width: 100%;">
              {{ tItem.title || '' }}
            </a>
            <div class="small text-muted mb-1">
              <span class="me-3">📅 发行: {{ tItem.release_date || '-' }}</span>
              <span>📥 添加: {{ tItem.add_date || '-' }}</span>
            </div>
            <div class="mt-1" v-if="tItem.tags_dict?.genre?.length">
              <span v-for="t in tItem.tags_dict.genre" :key="t" class="badge bg-primary bg-opacity-75 badge-tag me-1 mb-1">{{ t }}</span>
            </div>
            <div class="mt-1" v-if="tItem.tags_dict?.star?.length">
              <span v-for="t in tItem.tags_dict.star" :key="t" class="badge bg-warning text-dark badge-tag me-1 mb-1">{{ t }}</span>
            </div>
          </div>
          <div class="col-12 col-sm-12 col-md-3 col-lg-3 d-flex align-items-center justify-content-md-end">
            <button class="btn btn-outline-info btn-sm me-2" @click="copyMagnet(tItem.fanhao)"
                    :disabled="!!magnetLoading[tItem.fanhao]">
              <template v-if="magnetLoading[tItem.fanhao] === 'done'">✅ 已复制</template>
              <template v-else-if="magnetLoading[tItem.fanhao]">⏳</template>
              <template v-else>🧲 磁力</template>
            </button>
            <button class="btn btn-outline-success btn-sm me-2" @click="tagItem(tItem.fanhao, 1, $event)">👍</button>
            <button class="btn btn-outline-danger btn-sm" @click="tagItem(tItem.fanhao, 0, $event)">👎</button>
          </div>
        </div>
      </div>
      <Pagination :pageInfo="tagPageInfo" @go-page="goTagPage" />
    </template>

    <!-- 标签搜索无结果 -->
    <div v-if="currentTag && tagItems.length === 0 && !loading" class="text-center py-4">
      <div class="alert alert-warning d-inline-block">未找到标签「{{ currentTag }}」的相关信息</div>
    </div>
  </div>
</template>

<script setup>
const { showImage } = useImageModal()
const { magnetLoading, copyMagnet } = useMagnet()

const query = ref('')
const item = ref(null)
const tagItems = ref([])
const tagPageInfo = ref(null)
const genreTags = ref([])
const starTags = ref([])
const currentTagId = ref('')
const currentStarId = ref('')
const currentTag = ref('')
const loading = ref(false)
const searched = ref(false)

const showImg = (url) => showImage(imgProxyUrl(url))

const loadTags = async () => {
  if (genreTags.value.length > 0 && starTags.value.length > 0) return
  try {
    const res = await $fetch('/api/search', { params: { page: 1 } })
    genreTags.value = res.genre_tags || []
    starTags.value = res.star_tags || []
  } catch (e) {
    console.error('加载标签失败:', e)
  }
}

// 当前列表搜索类型: '' = 无, 'tag' = 标签, 'star' = 女优
const searchType = ref('')

const doSearch = async () => {
  if (!query.value.trim()) return
  currentTagId.value = ''
  currentStarId.value = ''
  currentTag.value = ''
  searchType.value = ''
  tagItems.value = []
  tagPageInfo.value = null
  searched.value = true
  loading.value = true
  try {
    const res = await $fetch('/api/search', { params: { q: query.value, page: 1 } })
    item.value = res.item
    genreTags.value = res.genre_tags || genreTags.value
    starTags.value = res.star_tags || starTags.value
  } catch (e) {
    console.error('搜索失败:', e)
  } finally {
    loading.value = false
  }
}

const doTagSearch = async () => {
  if (!currentTagId.value) return
  query.value = ''
  currentStarId.value = ''
  item.value = null
  searched.value = false
  searchType.value = 'tag'
  loading.value = true
  try {
    const res = await $fetch('/api/search', { params: { tag_id: currentTagId.value, page: 1 } })
    tagItems.value = res.tag_items || []
    tagPageInfo.value = res.page_info
    currentTag.value = res.tag_value || ''
    genreTags.value = res.genre_tags || genreTags.value
    starTags.value = res.star_tags || starTags.value
  } catch (e) {
    console.error('搜索失败:', e)
  } finally {
    loading.value = false
  }
}

const doStarSearch = async () => {
  if (!currentStarId.value) return
  query.value = ''
  currentTagId.value = ''
  item.value = null
  searched.value = false
  searchType.value = 'star'
  loading.value = true
  try {
    const res = await $fetch('/api/search', { params: { star_id: currentStarId.value, page: 1 } })
    tagItems.value = res.tag_items || []
    tagPageInfo.value = res.page_info
    currentTag.value = res.tag_value || ''
    genreTags.value = res.genre_tags || genreTags.value
    starTags.value = res.star_tags || starTags.value
  } catch (e) {
    console.error('搜索失败:', e)
  } finally {
    loading.value = false
  }
}

const goTagPage = async (page) => {
  loading.value = true
  try {
    const params = { page }
    if (searchType.value === 'star') {
      params.star_id = currentStarId.value
    } else {
      params.tag_id = currentTagId.value
    }
    const res = await $fetch('/api/search', { params })
    tagItems.value = res.tag_items || []
    tagPageInfo.value = res.page_info
  } catch (e) {
    console.error('搜索失败:', e)
  } finally {
    loading.value = false
  }
}

const refreshTagResults = async () => {
  const page = tagPageInfo.value?.current_page || 1
  const params = { page }
  if (searchType.value === 'star') {
    params.star_id = currentStarId.value
  } else {
    params.tag_id = currentTagId.value
  }
  const res = await $fetch('/api/search', { params })
  tagItems.value = res.tag_items || []
  tagPageInfo.value = res.page_info
}

const tagItem = async (fanhao, rateValue, event) => {
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
    // 刷新当前搜索结果以更新打标状态
    if (item.value && item.value.fanhao === fanhao && query.value) {
      // 番号搜索结果：重新搜索
      const res = await $fetch('/api/search', { params: { q: query.value, page: 1 } })
      item.value = res.item
    } else if (searchType.value) {
      // 标签/女优搜索结果：刷新当前页
      await refreshTagResults()
    }
  } catch (e) {
    console.error('打标失败:', e)
    if (btn) {
      btn.disabled = false
      btn.textContent = rateValue === 1 ? '👍 喜欢' : '👎 不喜欢'
    }
    alert('打标失败: ' + (e.data?.status || e.message))
  }
}

onMounted(() => loadTags())
</script>