<template>
  <div class="container">
    <!-- 影片类型 + 喜欢筛选 Tab -->
    <div class="row py-3">
      <div class="col-12">
        <ul class="nav nav-tabs flex-nowrap overflow-auto">
          <li class="nav-item" v-for="mt in movieTypes" :key="mt + '-all'">
            <a class="nav-link" :class="{ active: movieType === mt && like === null }"
               href="#" @click.prevent="switchTab(mt, null)">{{ mt === 'normal' ? '有码' : '无码' }}全部</a>
          </li>
          <li class="nav-item" v-for="mt in movieTypes" :key="mt + '-like'">
            <a class="nav-link" :class="{ active: movieType === mt && like === 1 }"
               href="#" @click.prevent="switchTab(mt, 1)">{{ mt === 'normal' ? '有码' : '无码' }}喜欢</a>
          </li>
          <li class="nav-item" v-for="mt in movieTypes" :key="mt + '-dislike'">
            <a class="nav-link" :class="{ active: movieType === mt && like === 0 }"
               href="#" @click.prevent="switchTab(mt, 0)">{{ mt === 'normal' ? '有码' : '无码' }}不喜欢</a>
          </li>
        </ul>
      </div>
    </div>

    <div v-for="item in items" :key="item.fanhao" class="row py-3 card-item">
      <div class="col-12 col-md-4">
        <img class="img-fluid img-thumbnail coverimg" :src="imgProxyUrl(item.cover_img_url)"
             @click="showImg(item.cover_img_url)" alt="cover" loading="lazy" />
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
      <div class="col-5 col-md-3 d-flex align-self-center justify-content-center">
        <button class="btn btn-success mx-1" @click="tag(item.fanhao, 1)">喜欢</button>
        <button class="btn btn-danger" @click="tag(item.fanhao, 0)">不喜欢</button>
      </div>
    </div>

    <Pagination :pageInfo="pageInfo" @go-page="goPage" />
  </div>
</template>

<script>
import { ref, onMounted, inject } from 'vue'
import { getTagit, postTag, imgProxyUrl } from '../assets/api.js'
import Pagination from '../components/Pagination.vue'

export default {
  components: { Pagination },
  setup() {
    const items = ref([])
    const pageInfo = ref(null)
    const like = ref(null)
    const movieTypes = ref(['normal'])
    const movieType = ref('normal')
    const showImage = inject('showImage')

    const showImg = (url) => showImage(imgProxyUrl(url))

    const loadData = async (page = 1) => {
      try {
        const params = { page, type: movieType.value }
        if (like.value !== null) params.like = like.value
        const res = await getTagit(params)
        items.value = res.data.items
        pageInfo.value = res.data.page_info
        movieTypes.value = res.data.movie_types
        movieType.value = res.data.movie_type
      } catch (e) {
        console.error('加载打标失败:', e)
      }
    }

    const switchTab = (mt, lk) => {
      movieType.value = mt
      like.value = lk
      loadData(1)
    }

    const goPage = (page) => loadData(page)

    const tag = async (fanhao, rateValue) => {
      try {
        await postTag(fanhao, { rate_value: rateValue })
        loadData(pageInfo.value?.current_page || 1)
      } catch (e) {
        console.error('打标失败:', e)
      }
    }

    onMounted(() => loadData())

    return { items, pageInfo, like, movieTypes, movieType, imgProxyUrl, showImg, switchTab, goPage, tag }
  }
}
</script>