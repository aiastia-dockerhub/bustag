<template>
  <div class="model-container">
    <div class="model-page">
      <div v-if="jobError" class="alert alert-warning">{{ jobError }}</div>
      <div
        v-for="job in active"
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

      <!-- ========== 训练模型 ========== -->
      <section class="card-section model-control">
        <div class="section-head">
          <span class="section-icon"><AppIcon name="model" /></span>
          <div>
            <h5 class="section-title mb-0">重新训练模型</h5>
            <p class="section-desc mb-0">
              将新的打标记录融入模型，更新你的专属推荐。
            </p>
          </div>
        </div>

        <div class="section-body">
          <button
            class="btn btn-primary px-4"
            @click="trainModel"
            :disabled="busy"
          >
            <span
              v-if="training"
              class="spinner-border spinner-border-sm me-1"
            ></span>
            {{ training ? "训练中…" : "开始训练" }}
          </button>

          <label class="model-evaluation">
            <input type="checkbox" v-model="fullEvaluation" :disabled="busy" />
            完整评估（含 5 折交叉验证）
          </label>
          <transition name="fade">
            <div
              v-if="error"
              class="alert alert-danger mt-3 mb-0 d-flex align-items-center"
            >
              <span class="me-2">⚠️</span>
              <span>{{ error }}</span>
            </div>
          </transition>

          <transition name="fade">
            <div v-if="training" class="training-hint mt-3">
              <span
                class="spinner-border spinner-border-sm text-primary me-2"
              ></span>
              <span class="text-muted"
                >正在训练中，可能需要几十秒，请稍候...</span
              >
            </div>
          </transition>
        </div>
      </section>

      <!-- ========== 推荐数据管理 ========== -->
      <section class="card-section model-control">
        <div class="section-head">
          <span class="section-icon"><AppIcon name="refresh" /></span>
          <div>
            <h5 class="section-title mb-0">推荐数据管理</h5>
            <p class="section-desc mb-0">
              训练后可以重新推荐，让已有影片也应用新的偏好。
              <span class="text-warning-emphasis fw-semibold"
                >用户打标记录始终保留。</span
              >
            </p>
          </div>
        </div>

        <div class="section-body">
          <div class="btn-row">
            <button
              class="btn btn-outline-warning px-4"
              @click="clearRecommend"
              :disabled="busy"
            >
              <span
                v-if="recommendBusy"
                class="spinner-border spinner-border-sm me-1"
              ></span>
              清理旧推荐
            </button>
            <button
              class="btn btn-success px-4"
              @click="reRecommend"
              :disabled="busy"
            >
              <span
                v-if="recommendBusy"
                class="spinner-border spinner-border-sm me-1"
              ></span>
              重新推荐
            </button>
          </div>

          <transition name="fade">
            <div
              v-if="recommendResult"
              class="result-box mt-3"
              :class="
                recommendResult.success ? 'result-success' : 'result-error'
              "
            >
              <span class="result-icon">{{
                recommendResult.success ? "✅" : "❌"
              }}</span>
              <span>{{ recommendResultMsg }}</span>
            </div>
          </transition>
        </div>
      </section>

      <!-- ========== 模型数据 ========== -->
      <section class="card-section">
        <div class="section-head">
          <span class="section-icon"><AppIcon name="model" /></span>
          <div>
            <h5 class="section-title mb-0">当前模型数据</h5>
            <p class="section-desc mb-0">模型在测试集上的评估指标</p>
          </div>
        </div>

        <div class="section-body">
          <div v-if="scores">
            <!-- 核心指标卡片 -->
            <div class="metrics-grid mb-4">
              <div class="metric-card metric-precision">
                <div class="metric-value">
                  {{ formatScore(scores.precision) }}
                </div>
                <div class="metric-label">精确率 Precision</div>
                <div class="metric-hint">推荐中真正喜欢的比例</div>
              </div>
              <div class="metric-card metric-recall">
                <div class="metric-value">{{ formatScore(scores.recall) }}</div>
                <div class="metric-label">覆盖率 Recall</div>
                <div class="metric-hint">喜欢中被推荐出来的比例</div>
              </div>
              <div class="metric-card metric-f1">
                <div class="metric-value">{{ formatScore(scores.f1) }}</div>
                <div class="metric-label">综合评分 F1</div>
                <div class="metric-hint">越高越好</div>
              </div>
              <div v-if="scores.auc" class="metric-card metric-auc">
                <div class="metric-value">{{ formatScore(scores.auc) }}</div>
                <div class="metric-label">AUC 区分度</div>
                <div class="metric-hint">越接近 1 越好</div>
              </div>
            </div>

            <!-- 交叉验证 -->
            <div v-if="scores.cv_f1_mean" class="cv-bar mb-4">
              <span class="me-2">5 折交叉验证 F1</span>
              <span class="badge bg-info text-dark fs-6">
                {{ scores.cv_f1_mean }} ± {{ scores.cv_f1_std }}
              </span>
            </div>

            <!-- Top 特征 -->
            <template
              v-if="scores.top_features && scores.top_features.length > 0"
            >
              <h6 class="features-title">
                Top {{ scores.top_features.length }} 重要特征
              </h6>
              <div class="features-list">
                <div
                  v-for="(feat, idx) in scores.top_features"
                  :key="feat.name"
                  class="feature-row"
                >
                  <span class="feature-rank">{{ idx + 1 }}</span>
                  <span class="feature-name text-truncate">{{
                    feat.name
                  }}</span>
                  <div class="feature-bar-wrap">
                    <div
                      class="feature-bar"
                      :style="{ width: featureWidth(feat.importance) }"
                    ></div>
                  </div>
                  <span class="feature-value">{{ feat.importance }}</span>
                </div>
              </div>
            </template>
          </div>

          <div v-else-if="!training" class="empty-state text-center py-4">
            <AppIcon name="model" />
            <p class="text-muted mb-0">
              还没有训练过模型，点击上方"开始训练"。
            </p>
          </div>
        </div>
      </section>

      <details class="model-method surface">
        <summary><AppIcon name="discover" />推荐如何变得更懂你？</summary>
        <div>
          <p>
            在偏好打标页记录喜欢与不喜欢的影片，模型会从类型、演员等信息中学习你的偏好。
          </p>
          <p>
            积累新记录后重新训练，再点击「重新推荐」，即可更新资料库中的推荐结果。完整评估会额外检查模型的稳定性，需要更长时间。
          </p>
        </div>
      </details>
    </div>
  </div>
</template>

<script setup>
const scores = ref(null);
const error = ref("");
const { jobs, active, error: jobError, submit } = useJobs();
const fullEvaluation = ref(false);
const submitting = ref(false);
const busy = computed(() => submitting.value || active.value.length > 0);
const training = computed(() =>
  active.value.some((job) => job.kind === "train"),
);
const recommendBusy = computed(() =>
  active.value.some((job) => ["recommend", "clear"].includes(job.kind)),
);

const loadModel = async () => {
  try {
    const res = await $fetch("/api/model");
    scores.value = res.model_scores;
  } catch (e) {
    handle401(e);
  }
};

const trainModel = async () => {
  submitting.value = true;
  error.value = "";
  try {
    await submit("/api/do-training", { full_evaluation: fullEvaluation.value });
  } catch (e) {
    error.value = e.data?.error || e.message;
  } finally {
    submitting.value = false;
  }
};

// Refresh model metrics on completion, including jobs submitted on another device.
const latest = computed(() =>
  jobs.value.find((job) => ["train", "recommend", "clear"].includes(job.kind)),
);
watch(
  () => latest.value && `${latest.value.id}:${latest.value.state}`,
  async () => {
    const job = latest.value;
    if (job?.state === "failed") error.value = job.error;
    if (job?.state === "succeeded") {
      if (job.kind === "train") await loadModel();
      else recommendResult.value = job.result;
    }
  },
);

// 推荐数据管理
const recommendResult = ref(null);

const recommendResultMsg = computed(() => {
  const r = recommendResult.value;
  if (!r) return "";
  if (!r.success) return "失败：" + (r.error || "未知错误");
  let msg = `已清理 ${r.deleted} 条旧推荐`;
  if (r.total !== undefined) {
    msg += `，重新推荐 ${r.recommended} / ${r.total} 条`;
  }
  if (r.warning) msg += `（${r.warning}）`;
  return msg;
});

const callRecommendApi = async (url, confirmMsg) => {
  if (!confirm(confirmMsg)) return;
  submitting.value = true;
  recommendResult.value = null;
  try {
    await submit(url);
  } catch (e) {
    recommendResult.value = { success: false, error: e.message };
  } finally {
    submitting.value = false;
  }
};

const clearRecommend = () =>
  callRecommendApi(
    "/api/clear-recommend",
    "确认清理所有系统推荐记录？\n用户打标记录始终保留。",
  );

const reRecommend = () =>
  callRecommendApi(
    "/api/re-recommend",
    "确认清理旧推荐并用当前模型重新推荐？\n用户打标记录始终保留。",
  );

// 格式化分数：保留 2 位，无值时 N/A
const formatScore = (v) =>
  v === null || v === undefined || v === "" ? "N/A" : v;

// 计算特征条宽度（相对最大重要性）
const maxImportance = computed(() => {
  const feats = scores.value?.top_features;
  if (!feats || !feats.length) return 1;
  return Math.max(...feats.map((f) => f.importance), 1);
});
const featureWidth = (imp) =>
  Math.max(5, (imp / maxImportance.value) * 100) + "%";

const { data: initial } = await useFetch("/api/model");
if (initial.value) scores.value = initial.value.model_scores;
</script>

<style scoped>
.model-page {
  display: grid;
  gap: 22px;
}
.model-page > .alert,
.card-section,
.model-method {
  grid-column: 1 / -1;
  margin: 0 !important;
}
.card-section {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  overflow: hidden;
}
.section-head {
  display: flex;
  align-items: flex-start;
  gap: 13px;
  padding: 24px 24px 18px;
}
.section-icon {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  background: var(--accent-soft);
  color: var(--accent);
  border-radius: 10px;
  flex: 0 0 auto;
}
.section-title {
  color: var(--ink);
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 8px !important;
}
.section-desc {
  font-size: 12px;
  line-height: 1.8;
  color: var(--muted);
}
.section-body {
  padding: 0 24px 24px;
}
.text-warning-emphasis {
  display: block;
  font-size: 11px;
  font-weight: 400 !important;
  color: var(--muted) !important;
}
.model-evaluation {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  font-size: 11px;
  color: var(--muted);
}
.model-evaluation input {
  accent-color: var(--accent);
}
.btn-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.result-box {
  padding: 12px;
  border-radius: 8px;
  margin-top: 16px;
  display: flex;
  gap: 8px;
  font-size: 12px;
  line-height: 1.7;
}
.result-success {
  color: var(--accent);
  background: var(--accent-soft);
}
.result-error {
  color: var(--danger);
  background: #fcf0f0;
}
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}
.metric-card {
  padding: 20px;
  background: var(--surface-soft);
  border: 1px solid var(--line);
  border-radius: 11px;
}
.metric-value {
  font-size: 29px;
  font-weight: 650;
  font-variant-numeric: tabular-nums;
  color: var(--ink);
}
.metric-label {
  margin-top: 8px;
  font-size: 12px;
  font-weight: 500;
}
.metric-hint {
  margin-top: 5px;
  color: var(--muted);
  font-size: 10px;
  line-height: 1.6;
}
.cv-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--muted);
}
.cv-bar .badge {
  background: var(--accent-soft) !important;
  color: var(--accent) !important;
  font-size: 12px !important;
  font-weight: 500;
}
.features-title {
  font-size: 13px;
  font-weight: 600;
  margin: 25px 0 14px;
}
.features-list {
  display: grid;
  gap: 3px;
}
.feature-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--line);
}
.feature-rank {
  width: 22px;
  font-size: 11px;
  color: var(--faint);
}
.feature-name {
  font-size: 12px;
  flex: 0 1 160px;
  min-width: 0;
}
.feature-bar-wrap {
  flex: 1;
  height: 5px;
  border-radius: 10px;
  overflow: hidden;
  background: #edf2f4;
}
.feature-bar {
  height: 100%;
  background: #79afa2;
  border-radius: 10px;
}
.feature-value {
  width: 30px;
  text-align: right;
  font-size: 11px;
  color: var(--muted);
}
.model-method summary {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  cursor: pointer;
}
.model-method summary::after {
  content: "+";
  margin-left: auto;
  color: var(--muted);
  font-size: 18px;
}
.model-method[open] summary::after {
  content: "−";
}
.model-method div {
  padding: 18px 0 0;
  font-size: 12px;
  line-height: 1.9;
  color: var(--muted);
}
.model-method p:last-child {
  margin-bottom: 0;
}
@media (min-width: 900px) {
  .model-page {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .model-control {
    grid-column: auto;
  }
}
@media (max-width: 767px) {
  .metrics-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .section-head {
    padding: 20px;
  }
  .section-body {
    padding: 0 20px 20px;
  }
  .metric-card {
    padding: 16px;
  }
}
</style>
