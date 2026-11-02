<template>
  <div class="library-page">
    <div class="library-toolbar">
      <div class="segmented-control" aria-label="打标状态">
        <button
          :class="{ active: like === null }"
          :aria-pressed="like === null"
          @click="switchTab(null)"
        >
          未打标
        </button>
        <button
          :class="{ active: like === 1 }"
          :aria-pressed="like === 1"
          @click="switchTab(1)"
        >
          喜欢
        </button>
        <button
          :class="{ active: like === 0 }"
          :aria-pressed="like === 0"
          @click="switchTab(0)"
        >
          不喜欢
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
      ><span>每一次打标，都在完善你的偏好</span>
    </div>
    <div class="movie-list">
      <MovieCard
        v-for="(item, index) in items"
        :key="item.fanhao"
        :item="item"
        :priority="index === 0"
        :status-label="
          like === null ? '待打标' : like === 1 ? '已喜欢' : '不喜欢'
        "
        mode="tag"
        :busy="!!ratingBusy[item.fanhao]"
        @rate="tag"
      />
    </div>
    <EmptyState
      v-if="!items.length"
      title="这一栏暂时没有影片"
      description="切换打标状态或影片类型，看看其他内容。"
      icon="tag"
    />
    <Pagination :pageInfo="pageInfo" @go-page="goPage" />
  </div>
</template>

<script setup>
const ratingBusy = ref({});
const { notify } = useNotifications();

const items = ref([]);
const pageInfo = ref(null);
const like = ref(null);
const movieTypes = ref(["normal"]);
const movieType = ref("normal");

const applyResponse = (res) => {
  items.value = res.items;
  pageInfo.value = res.page_info;
  movieTypes.value = res.movie_types;
  movieType.value = res.movie_type;
};

let listController;
onBeforeUnmount(() => listController?.abort());

const loadData = async (page = 1) => {
  listController?.abort();
  listController = new AbortController();
  try {
    const params = { page, type: movieType.value };
    if (like.value !== null) params.like = like.value;
    const res = await $fetch("/api/tagit", {
      params,
      signal: listController.signal,
    });
    applyResponse(res);
  } catch (e) {
    if (e.name === "AbortError") return;
    handle401(e);
    console.error("加载打标数据失败:", e);
  }
};

const switchTab = (lk) => {
  like.value = lk;
  loadData(1);
};

const onTypeChange = () => loadData(1);
const goPage = (page) => loadData(page);

const tag = async (fanhao, rateValue) => {
  if (ratingBusy.value[fanhao]) return;
  ratingBusy.value[fanhao] = true;
  try {
    await $fetch(`/api/tag/${fanhao}`, {
      method: "POST",
      body: { rate_value: rateValue },
    });
    const page = pageInfo.value?.current_page || 1;
    await loadData(page);
  } catch (e) {
    if (!handle401(e))
      notify("error", `${fanhao} · 操作失败：${e.data?.error || e.message}`);
  } finally {
    ratingBusy.value[fanhao] = false;
  }
};

const { data: initial } = await useFetch("/api/tagit", {
  params: { page: 1, type: movieType.value },
});
if (initial.value) applyResponse(initial.value);
</script>
