<template>
  <div class="container">
    <!-- 影片类型下拉 + 状态 Tab -->
    <div class="row py-3">
      <div class="col-12">
        <ul class="nav nav-tabs">
          <li class="nav-item">
            <a class="nav-link" :class="{ active: like === null }"
               href="#" @click.prevent="switchTab(null)">未打标</a>
          </li>
          <li class="nav-item">
            <a class="nav-link" :class="{ active: like === 1 }"
               href="#" @click.prevent="switchTab(1)">喜欢</a>
          </li>
          <li class="nav-item">
            <a class="nav-link" :class="{ active: like === 0 }"
               href="#" @click.prevent="switchTab(0)">不喜欢</a>
          </li>
          <li class="nav-item ms-auto">
            <select class="form-select form-select-sm" style="width: auto;" v-model="movieType" @change="onTypeChange">
              <option v-for="mt in movieTypes" :key="mt" :value="mt">{{ mt === 'normal' ? '有码' : '无码' }}</option>
            </select>
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

    const switchTab = (lk) => {
      like.value = lk
      loadData(1)
    }

    const onTypeChange = () => {
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

    return { items, pageInfo, like, movieTypes, movieType, imgProxyUrl, showImg, switchTab, onTypeChange, goPage, tag }
  }
}
</script>