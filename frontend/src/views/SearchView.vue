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
            <select class="form-control" v-model="currentTagId">
              <option value="">-- 选择标签类型 --</option>
              <option v-for="tag in genreTags" :key="tag.id" :value="tag.id">{{ tag.value }}</option>
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
    const currentTagId = ref('')
    const currentTag = ref('')
    const loading = ref(false)
    const searched = ref(false)
    const showImage = inject('showImage')

    const showImg = (url) => showImage(imgProxyUrl(url))

    // 加载标签列表（不触发搜索）
    const loadGenreTags = async () => {
      if (genreTags.value.length > 0) return
      try {
        const res = await getSearch({ page: 1 })
        genreTags.value = res.data.genre_tags || []
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
        const res = await getSearch({ q: query.value, page: 1 })
        item.value = res.data.item
        genreTags.value = res.data.genre_tags || genreTags.value
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
        const res = await getSearch({ tag_id: currentTagId.value, page: 1 })
        tagItems.value = res.data.tag_items || []
        tagPageInfo.value = res.data.page_info
        currentTag.value = res.data.tag_value || ''
        genreTags.value = res.data.genre_tags || genreTags.value
      } catch (e) {
        console.error('搜索失败:', e)
      } finally {
        loading.value = false
      }
    }

    const goTagPage = async (page) => {
      loading.value = true
      try {
        const res = await getSearch({ tag_id: currentTagId.value, page })
        tagItems.value = res.data.tag_items || []
        tagPageInfo.value = res.data.page_info
      } catch (e) {
        console.error('搜索失败:', e)
      } finally {
        loading.value = false
      }
    }

    // 页面挂载只加载标签列表
    onMounted(() => loadGenreTags())

    return { query, item, tagItems, tagPageInfo, genreTags, currentTagId, currentTag, loading, searched, imgProxyUrl, showImg, doSearch, doTagSearch, goTagPage }
  }
}
</script>