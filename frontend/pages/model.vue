<template>
  <div class="container">
    <div class="row py-3">
      <div class="col-10 offset-1">
        <div class="accordion" id="modelAccordion">
          <!-- 训练模型 -->
          <div class="card">
            <div class="card-header" id="headingOne">
              <h2 class="mb-0">
                <button class="btn btn-link" type="button" data-bs-toggle="collapse" data-bs-target="#collapseOne"
                        aria-expanded="true" aria-controls="collapseOne">
                  训练模型
                </button>
              </h2>
            </div>
            <div id="collapseOne" class="collapse show" aria-labelledby="headingOne" data-bs-parent="#modelAccordion">
              <div class="card-body">
                <h5 class="card-title">重新训练模型</h5>
                <p class="card-text">重新使用系统所有用户打标数据训练模型，当打标数据增多后，可以重新训练模型，提高模型预测效果</p>
                <button class="btn btn-primary" @click="trainModel" :disabled="training">
                  {{ training ? '训练中...' : '开始训练' }}
                </button>
              </div>

              <!-- 错误信息 -->
              <div v-if="error" class="card-body text-danger">{{ error }}</div>
              <div v-if="training" class="card-body text-info">正在训练中，请稍候...</div>

              <!-- 当前模型数据 -->
              <div class="card-header"><h6>当前模型数据</h6></div>
              <div v-if="scores" class="card-body">
                <ul class="list-group list-group-flush">
                  <li class="list-group-item">准确率 (Precision): {{ scores.precision ?? 'N/A' }}</li>
                  <li class="list-group-item">覆盖率 (Recall): {{ scores.recall ?? 'N/A' }}</li>
                  <li class="list-group-item">综合评分 F1 (越高越好): {{ scores.f1 ?? 'N/A' }}</li>
                  <li v-if="scores.auc" class="list-group-item">AUC 区分度 (越接近1越好): {{ scores.auc }}</li>
                  <li v-if="scores.cv_f1_mean" class="list-group-item">5折交叉验证 F1: {{ scores.cv_f1_mean }} ± {{ scores.cv_f1_std }}</li>
                </ul>

                <!-- Top 10 重要特征 -->
                <template v-if="scores.top_features && scores.top_features.length > 0">
                  <div class="card-header mt-2"><h6>Top 10 重要特征</h6></div>
                  <ul class="list-group list-group-flush">
                    <li v-for="feat in scores.top_features" :key="feat.name"
                        class="list-group-item d-flex justify-content-between align-items-center">
                      {{ feat.name }}
                      <span class="badge bg-primary rounded-pill">{{ feat.importance }}</span>
                    </li>
                  </ul>
                </template>
              </div>
              <div v-else-if="!training" class="card-body text-muted">
                还没有训练过模型。
              </div>
            </div>
          </div>

          <!-- 优化说明 -->
          <div class="card">
            <div class="card-header" id="headingTwo">
              <h2 class="mb-0">
                <button class="btn btn-link collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseTwo"
                        aria-expanded="false" aria-controls="collapseTwo">
                  优化说明
                </button>
              </h2>
            </div>
            <div id="collapseTwo" class="collapse" aria-labelledby="headingTwo" data-bs-parent="#modelAccordion">
              <div class="card-body">
                <h6>特征工程优化</h6>
                <ul>
                  <li>按标签类型（genre/star/other）分别编码，而非混合编码</li>
                  <li>新增数值特征：标签数量、演员数量、是否有演员信息</li>
                  <li>新增系列（番号前缀）特征</li>
                </ul>
                <h6>模型优化</h6>
                <ul>
                  <li>LightGBM 梯度提升树，更多树 + 更低学习率</li>
                  <li>5折交叉验证评估模型稳定性</li>
                  <li>AUC 指标评估模型区分能力</li>
                  <li>概率阈值推荐（≥0.6 才推荐），减少误推荐</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
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

onMounted(() => loadModel())
</script>