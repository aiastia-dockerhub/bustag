<template>
  <nav
    v-if="pageInfo && pageInfo.max_page > 0"
    class="library-pagination"
    aria-label="影片分页"
  >
    <span class="pagination-summary">共 {{ pageInfo.total_items }} 部影片</span>
    <div class="pagination-controls">
      <button
        class="btn btn-quiet"
        :disabled="pageInfo.current_page <= 1"
        @click="goPage(pageInfo.current_page - 1)"
        aria-label="上一页"
      >
        <AppIcon name="left" />
      </button>
      <span
        ><strong>{{ pageInfo.current_page }}</strong
        ><span class="pagination-divider">/</span>{{ pageInfo.max_page }}</span
      >
      <button
        class="btn btn-quiet"
        :disabled="pageInfo.current_page >= pageInfo.max_page"
        @click="goPage(pageInfo.current_page + 1)"
        aria-label="下一页"
      >
        <AppIcon name="right" />
      </button>
    </div>
    <label class="pagination-jump"
      >跳至<input
        type="number"
        class="form-control"
        aria-label="跳转页码"
        min="1"
        :max="pageInfo.max_page"
        :value="pageInfo.current_page"
        @change="goPage($event.target.value)"
      />页</label
    >
  </nav>
</template>
<script setup>
const props = defineProps({ pageInfo: Object });
const emit = defineEmits(["go-page"]);
const goPage = (value) => {
  const number = Number(value);
  if (!Number.isFinite(number)) return;
  const page = Math.max(
    1,
    Math.min(props.pageInfo.max_page, Math.trunc(number)),
  );
  if (page === props.pageInfo.current_page) return;
  window.scrollTo({ top: 0, behavior: "smooth" });
  emit("go-page", page);
};
</script>
