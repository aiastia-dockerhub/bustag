<template>
  <div class="container py-3">
    <div class="model-page">

      <!-- ========== 训练模型 ========== -->
      <section class="card-section mb-4">
        <div class="section-head">
          <span class="section-icon">🎯</span>
          <div>
            <h5 class="section-title mb-0">重新训练模型</h5>
            <p class="section-desc mb-0">
              重新使用系统所有用户打标数据训练模型，当打标数据增多后，可以重新训练模型，提高模型预测效果
            </p>
          </div>
        </div>

        <div class="section-body">
          <button class="btn btn-primary px-4" @click="trainModel" :disabled="training">
            <span v-if="training" class="spinner-border spinner-border-sm me-1"></span>
            {{ training ? '训练中...' : '🚀 开始训练' }}
          </button>

          <transition name="fade">
            <div v-if="error" class="alert alert-danger mt-3 mb-0 d-flex align-items-center">
              <span class="me-2">⚠️</span>
              <span>{{ error }}</span>
            </div>
          </transition>

          <transition name="fade">
            <div v-if="training" class="training-hint mt-3">
              <span class="spinner-border spinner-border-sm text-primary me-2"></span>
              <span class="text-muted">正在训练中，可能需要几十秒，请稍候...</span>
            </div>
          </transition>
        </div>
      </section>

      <!-- ========== 推荐数据管理 ========== -->
      <section class="card-section mb-4">
        <div class="section-head">
          <span class="section-icon">🧹</span>
          <div>
            <h5 class="section-title mb-0">推荐数据管理</h5>
            <p class="section-desc mb-0">
              训练新模型后，旧推荐结果不会自动更新。可在此清理旧推荐，再用当前模型重新生成推荐。
              <span class="text-warning-emphasis fw-semibold">（用户打标数据会保留）</span>
            </p>
          </div>
        </div>

        <div class="section-body">
          <div class="btn-row">
            <button class="btn btn-outline-warning px-4" @click="clearRecommend" :disabled="recommendBusy">
              <span v-if="recommendBusy" class="spinner-border spinner-border-sm me-1"></span>
              🗑️ 清理旧推荐
            </button>
            <button class="btn btn-success px-4" @click="reRecommend" :disabled="recommendBusy">
              <span v-if="recommendBusy" class="spinner-border spinner-border-sm me-1"></span>
              ✨ 重新推荐
            </button>
          </div>

          <transition name="fade">
            <div v-if="recommendResult" class="result-box mt-3"
                 :class="recommendResult.success ? 'result-success' : 'result-error'">
              <span class="result-icon">{{ recommendResult.success ? '✅' : '❌' }}</span>
              <span>{{ recommendResultMsg }}</span>
            </div>
          </transition>
        </div>
      </section>

      <!-- ========== 模型数据 ========== -->
      <section class="card-section">
        <div class="section-head">
          <span class="section-icon">📊</span>
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
                <div class="metric-value">{{ formatScore(scores.precision) }}</div>
                <div class="metric-label">准确率 Precision</div>
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
              <span class="me-2">🔬 5 折交叉验证 F1</span>
              <span class="badge bg-info text-dark fs-6">
                {{ scores.cv_f1_mean }} ± {{ scores.cv_f1_std }}
              </span>
            </div>

            <!-- Top 特征 -->
            <template v-if="scores.top_features && scores.top_features.length > 0">
              <h6 class="features-title">🏆 Top {{ scores.top_features.length }} 重要特征</h6>
              <div class="features-list">
                <div v-for="(feat, idx) in scores.top_features" :key="feat.name"
                     class="feature-row">
                  <span class="feature-rank">{{ idx + 1 }}</span>
                  <span class="feature-name text-truncate">{{ feat.name }}</span>
                  <div class="feature-bar-wrap">
                    <div class="feature-bar"
                         :style="{ width: featureWidth(feat.importance) }"></div>
                  </div>
                  <span class="feature-value">{{ feat.importance }}</span>
                </div>
              </div>
            </template>
          </div>

          <div v-else-if="!training" class="empty-state text-center py-4">
            <div class="empty-icon">📭</div>
            <p class="text-muted mb-0">还没有训练过模型，点击上方"开始训练"。</p>
          </div>
        </div>
      </section>

      <!-- ========== 优化说明 ========== -->
      <section class="card-section mt-4">
        <a class="optim-toggle" data-bs-toggle="collapse" href="#optimCollapse"
           role="button" aria-expanded="false" aria-controls="optimCollapse">
          <span class="section-icon">💡</span>
          <span class="section-title mb-0">优化说明</span>
          <span class="toggle-arrow">▾</span>
        </a>
        <div class="collapse" id="optimCollapse">
          <div class="section-body">
            <h6 class="fw-bold">特征工程优化</h6>
            <ul class="mb-3">
              <li>按标签类型（genre/star/other）分别编码，而非混合编码</li>
              <li>新增数值特征：标签数量、演员数量、是否有演员信息</li>
              <li>新增系列（番号前缀）特征</li>
            </ul>
            <h6 class="fw-bold">模型优化</h6>
            <ul class="mb-0">
              <li>LightGBM 梯度提升树，更多树 + 更低学习率</li>
              <li>5 折交叉验证评估模型稳定性</li>
              <li>AUC 指标评估模型区分能力</li>
              <li>概率阈值推荐（≥0.6 才推荐），减少误推荐</li>
            </ul>
          </div>
        </div>
      </section>

    </div>
  </div>
</template>

<script setup>
const scores = ref(null)
const error = ref('')
const training = ref(false)

const loadModel = async () => {
  try {
    const res = await $fetch('/api/model')
    scores.value = res.model_scores
  } catch (e) {
    console.error('加载模型失败:', e)
  }
}

const trainModel = async () => {
  training.value = true
  error.value = ''
  try {
    const res = await $fetch('/api/do-training', { timeout: 300000 })
    if (res.error_msg) {
      error.value = res.error_msg
    } else {
      scores.value = res.model_scores
    }
  } catch (e) {
    error.value = '训练失败: ' + e.message
  } finally {
    training.value = false
  }
}

// 推荐数据管理
const recommendBusy = ref(false)
const recommendResult = ref(null)

const recommendResultMsg = computed(() => {
  const r = recommendResult.value
  if (!r) return ''
  if (!r.success) return '失败：' + (r.error || '未知错误')
  let msg = `已清理 ${r.deleted} 条旧推荐`
  if (r.total !== undefined) {
    msg += `，重新推荐 ${r.recommended} / ${r.total} 条`
  }
  if (r.warning) msg += `（${r.warning}）`
  return msg
})

const callRecommendApi = async (url, confirmMsg) => {
  if (!confirm(confirmMsg)) return
  recommendBusy.value = true
  recommendResult.value = null
  try {
    const res = await $fetch(url, { method: 'POST', timeout: 300000 })
    recommendResult.value = res
  } catch (e) {
    recommendResult.value = { success: false, error: e.message }
  } finally {
    recommendBusy.value = false
  }
}

const clearRecommend = () => callRecommendApi(
  '/api/clear-recommend',
  '确认清理所有系统推荐记录？\n（用户打标数据会保留）'
)

const reRecommend = () => callRecommendApi(
  '/api/re-recommend',
  '确认清理旧推荐并用当前模型重新推荐？\n（用户打标数据会保留）'
)

// 格式化分数：保留 2 位，无值时 N/A
const formatScore = (v) => (v === null || v === undefined || v === '') ? 'N/A' : v

// 计算特征条宽度（相对最大重要性）
const maxImportance = computed(() => {
  const feats = scores.value?.top_features
  if (!feats || !feats.length) return 1
  return Math.max(...feats.map(f => f.importance), 1)
})
const featureWidth = (imp) => Math.max(5, (imp / maxImportance.value * 100)) + '%'

onMounted(() => loadModel())
</script>

<style scoped>
.model-page {
  max-width: 880px;
  margin: 0 auto;
}

/* ===== 分区卡片 ===== */
.card-section {
  background: #fff;
  border: 1px solid #e9ecef;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

.section-head {
  display: flex;
  align-items: flex-start;
  gap: 0.85rem;
  padding: 1rem 1.25rem;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.section-icon {
  font-size: 1.4rem;
  line-height: 1.2;
}

.section-title {
  font-size: 1.05rem;
  font-weight: 600;
  color: #212529;
}

.section-desc {
  font-size: 0.85rem;
  color: #6c757d;
  margin-top: 0.15rem;
}

.text-warning-emphasis {
  color: #b8860b;
}

.section-body {
  padding: 1.25rem;
}

/* ===== 按钮行 ===== */
.btn-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

/* ===== 结果提示 ===== */
.result-box {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.7rem 1rem;
  border-radius: 8px;
  font-size: 0.9rem;
}
.result-success {
  background: #d1e7dd;
  color: #0a3622;
  border: 1px solid #badbcc;
}
.result-error {
  background: #f8d7da;
  color: #842029;
  border: 1px solid #f5c2c7;
}
.result-icon {
  font-size: 1rem;
}

/* ===== 指标卡片网格 ===== */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 0.85rem;
}

.metric-card {
  padding: 1rem;
  border-radius: 10px;
  border-left: 4px solid #0d6efd;
  background: #f8f9fa;
  transition: transform 0.15s, box-shadow 0.15s;
}
.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}
.metric-precision { border-left-color: #198754; }
.metric-recall { border-left-color: #0dcaf0; }
.metric-f1 { border-left-color: #0d6efd; }
.metric-auc { border-left-color: #6f42c1; }

.metric-value {
  font-size: 1.8rem;
  font-weight: 700;
  line-height: 1.1;
  color: #212529;
}
.metric-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #495057;
  margin-top: 0.15rem;
}
.metric-hint {
  font-size: 0.72rem;
  color: #868e96;
  margin-top: 0.1rem;
}

/* ===== 交叉验证条 ===== */
.cv-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
  font-size: 0.9rem;
  color: #495057;
}

/* ===== 特征列表 ===== */
.features-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: #495057;
  margin-bottom: 0.6rem;
}

.features-list {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.feature-row {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.4rem 0.6rem;
  border-radius: 6px;
  background: #f8f9fa;
  transition: background 0.15s;
}
.feature-row:hover {
  background: #eef4ff;
}

.feature-rank {
  flex-shrink: 0;
  width: 1.6rem;
  height: 1.6rem;
  line-height: 1.6rem;
  text-align: center;
  border-radius: 50%;
  background: #0d6efd;
  color: #fff;
  font-size: 0.78rem;
  font-weight: 700;
}

.feature-name {
  flex-shrink: 0;
  min-width: 90px;
  max-width: 40%;
  font-size: 0.85rem;
  color: #343a40;
}

.feature-bar-wrap {
  flex-grow: 1;
  height: 8px;
  background: #e9ecef;
  border-radius: 4px;
  overflow: hidden;
}
.feature-bar {
  height: 100%;
  background: linear-gradient(90deg, #0d6efd, #4dabf7);
  border-radius: 4px;
  transition: width 0.4s ease;
}

.feature-value {
  flex-shrink: 0;
  min-width: 2.5rem;
  text-align: right;
  font-size: 0.8rem;
  font-weight: 600;
  color: #495057;
}

/* ===== 空状态 ===== */
.empty-state {
  color: #adb5bd;
}
.empty-icon {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
}

/* ===== 训练提示 ===== */
.training-hint {
  display: flex;
  align-items: center;
}

/* ===== 优化说明折叠 ===== */
.optim-toggle {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 1rem 1.25rem;
  background: #f8f9fa;
  text-decoration: none;
  color: #212529;
}
.optim-toggle:hover {
  background: #eef0f2;
}
.optim-toggle .section-title {
  flex-grow: 1;
}
.toggle-arrow {
  color: #6c757d;
  transition: transform 0.2s;
  font-size: 0.85rem;
}
.optim-toggle[aria-expanded="true"] .toggle-arrow,
.optim-toggle.collapsed[aria-expanded="false"] .toggle-arrow {
  transform: rotate(0deg);
}

/* ===== 过渡动画 ===== */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.2s;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

/* ===== 响应式 ===== */
@media (max-width: 576px) {
  .section-head {
    padding: 0.85rem 1rem;
  }
  .section-body {
    padding: 1rem;
  }
  .metric-value {
    font-size: 1.5rem;
  }
  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .btn-row .btn {
    flex: 1;
  }
  .feature-name {
    min-width: 70px;
    max-width: 30%;
    font-size: 0.8rem;
  }
}
</style>
