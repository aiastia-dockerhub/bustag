<template>
  <div class="container">
    <div class="row py-3">
      <div class="col-12">
        <form @submit.prevent="doSearch" class="d-flex mb-3">
          <input class="form-control me-2" v-model="query" placeholder="输入番号搜索" />
          <button class="btn btn-primary" type="submit">搜索</button>
        </form>

        <!-- 标签云 -->
        <div v-if="genreTags.length > 0 && !query" class="mb-3">
          <h6>标签搜索</h6>
          <span v-for="tag in genreTags" :key="tag" class="badge bg-secondary me-1 mb-1" style="cursor:pointer"
                @click="searchByTag(tag)">{{ tag }}</span>
        </div>

        <!-- 番号搜索结果 -->
        <div v-if="item" class="row py-3 card-item">
          <div class="col-12 col-md-4">
            <img class="img-fluid img-thumbnail coverimg" :src="imgProxyUrl(item.cover_img_url)"
                 @click="showImg(item.cover_img_url)" alt="cover" />
          </div>
          <div class="col-7 col-md-5">
            <div class="small text-muted">发行日期: {{ item.release_date }}</div>
            <h6>{{ item.fanhao }}</h6>
            <a :href="item.url" target="_blank">{{ (item.title || '').substring(0, 30) }}</a>
            <div class="mt-1">
              <span v-for="t in (item.tags_dict?.genre || [])" :key="t" class="badge bg-primary me-1">{{ t }}</span>
            </div>
            <div class="mt-1">
              <span v-for="t in (item.tags_dict?.star || [])" :key="t" class="badge bg-warning text-dark me-1">{{ t }}</span>
            </div>
          </div>
        </div>

        <!-- 标签搜索结果 -->
        <div v-for="tItem in tagItems" :key="tItem.fanhao" class="row py-3 card-item">
          <div class="col-12 col-md-4">
            <img class="img-fluid img-thumbnail coverimg" :src="imgProxyUrl(tItem.cover_img_url)"
                 @click="showImg(tItem.cover_img_url)" alt="cover" loading="lazy" />
          </div>
          <div class="col-7 col-md-5">
            <div class="small text-muted">发行日期: {{ tItem.release_date }}</div>
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

        <Pagination v-if="tagPageInfo" :pageInfo="tagPageInfo" @go-page="goTagPage" />
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
    const showImage = inject('showImage')

    const showImg = (url) => showImage(imgProxyUrl(url))

    const loadPage = async () => {
      try {
        const res = await getSearch({ q: query.value, tag: currentTag.value })
        item.value = res.data.item
        tagItems.value = res.data.tag_items
        tagPageInfo.value = res.data.page_info
        genreTags.value = res.data.genre_tags
      } catch (e) {
        console.error('搜索失败:', e)
      }
    }

    const doSearch = () => {
      currentTag.value = ''
      tagItems.value = []
      tagPageInfo.value = null
      loadPage()
    }

    const searchByTag = (tag) => {
      query.value = ''
      currentTag.value = tag
      item.value = null
      loadPage()
    }

    const goTagPage = (page) => {
      loadPage()
    }

    onMounted(() => loadPage())

    return { query, item, tagItems, tagPageInfo, genreTags, imgProxyUrl, showImg, doSearch, searchByTag, goTagPage }
  }
}
</script>