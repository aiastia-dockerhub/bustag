<template>
  <div class="container">
    <div class="row py-3">
      <div class="col-12">
        <ul class="nav nav-tabs">
          <li class="nav-item">
            <router-link class="nav-link active" to="/local">本地文件</router-link>
          </li>
          <li class="nav-item">
            <router-link class="nav-link" to="/local_fanhao">上传番号</router-link>
          </li>
        </ul>
      </div>
    </div>

    <div v-for="localItem in items" :key="localItem.id" class="row py-3 card-item">
      <div class="col-12 col-md-4">
        <img class="img-fluid img-thumbnail coverimg" :src="imgProxyUrl(localItem.item.cover_img_url)"
             @click="showImg(localItem.item.cover_img_url)" alt="cover" loading="lazy" />
      </div>
      <div class="col-7 col-md-5">
        <div class="small text-muted">发行日期: {{ localItem.item.release_date }}</div>
        <div class="small text-muted">上次观看: {{ localItem.last_view_date }}</div>
        <div class="small text-muted">观看次数: {{ localItem.view_times }}</div>
        <h6>{{ localItem.item.fanhao }}</h6>
        <a :href="localItem.item.url" target="_blank">{{ (localItem.item.title || '').substring(0, 30) }}</a>
        <div class="mt-1">
          <span v-for="t in (localItem.item.tags_dict?.genre || [])" :key="t" class="badge bg-primary me-1">{{ t }}</span>
        </div>
        <div class="mt-1">
          <span v-for="t in (localItem.item.tags_dict?.star || [])" :key="t" class="badge bg-warning text-dark me-1">{{ t }}</span>
        </div>
      </div>
      <div class="col-5 col-md-3 d-flex align-self-center justify-content-center">
        <a class="btn btn-primary" :href="'/api/local_play/' + localItem.id" target="_blank" role="button">播放</a>
      </div>
    </div>

    <Pagination :pageInfo="pageInfo" @go-page="goPage" />
  </div>
</template>

<script>
import { ref, onMounted, inject } from 'vue'
import { getLocal, imgProxyUrl } from '../assets/api.js'
import Pagination from '../components/Pagination.vue'

export default {
  components: { Pagination },
  setup() {
    const items = ref([])
    const pageInfo = ref(null)
    const showImage = inject('showImage')

    const showImg = (url) => showImage(imgProxyUrl(url))

    const loadData = async (page = 1) => {
      try {
        const res = await getLocal({ page })
        items.value = res.data.items
        pageInfo.value = res.data.page_info
      } catch (e) {
        console.error('加载本地文件失败:', e)
      }
    }

    const goPage = (page) => loadData(page)

    onMounted(() => loadData())

    return { items, pageInfo, imgProxyUrl, showImg, goPage }
  }
}
</script>