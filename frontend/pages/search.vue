<template>
  <div class="library-page">
    <section class="search-panel surface" aria-label="搜索条件">
      <form @submit.prevent="doSearch" class="number-search">
        <label for="movie-query">番号搜索</label>
        <div class="search-input-wrap">
          <AppIcon name="search" /><input
            id="movie-query"
            class="form-control"
            v-model="query"
            placeholder="输入番号，如 SSIS-001"
          /><button class="btn btn-primary" type="submit" :disabled="loading">
            搜索
          </button>
        </div>
      </form>
      <div class="search-divider"><span>或按资料筛选</span></div>
      <div class="search-filters">
        <form @submit.prevent="doTagSearch">
          <label for="genre-filter">类型标签</label>
          <div class="input-group">
            <select
              id="genre-filter"
              class="form-select"
              v-model="currentTagId"
            >
              <option value="">选择类型标签</option>
              <option v-for="tag in genreTags" :key="tag.id" :value="tag.id">
                {{ tag.value }}
              </option></select
            ><button
              class="btn btn-quiet"
              type="submit"
              :disabled="!currentTagId || loading"
            >
              搜索
            </button>
          </div>
        </form>
        <form @submit.prevent="doStarSearch">
          <label for="star-filter">演员</label>
          <div class="input-group">
            <select
              id="star-filter"
              class="form-select"
              v-model="currentStarId"
            >
              <option value="">选择演员</option>
              <option v-for="star in starTags" :key="star.id" :value="star.id">
                {{ star.value }}
              </option></select
            ><button
              class="btn btn-quiet"
              type="submit"
              :disabled="!currentStarId || loading"
            >
              搜索
            </button>
          </div>
        </form>
        <div>
          <label for="rate-filter">评分状态</label
          ><select
            id="rate-filter"
            class="form-select"
            v-model="rateFilter"
            @change="applyRateFilter"
          >
            <option value="">全部状态</option>
            <option value="liked">喜欢</option>
            <option value="disliked">不喜欢</option>
            <option value="recommended">系统推荐</option>
            <option value="unrated">未打标</option>
          </select>
        </div>
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
          ? '试试其他番号、类型或演员，或者调整评分筛选。'
          : '输入番号直接查找，也可以通过类型和演员探索你的资料库。'
      "
      icon="search"
    />
  </div>
</template>

<script setup>
const ratingBusy = ref({});
const { notify } = useNotifications();

const query = ref("");
const item = ref(null);
const tagItems = ref([]);
const tagPageInfo = ref(null);
const genreTags = ref([]);
const starTags = ref([]);
const currentTagId = ref("");
const currentStarId = ref("");
const currentTag = ref("");
const loading = ref(false);
const searched = ref(false);
const rateFilter = ref("");

// 构建带评分筛选的搜索参数
const _buildParams = (base = {}) => {
  if (rateFilter.value) {
    base.rate_filter = rateFilter.value;
  }
  return base;
};

// 评分筛选变更时，重新执行当前搜索
const applyRateFilter = async () => {
  if (searchType.value === "tag" && currentTagId.value) {
    await doTagSearch();
  } else if (searchType.value === "star" && currentStarId.value) {
    await doStarSearch();
  }
};

// 当前列表搜索类型: '' = 无, 'tag' = 标签, 'star' = 女优
const searchType = ref("");

const doSearch = async () => {
  if (!query.value.trim()) return;
  currentTagId.value = "";
  currentStarId.value = "";
  currentTag.value = "";
  searchType.value = "";
  tagItems.value = [];
  tagPageInfo.value = null;
  searched.value = true;
  loading.value = true;
  try {
    const res = await $fetch("/api/search", {
      params: _buildParams({ q: query.value, page: 1 }),
    });
    item.value = res.item;
    // 精确未命中时，展示后端模糊匹配到的多条结果
    if (!res.item && res.tag_items && res.tag_items.length > 0) {
      tagItems.value = res.tag_items;
      tagPageInfo.value = res.page_info || null;
      currentTag.value = query.value;
      searchType.value = "fanhao";
      searched.value = false;
    }
    genreTags.value = res.genre_tags || genreTags.value;
    starTags.value = res.star_tags || starTags.value;
  } catch (e) {
    console.error("搜索失败:", e);
  } finally {
    loading.value = false;
  }
};

const doTagSearch = async () => {
  if (!currentTagId.value) return;
  query.value = "";
  currentStarId.value = "";
  item.value = null;
  searched.value = false;
  searchType.value = "tag";
  loading.value = true;
  try {
    const res = await $fetch("/api/search", {
      params: _buildParams({ tag_id: currentTagId.value, page: 1 }),
    });
    tagItems.value = res.tag_items || [];
    tagPageInfo.value = res.page_info;
    currentTag.value = res.tag_value || "";
    genreTags.value = res.genre_tags || genreTags.value;
    starTags.value = res.star_tags || starTags.value;
  } catch (e) {
    console.error("搜索失败:", e);
  } finally {
    loading.value = false;
  }
};

const doStarSearch = async () => {
  if (!currentStarId.value) return;
  query.value = "";
  currentTagId.value = "";
  item.value = null;
  searched.value = false;
  searchType.value = "star";
  loading.value = true;
  try {
    const res = await $fetch("/api/search", {
      params: _buildParams({ star_id: currentStarId.value, page: 1 }),
    });
    tagItems.value = res.tag_items || [];
    tagPageInfo.value = res.page_info;
    currentTag.value = res.tag_value || "";
    genreTags.value = res.genre_tags || genreTags.value;
    starTags.value = res.star_tags || starTags.value;
  } catch (e) {
    console.error("搜索失败:", e);
  } finally {
    loading.value = false;
  }
};

const goTagPage = async (page) => {
  loading.value = true;
  try {
    const params = _buildParams({ page });
    if (searchType.value === "star") {
      params.star_id = currentStarId.value;
    } else {
      params.tag_id = currentTagId.value;
    }
    const res = await $fetch("/api/search", { params });
    tagItems.value = res.tag_items || [];
    tagPageInfo.value = res.page_info;
  } catch (e) {
    console.error("搜索失败:", e);
  } finally {
    loading.value = false;
  }
};

const refreshTagResults = async () => {
  const page = tagPageInfo.value?.current_page || 1;
  const params = _buildParams({ page });
  if (searchType.value === "star") {
    params.star_id = currentStarId.value;
  } else {
    params.tag_id = currentTagId.value;
  }
  const res = await $fetch("/api/search", { params });
  tagItems.value = res.tag_items || [];
  tagPageInfo.value = res.page_info;
};

const tagItem = async (fanhao, rateValue) => {
  if (ratingBusy.value[fanhao]) return;
  ratingBusy.value[fanhao] = true;
  try {
    await $fetch(`/api/tag/${fanhao}`, {
      method: "POST",
      body: { rate_value: rateValue },
    });
    // 刷新当前搜索结果以更新打标状态
    if (item.value && item.value.fanhao === fanhao && query.value) {
      // 番号精确搜索结果：重新搜索
      const res = await $fetch("/api/search", {
        params: _buildParams({ q: query.value, page: 1 }),
      });
      item.value = res.item;
    } else if (searchType.value === "fanhao" && query.value) {
      // 番号模糊搜索结果：重新模糊搜索刷新列表
      const res = await $fetch("/api/search", {
        params: _buildParams({ q: query.value, page: 1 }),
      });
      tagItems.value = res.tag_items || [];
      tagPageInfo.value = res.page_info || null;
    } else if (searchType.value) {
      // 标签/女优搜索结果：刷新当前页
      await refreshTagResults();
    }
  } catch (e) {
    if (!handle401(e))
      notify("error", `${fanhao} · 操作失败：${e.data?.error || e.message}`);
  } finally {
    ratingBusy.value[fanhao] = false;
  }
};

const { data: dictionary } = await useFetch("/api/tags", {
  key: "search-tags",
});
if (dictionary.value) {
  genreTags.value = dictionary.value.genre_tags;
  starTags.value = dictionary.value.star_tags;
}
</script>
