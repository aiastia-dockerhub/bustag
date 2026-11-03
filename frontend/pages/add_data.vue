<template>
  <div class="import-layout">
    <section class="surface">
      <h2 class="panel-title">批量添加影片</h2>
      <p class="panel-description">
        输入演员 ID 和/或搜索关键词（可同时填，会合并去重后一起处理），抓取有磁力链接的影片加入资料库。已入库的影片会自动跳过。
      </p>

      <div v-if="jobError" class="alert alert-warning">{{ jobError }}</div>
      <div
        v-for="job in activeJobs"
        :key="job.id"
        class="alert alert-info"
        role="status"
      >
        {{
          job.state === "queued"
            ? "任务排队中"
            : job.progress.stage || "后台处理中"
        }}
        <span v-if="job.progress.processed">
          · 已处理 {{ job.progress.processed }} 条</span
        >
      </div>
      <div v-if="resultMsg" class="alert alert-success" role="status">
        {{ resultMsg }}
      </div>
      <div v-if="jobFailed" class="alert alert-danger" role="alert">
        {{ jobFailed }}
      </div>
      <div v-if="formError" class="alert alert-danger" role="alert">
        {{ formError }}
      </div>

      <form @submit.prevent="directAdd">
        <div class="field-group">
          <label for="batch-stars" class="form-label">演员 ID</label>
          <textarea
            id="batch-stars"
            v-model="stars"
            class="form-control"
            rows="3"
            placeholder="每行一个，如：&#10;qs6"
          ></textarea>
          <p class="field-hint">
            JavBus 演员页网址 /star/qs6 中的 qs6 就是演员 ID
          </p>
        </div>

        <div class="field-group">
          <label for="batch-keywords" class="form-label">搜索关键词</label>
          <textarea
            id="batch-keywords"
            v-model="keywords"
            class="form-control"
            rows="3"
            placeholder="每行一个，如：&#10;三上"
          ></textarea>
        </div>

        <div class="field-row">
          <div class="field-group">
            <span class="form-label">影片类型</span>
            <div class="type-toggle">
              <input
                type="radio"
                class="btn-check"
                name="movieType"
                id="mt-normal"
                value="normal"
                v-model="movieType"
                :disabled="busy"
              />
              <label class="btn btn-outline-secondary" for="mt-normal">有码</label>
              <input
                type="radio"
                class="btn-check"
                name="movieType"
                id="mt-uncensored"
                value="uncensored"
                v-model="movieType"
                :disabled="busy"
              />
              <label class="btn btn-outline-secondary" for="mt-uncensored">无码</label>
            </div>
            <p class="field-hint">无码影片要用 JavBus 无码区的演员 ID 和关键词</p>
          </div>

          <div class="field-group">
            <label for="batch-pages" class="form-label">抓取页数</label>
            <input
              id="batch-pages"
              v-model.number="pages"
              class="form-control pages-input"
              type="number"
              min="1"
              max="30"
              :disabled="busy"
            />
            <p class="field-hint">每个来源抓前 N 页（第 1 页最新），全是旧影片会提前停止</p>
          </div>
        </div>

        <div class="btn-row">
          <button
            type="button"
            class="btn btn-outline-primary"
            @click="preview"
            :disabled="submitting || busy"
          >
            <span
              v-if="previewRunning"
              class="spinner-border spinner-border-sm me-1"
            ></span>
            <AppIcon v-else name="eye" />
            {{ previewRunning ? "预览中…" : "预览候选" }}
          </button>
          <button
            type="submit"
            class="btn btn-primary"
            :disabled="submitting || busy"
          >
            <span
              v-if="addRunning"
              class="spinner-border spinner-border-sm me-1"
            ></span>
            <AppIcon v-else name="download" />
            {{ addRunning ? "抓取中…" : "直接添加" }}
          </button>
        </div>
      </form>

      <!-- ========== 预览结果 ========== -->
      <section v-if="previewDone" class="preview-section">
        <div class="preview-head">
          <h5 class="preview-title-heading">
            预览候选（{{ previewItems.length }}）
          </h5>
          <span v-if="previewSkipped" class="preview-skipped">
            已跳过 {{ previewSkipped }} 个已入库/无效影片
          </span>
        </div>

        <template v-if="previewItems.length">
          <div class="preview-actions">
            <button
              type="button"
              class="btn btn-sm btn-outline-secondary"
              @click="setAllChecked(true)"
            >
              全选
            </button>
            <button
              type="button"
              class="btn btn-sm btn-outline-secondary"
              @click="setAllChecked(false)"
            >
              全不选
            </button>
          </div>
          <ul class="preview-list">
            <li v-for="item in previewItems" :key="item.fanhao">
              <label class="preview-item">
                <input type="checkbox" v-model="item.checked" />
                <img
                  class="preview-cover"
                  :src="imgProxyUrl(item.img, 160, item.url)"
                  loading="lazy"
                  alt=""
                />
                <span class="preview-fanhao">{{ item.fanhao }}</span>
                <span class="preview-item-title text-truncate">{{
                  item.title || "（无标题）"
                }}</span>
                <span class="preview-date">{{ item.date }}</span>
                <span class="badge preview-source">{{ item.source }}</span>
              </label>
            </li>
          </ul>
          <button
            type="button"
            class="btn btn-primary"
            @click="addSelected"
            :disabled="addRunning || selectedCount === 0"
          >
            <span
              v-if="addRunning"
              class="spinner-border spinner-border-sm me-1"
            ></span>
            <AppIcon v-else name="magnet" />
            {{ addRunning ? "抓取中…" : `添加所选（${selectedCount}）` }}
          </button>
        </template>
        <p v-else class="preview-empty">
          没有找到新的候选影片（可能都已入库，或没有磁力链接）
        </p>
      </section>
    </section>

    <aside class="form-guide">
      <span class="guide-icon"><AppIcon name="magnet" /></span>
      <h2>先预览，再入库</h2>
      <p>
        「预览候选」会先抓取影片列表（只保留有磁力链接的，自动滤掉已入库的），勾掉不想要的，再点「添加所选」才真正入库。
      </p>
      <p>
        「直接添加」则跳过预览一步到位。两种方式都在后台进行，完成后会用你的模型自动推荐。
      </p>
      <NuxtLink to="/" class="text-link"
        >前往首页推荐<AppIcon name="right"
      /></NuxtLink>
    </aside>
  </div>
</template>

<script setup>
const stars = ref("");
const keywords = ref("");
const movieType = ref("normal");
const pages = ref(1);
const formError = ref("");
const submitting = ref(false);
const { jobs, active, error: jobError, submit } = useJobs();

const previewJobId = ref("");
const addJobId = ref("");
const activeJobs = computed(() =>
  active.value.filter((job) => ["preview", "download"].includes(job.kind)),
);
const previewJob = computed(() =>
  jobs.value.find((job) => job.id === previewJobId.value),
);
const addJob = computed(() =>
  jobs.value.find((job) => job.id === addJobId.value),
);
const previewRunning = computed(() =>
  previewJob.value
    ? ["queued", "running"].includes(previewJob.value.state)
    : false,
);
const addRunning = computed(() =>
  addJob.value ? ["queued", "running"].includes(addJob.value.state) : false,
);
const busy = computed(() => previewRunning.value || addRunning.value);

// ========== 预览结果 ==========
const previewItems = ref([]);
const previewSkipped = ref(0);
const previewDone = ref(false);
const previewType = ref("normal");
const selectedCount = computed(
  () => previewItems.value.filter((item) => item.checked).length,
);
const setAllChecked = (value) =>
  previewItems.value.forEach((item) => {
    item.checked = value;
  });

watch(
  () => previewJob.value && `${previewJob.value.id}:${previewJob.value.state}`,
  () => {
    const job = previewJob.value;
    if (!job) return;
    if (job.state === "succeeded") {
      const result = job.result || {};
      previewItems.value = (result.movies || []).map((m) => ({
        ...m,
        checked: true,
      }));
      previewSkipped.value = result.skipped || 0;
      previewDone.value = true;
    }
    if (job.state === "failed") formError.value = job.error;
  },
);

// ========== 添加结果 ==========
const resultMsg = computed(() => {
  const job = addJob.value;
  if (!job || job.state !== "succeeded" || !job.result) return "";
  const r = job.result;
  let msg = `批量添加完成，共入库 ${r.saved ?? 0} 部影片`;
  const rec = r.recommendation;
  if (rec && rec.success && rec.total !== undefined) {
    msg += `，已推荐 ${rec.recommended} / ${rec.total} 条`;
  }
  if (r.warning) msg += `（${r.warning}）`;
  return msg;
});
const jobFailed = computed(() =>
  addJob.value?.state === "failed" ? addJob.value.error : "",
);

const validateInput = () => {
  if (!stars.value.trim() && !keywords.value.trim()) {
    formError.value = "请至少输入一个演员 ID 或搜索关键词";
    return false;
  }
  formError.value = "";
  return true;
};

const preview = async () => {
  if (!validateInput()) return;
  submitting.value = true;
  previewDone.value = false;
  previewItems.value = [];
  previewSkipped.value = 0;
  previewType.value = movieType.value;
  try {
    const job = await submit("/api/add_data/preview", {
      stars: stars.value,
      keywords: keywords.value,
      pages: pages.value,
      movie_type: movieType.value,
    });
    previewJobId.value = job.id;
  } catch (e) {
    formError.value = e.data?.error || e.message;
  } finally {
    submitting.value = false;
  }
};

const directAdd = async () => {
  if (!validateInput()) return;
  submitting.value = true;
  try {
    const job = await submit("/api/add_data", {
      stars: stars.value,
      keywords: keywords.value,
      pages: pages.value,
      movie_type: movieType.value,
    });
    addJobId.value = job.id;
  } catch (e) {
    formError.value = e.data?.error || e.message;
  } finally {
    submitting.value = false;
  }
};

const addSelected = async () => {
  const fanhaos = previewItems.value
    .filter((item) => item.checked)
    .map((item) => item.fanhao);
  if (!fanhaos.length) return;
  submitting.value = true;
  try {
    const job = await submit("/api/add_data", {
      fanhaos,
      movie_type: previewType.value,
    });
    addJobId.value = job.id;
  } catch (e) {
    formError.value = e.data?.error || e.message;
  } finally {
    submitting.value = false;
  }
};
</script>

<style scoped>
.field-group {
  margin-bottom: 18px;
}
.field-hint {
  margin-top: 6px;
  font-size: 11px;
  color: var(--muted);
}
.field-row {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
}
.pages-input {
  max-width: 120px;
}
.type-toggle {
  display: flex;
  gap: 0;
}
.type-toggle .btn {
  font-size: 12px;
  padding: 5px 14px;
}
.type-toggle .btn-check:checked + .btn {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}
textarea.form-control {
  resize: vertical;
}
.btn-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.preview-section {
  margin-top: 26px;
  padding-top: 20px;
  border-top: 1px solid var(--line);
}
.preview-head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
}
.preview-title-heading {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
  margin: 0;
}
.preview-skipped {
  font-size: 11px;
  color: var(--muted);
}
.preview-actions {
  display: flex;
  gap: 8px;
  margin: 12px 0;
}
.preview-list {
  list-style: none;
  margin: 0 0 16px;
  padding: 0;
  display: grid;
  gap: 2px;
}
.preview-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 7px 8px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 12px;
}
.preview-item:hover {
  background: var(--surface-soft);
}
.preview-item input {
  flex: 0 0 auto;
  accent-color: var(--accent);
}
.preview-cover {
  width: 64px;
  aspect-ratio: 3 / 2;
  object-fit: cover;
  border-radius: 5px;
  background: #f5f5f5;
  flex: 0 0 auto;
}
.preview-fanhao {
  font-weight: 600;
  color: var(--ink);
  min-width: 90px;
}
.preview-item-title {
  flex: 1;
  min-width: 0;
  color: var(--muted);
}
.preview-date {
  color: var(--faint);
  font-size: 11px;
  flex: 0 0 auto;
}
.preview-source {
  background: var(--accent-soft) !important;
  color: var(--accent) !important;
  font-weight: 500;
  flex: 0 0 auto;
}
.preview-empty {
  font-size: 12px;
  color: var(--muted);
}
@media (max-width: 767px) {
  .preview-date,
  .preview-source {
    display: none;
  }
}
</style>
