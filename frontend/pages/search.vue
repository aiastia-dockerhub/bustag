<template>
  <div class="library-page">
    <section class="search-panel surface" aria-label="搜索条件">
      <form @submit.prevent="doSearch" class="number-search">
        <label for="movie-query">番号 / 名称搜索</label>
        <div class="search-input-wrap">
          <AppIcon name="search" /><input
            id="movie-query"
            class="form-control"
            v-model="query"
            placeholder="输入番号或影片名称，如 SSIS-001"
          /><button class="btn btn-primary" type="submit" :disabled="loading">
            搜索
          </button>
        </div>
      </form>
      <div class="search-divider"><span>或按资料筛选</span></div>
      <div class="search-filters">
        <SearchSelect id="genre-filter" v-model="currentTagId" label="类型标签"
          placeholder="输入关键词查找类型" :options="genreTags" :disabled="loading" @select="doTagSearch" />
        <SearchSelect id="star-filter" v-model="currentStarId" label="演员"
          placeholder="输入名字查找演员" :options="starTags" :disabled="loading" @select="doStarSearch" />
        <fieldset class="rating-filter">
          <legend>评分状态</legend>
          <div class="rating-filter-options">
            <button v-for="option in rateOptions" :key="option.value" type="button"
              :aria-pressed="rateFilter === option.value" :disabled="loading"
              @click="rateFilter = option.value; applyRateFilter()">{{ option.label }}</button>
          </div>
        </fieldset>
      </div>
    </section>
    <div v-if="item || tagItems.length" class="list-caption">
      <span
        >{{ currentTag ? `“${currentTag}”` : "搜索结果" }} ·
        {{
          item ? 1 : tagPageInfo?.total_items || tagItems.length
        }}
        部影片</span
      ><span v-if="loading" role="status">正在搜索…</span>
    </div>
    <div class="movie-list" :aria-busy="loading">
      <MovieCard
        v-if="item"
        :item="item"
        priority
        mode="tag"
        :busy="!!ratingBusy[item.fanhao]"
        @rate="tagItem"
      />
      <MovieCard
        v-for="(tItem, index) in tagItems"
        :key="tItem.fanhao"
        :item="tItem"
        :priority="index === 0"
        mode="tag"
        :busy="!!ratingBusy[tItem.fanhao]"
        @rate="tagItem"
      />
    </div>
    <Pagination
      v-if="tagPageInfo"
      :pageInfo="tagPageInfo"
      @go-page="goTagPage"
    />
    <EmptyState
      v-if="!loading && !item && !tagItems.length"
      :title="searched || currentTag ? '没有找到匹配的影片' : '从一次搜索开始'"
      :description="
        searched || currentTag
          ? '试试其他番号、名称、类型或演员，或者调整评分筛选。'
          : '输入番号或影片名称直接查找，也可以通过类型和演员探索你的资料库。'
      "
      icon="search"
    />
  </div>
</template>

<script setup>
const { notify } = useNotifications();
const ratingBusy = ref({});
const query = ref("");
const item = ref(null);
const tagItems = ref([]);
const tagPageInfo = ref(null);
const currentTagId = ref("");
const currentStarId = ref("");
const currentTag = ref("");
const loading = ref(false);
const searched = ref(false);
const rateFilter = ref("");
const rateOptions = [
  { value: "", label: "全部状态" }, { value: "liked", label: "喜欢" },
  { value: "disliked", label: "不喜欢" }, { value: "recommended", label: "系统推荐" },
  { value: "unrated", label: "未打标" },
];
// Keep the submitted search separate from edits in the controls.
const activeSearch = ref(null);
const searchResults = async (page = 1) => {
  if (!activeSearch.value || loading.value) return;
  loading.value = true;
  try {
    const res = await $fetch("/api/search", {
      params: { ...activeSearch.value, page, rate_filter: rateFilter.value },
    });
    item.value = res.item || null;
    tagItems.value = res.tag_items || [];
    tagPageInfo.value = res.page_info || null;
    currentTag.value = res.tag_value || activeSearch.value.q || "";
    searched.value = true;
  } catch (e) {
    if (!handle401(e)) notify("error", `搜索失败：${e.data?.error || e.message}`);
  } finally {
    loading.value = false;
  }
};
const doSearch = () => {
  if (!query.value.trim() || loading.value) return;
  activeSearch.value = { q: query.value.trim() };
  currentTagId.value = "";
  currentStarId.value = "";
  return searchResults();
};
const doTagSearch = () => {
  if (!currentTagId.value || loading.value) return;
  activeSearch.value = { tag_id: currentTagId.value };
  query.value = "";
  currentStarId.value = "";
  return searchResults();
};
const doStarSearch = () => {
  if (!currentStarId.value || loading.value) return;
  activeSearch.value = { star_id: currentStarId.value };
  query.value = "";
  currentTagId.value = "";
  return searchResults();
};
const applyRateFilter = () => searchResults();
const goTagPage = page => searchResults(page);
const tagItem = async (fanhao, rateValue) => {
  if (ratingBusy.value[fanhao]) return;
  ratingBusy.value[fanhao] = true;
  try {
    await $fetch(`/api/tag/${fanhao}`, { method: "POST", body: { rate_value: rateValue } });
    await searchResults(tagPageInfo.value?.current_page || 1);
  } catch (e) {
    if (!handle401(e)) notify("error", `${fanhao} · 操作失败：${e.data?.error || e.message}`);
  } finally {
    ratingBusy.value[fanhao] = false;
  }
};
const { data: dictionary } = await useFetch("/api/tags", { key: "search-tags" });
const genreTags = computed(() => dictionary.value?.genre_tags || []);
const starTags = computed(() => dictionary.value?.star_tags || []);
</script>
