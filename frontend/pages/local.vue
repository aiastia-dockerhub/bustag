<template>
  <div class="library-page">
    <div class="library-toolbar">
      <div class="segmented-control">
        <NuxtLink to="/local" class="active">本地文件</NuxtLink
        ><NuxtLink to="/local_fanhao">添加收藏</NuxtLink>
      </div>
      <NuxtLink to="/local_fanhao" class="btn btn-primary"
        ><AppIcon name="upload" />添加番号</NuxtLink
      >
    </div>
    <div class="list-caption">
      <span>{{ pageInfo?.total_items || 0 }} 部本地影片</span
      ><span>收藏与观看记录</span>
    </div>
    <div class="movie-list">
      <MovieCard
        v-for="(localItem, index) in items"
        :key="localItem.id"
        :item="localItem.item"
        :local="localItem"
        :priority="index === 0"
      />
    </div>
    <EmptyState
      v-if="!items.length"
      title="收藏，从喜欢的一部开始"
      description="添加番号与本地文件路径，在这里整理和播放你的收藏。"
      icon="folder"
      ><NuxtLink to="/local_fanhao" class="btn btn-primary"
        >添加收藏<AppIcon name="right" /></NuxtLink
    ></EmptyState>
    <Pagination :pageInfo="pageInfo" @go-page="goPage" />
  </div>
</template>

<script setup>
const items = ref([]);
const pageInfo = ref(null);

const applyResponse = (res) => {
  items.value = res.items;
  pageInfo.value = res.page_info;
};

let listController;
onBeforeUnmount(() => listController?.abort());

const loadData = async (page = 1) => {
  listController?.abort();
  listController = new AbortController();
  try {
    const res = await $fetch("/api/local", {
      params: { page },
      signal: listController.signal,
    });
    applyResponse(res);
  } catch (e) {
    if (e.name === "AbortError") return;
    handle401(e);
    console.error("加载本地文件失败:", e);
  }
};

const goPage = (page) => loadData(page);

const { data: initial } = await useFetch("/api/local", { params: { page: 1 } });
if (initial.value) applyResponse(initial.value);
</script>
