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
      </div>
    </div>

    <!-- 番号搜索结果 -->
    <div v-if="item" class="card-item">
      <div class="row g-3">
        <div class="col-12 col-sm-6 col-md-5 col-lg-4">
          <img class="img-fluid coverimg" :src="imgProxyUrl(item.cover_img_url)"
               @click="showImg(item.cover_img_url)" alt="cover" />
        </div>
        <div class="col-12 col-sm-7 col-md-8 col-lg-9 d-flex flex-column">
          <h5 class="mb-1 fw-bold">{{ item.fanhao }}</h5>
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
      </div>
    </div>

    <!-- 番号搜索无结果 -->
    <div v-if="searched && !item && query && !currentTag" class="text-center py-4">
      <div class="alert alert-warning d-inline-block">未找到番号「{{ query }}」的相关信息</div>
    </div>

    <!-- 标签搜索结果 -->
    <template v-if="tagItems.length > 0">
      <div class="py-2">
        <h6 class="fw-bold">🏷️ 标签「{{ currentTag }}」共 {{ tagPageInfo?.total_items || 0 }} 条</h6>
      </div>
      <div v-for="tItem in tagItems" :key="tItem.fanhao" class="card-item">
        <div class="row g-3">
          <div class="col-12 col-sm-6 col-md-5 col-lg-4">
            <img class="img-fluid coverimg" :src="imgProxyUrl(tItem.cover_img_url)"
                 @click="showImg(tItem.cover_img_url)" alt="cover" loading="lazy" />
          </div>
          <div class="col-12 col-sm-7 col-md-8 col-lg-9 d-flex flex-column">
            <h6 class="mb-1 fw-bold">{{ tItem.fanhao }}</h6>
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

const query = ref('')
const item = ref(null)
const tagItems = ref([])
const tagPageInfo = ref(null)
const genreTags = ref([])
const currentTagId = ref('')
const currentTag = ref('')
const loading = ref(false)
const searched = ref(false)

const showImg = (url) => showImage(imgProxyUrl(url))

const loadGenreTags = async () => {
  if (genreTags.value.length > 0) return
  try {
    const res = await $fetch('/api/search', { params: { page: 1 } })
    genreTags.value = res.genre_tags || []
  } catch (e) {
    console.error('加载标签失败:', e)
  }
}

const doSearch = async () => {
  if (!query.value.trim()) return
  currentTagId.value = ''
  currentTag.value = ''
  tagItems.value = []
  tagPageInfo.value = null
  searched.value = true
  loading.value = true
  try {
    const res = await $fetch('/api/search', { params: { q: query.value, page: 1 } })
    item.value = res.item
    genreTags.value = res.genre_tags || genreTags.value
  } catch (e) {
    console.error('搜索失败:', e)
  } finally {
    loading.value = false
  }
}

const doTagSearch = async () => {
  if (!currentTagId.value) return
  query.value = ''
  item.value = null
  searched.value = false
  loading.value = true
  try {
    const res = await $fetch('/api/search', { params: { tag_id: currentTagId.value, page: 1 } })
    tagItems.value = res.tag_items || []
    tagPageInfo.value = res.page_info
    currentTag.value = res.tag_value || ''
    genreTags.value = res.genre_tags || genreTags.value
  } catch (e) {
    console.error('搜索失败:', e)
  } finally {
    loading.value = false
  }
}

const goTagPage = async (page) => {
  loading.value = true
  try {
    const res = await $fetch('/api/search', { params: { tag_id: currentTagId.value, page } })
    tagItems.value = res.tag_items || []
    tagPageInfo.value = res.page_info
  } catch (e) {
    console.error('搜索失败:', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => loadGenreTags())
</script>