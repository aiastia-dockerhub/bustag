<template>
  <div class="container">
    <!-- 番号搜索 -->
    <div class="row py-3">
      <div class="col-12">
        <form @submit.prevent="doSearch" class="form-inline justify-content-center">
          <div class="input-group" style="max-width: 400px;">
            <input class="form-control" v-model="query" placeholder="输入番号搜索，如 SSIS-001" />
            <div class="input-group-append">
              <button class="btn btn-primary" type="submit">搜索</button>
            </div>
          </div>
        </form>
      </div>
    </div>

    <!-- 标签搜索 -->
    <div class="row py-2">
      <div class="col-12 text-center">
        <form @submit.prevent="doTagSearch" class="form-inline justify-content-center">
          <div class="input-group" style="max-width: 400px;">
            <select class="form-control" v-model="currentTag">
              <option value="">-- 选择标签类型 --</option>
              <option v-for="tag in genreTags" :key="tag" :value="tag">{{ tag }}</option>
            </select>
            <div class="input-group-append">
              <button class="btn btn-secondary" type="submit">按标签搜索</button>
            </div>
          </div>
        </form>
      </div>
    </div>

    <!-- 番号搜索结果 -->
    <div v-if="item" class="row py-3 card-item">
      <div class="col-12 col-md-4">
        <img class="img-fluid img-thumbnail coverimg" :src="imgProxyUrl(item.cover_img_url)"
             @click="showImg(item.cover_img_url)" alt="cover" />
      </div>
      <div class="col-12 col-md-8">
        <h5>{{ item.fanhao }}</h5>
        <a :href="item.url" target="_blank">{{ item.title }}</a>
        <div class="small text-muted mt-2">发行日期: {{ item.release_date }}</div>
        <div class="small text-muted">添加日期: {{ item.add_date }}</div>
        <div class="mt-2">
          <span v-for="t in (item.tags_dict?.genre || [])" :key="t" class="badge bg-primary me-1">{{ t }}</span>
        </div>
        <div class="mt-1">
          <span v-for="t in (item.tags_dict?.star || [])" :key="t" class="badge bg-warning text-dark me-1">{{ t }}</span>
        </div>
      </div>
    </div>

    <!-- 番号搜索无结果 -->
    <div v-if="searched && !item && query && !currentTag" class="row py-3">
      <div class="col-12 text-center">
        <div class="alert alert-warning">未找到番号「{{ query }}」的相关信息</div>
      </div>
    </div>

    <!-- 标签搜索结果 -->
    <template v-if="tagItems.length > 0">
      <div class="row py-2">
        <div class="col-12">
          <h6>标签「{{ currentTag }}」共找到 {{ tagPageInfo?.total_items || 0 }} 条结果</h6>
        </div>
      </div>
      <div v-for="tItem in tagItems" :key="tItem.fanhao" class="row py-3 card-item">
        <div class="col-12 col-md-4">
          <img class="img-fluid img-thumbnail coverimg" :src="imgProxyUrl(tItem.cover_img_url)"
               @click="showImg(tItem.cover_img_url)" alt="cover" loading="lazy" />
        </div>
        <div class="col-12 col-md-8">
          <div class="small text-muted">id: {{ tItem.id }}</div>
          <div class="small text-muted">发行日期: {{ tItem.release_date }}</div>
          <div class="small text-muted">添加日期: {{ tItem.add_date }}</div>
          <h6>{{ tItem.fanhao }}</h6>
          <a :href="tItem.url" target="_blank">{{ (tItem.title || '').substring(0, 30) }}</a>
          <div class="mt-1">
            <span v-for="t in (tItem.tags_dict?.genre || [])" :key="t" class="badge bg-primary me-1">{{ t }}</span>
          </div>
          <div class="mt-1">
            <span v-for="t in (tItem.tags_dict?.star || [])" :key="t" class="badge bg-warning text-dark me-1">{{ t }}</span>
          </div>
        </div>
      </div>
      <Pagination :pageInfo="tagPageInfo" @go-page="goTagPage" />
    </template>

    <!-- 标签搜索无结果 -->
    <div v-if="currentTag && tagItems.length === 0 && !loading" class="row py-3">
      <div class="col-12 text-center">
        <div class="alert alert-warning">未找到标签「{{ currentTag }}」的相关信息</div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, inject } from 'vue'
import { getSearch, imgProxyUrl } from '../assets/api.js'
import Pagination from '../components/Pagination.vue'

export default {
  components: { Pagination },
  setup() {
    const query = ref('')
    const item = ref(null)
    const tagItems = ref([])
    const tagPageInfo = ref(null)
    const genreTags = ref([])
    const currentTag = ref('')
    const loading = ref(false)
    const searched = ref(false)
    const showImage = inject('showImage')

    const showImg = (url) => showImage(imgProxyUrl(url))

    const loadPage = async (page = 1) => {
      loading.value = true
      try {
        const params = { page }
        if (query.value) params.q = query.value
        if (currentTag.value) params.tag = currentTag.value
        const res = await getSearch(params)
        item.value = res.data.item
        tagItems.value = res.data.tag_items || []
        tagPageInfo.value = res.data.page_info
        genreTags.value = res.data.genre_tags || []
      } catch (e) {
        console.error('搜索失败:', e)
      } finally {
        loading.value = false
      }
    }

    const doSearch = () => {
      currentTag.value = ''
      tagItems.value = []
      tagPageInfo.value = null
      searched.value = true
      loadPage(1)
    }

    const doTagSearch = () => {
      query.value = ''
      item.value = null
      searched.value = false
      loadPage(1)
    }

    const goTagPage = (page) => loadPage(page)

    // 只加载标签列表，不触发搜索
    onMounted(() => loadPage())

    return { query, item, tagItems, tagPageInfo, genreTags, currentTag, loading, searched, imgProxyUrl, showImg, doSearch, doTagSearch, goTagPage }
  }
}
</script>