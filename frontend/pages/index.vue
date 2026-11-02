<template>
  <div class="library-page">
    <section class="overview-strip" aria-label="推荐概况">
      <div>
        <span>当前推荐</span
        ><strong>{{ pageInfo?.total_items || 0 }}<small> 部</small></strong>
      </div>
      <div>
        <span>今日新增</span
        ><strong>{{ todayUpdate }}<small> 部</small></strong>
      </div>
      <div>
        <span>今日推荐</span
        ><strong>{{ todayRecommend }}<small> 部</small></strong>
      </div>
      <p><AppIcon name="discover" />根据你的打标偏好，为你挑选。</p>
    </section>
    <div class="library-toolbar">
      <div class="segmented-control" aria-label="推荐偏好">
        <button
          :class="{ active: like === 1 }"
          :aria-pressed="like === 1"
          @click="switchLike(1)"
        >
          喜欢的影片
        </button>
        <button
          :class="{ active: like === 0 }"
          :aria-pressed="like === 0"
          @click="switchLike(0)"
        >
          不喜欢的影片
        </button>
      </div>
      <label class="type-filter"
        >影片类型<select
          class="form-select"
          v-model="movieType"
          @change="onTypeChange"
        >
          <option v-for="mt in movieTypes" :key="mt" :value="mt">
            {{ mt === "normal" ? "有码" : "无码" }}
          </option>
        </select></label
      >
    </div>
    <div class="list-caption">
      <span>{{ pageInfo?.total_items || 0 }} 部影片</span
      ><span v-if="loading" role="status">正在更新…</span
      ><span v-else><AppIcon name="clock" />最新加入优先</span>
    </div>
    <div class="movie-list" :aria-busy="loading">
      <MovieCard
        v-for="(item, index) in items"
        :key="item.fanhao"
        :item="item"
        :priority="index === 0"
        mode="feedback"
        :busy="!!ratingBusy[item.fanhao]"
        @rate="(fanhao, value) => correct(fanhao, value === 1)"
      />
    </div>
    <EmptyState
      v-if="!items.length && !loading"
      title="还没有这类推荐"
      description="先记录一些喜欢与不喜欢的影片，再训练模型，开启你的专属推荐。"
      icon="discover"
      ><NuxtLink to="/tagit" class="btn btn-primary"
        >开始打标<AppIcon name="right" /></NuxtLink
    ></EmptyState>
    <Pagination :pageInfo="pageInfo" @go-page="goPage" />
  </div>
</template>

<script setup>
const ratingBusy = ref({});
const { notify } = useNotifications();

const items = ref([]);
const pageInfo = ref(null);
const like = ref(1);
const movieTypes = ref(["normal"]);
const movieType = ref("normal");
const loading = ref(false);
const todayUpdate = ref(0);
const todayRecommend = ref(0);

const applyResponse = (res) => {
  items.value = res.items;
  pageInfo.value = res.page_info;
  movieTypes.value = res.movie_types;
  movieType.value = res.movie_type;
  if (res.page_info?.current_page === 1) {
    todayUpdate.value = res.today_update || 0;
    todayRecommend.value = res.today_recommend || 0;
  }
};

let listController;
onBeforeUnmount(() => listController?.abort());

const loadData = async (page = 1, bustCache = false) => {
  loading.value = true;
  listController?.abort();
  listController = new AbortController();
  try {
    const params = { like: like.value, page, type: movieType.value };
    if (bustCache) params._t = Date.now();
    const res = await $fetch("/api/index", {
      params,
      signal: listController.signal,
    });
    applyResponse(res);
  } catch (e) {
    if (e.name === "AbortError") return;
    handle401(e);
    console.error("加载推荐失败:", e);
  } finally {
    loading.value = false;
  }
};

const switchLike = (lk) => {
  like.value = lk;
  loadData(1);
};

const onTypeChange = () => loadData(1);
const goPage = (page) => loadData(page);

const correct = async (fanhao, isCorrect) => {
  if (ratingBusy.value[fanhao]) return;
  ratingBusy.value[fanhao] = true;
  try {
    await $fetch(`/api/correct/${fanhao}`, {
      method: "POST",
      body: { is_correct: isCorrect },
    });
    const page = pageInfo.value?.current_page || 1;
    await loadData(page, true);
  } catch (e) {
    if (!handle401(e))
      notify("error", `${fanhao} · 操作失败：${e.data?.error || e.message}`);
  } finally {
    ratingBusy.value[fanhao] = false;
  }
};

const { data: initial } = await useFetch("/api/index", {
  params: { page: 1, type: movieType.value, like: like.value },
});
if (initial.value) applyResponse(initial.value);
</script>
