<template>
  <div class="container">
    <div class="row py-3">
      <div class="col-12">
        <h4>模型信息</h4>
        <div v-if="error" class="alert alert-danger">{{ error }}</div>
        <div v-if="training" class="alert alert-info">
          正在训练中，GridSearchCV 搜索 54 种参数组合，预计需要 1-5 分钟，请耐心等待...
        </div>

        <div v-if="scores" class="mb-3">
          <table class="table table-bordered">
            <tbody>
              <tr><th>准确率 (Accuracy)</th><td>{{ (scores.accuracy * 100).toFixed(1) }}%</td></tr>
              <tr><th>精确率 (Precision)</th><td>{{ (scores.precision * 100).toFixed(1) }}%</td></tr>
              <tr><th>召回率 (Recall)</th><td>{{ (scores.recall * 100).toFixed(1) }}%</td></tr>
              <tr><th>F1 分数</th><td>{{ (scores.f1 * 100).toFixed(1) }}%</td></tr>
            </tbody>
          </table>
        </div>
        <div v-else-if="!training">
          <p class="text-muted">还没有训练好的模型</p>
        </div>

        <button class="btn btn-primary" @click="trainModel" :disabled="training">
          {{ training ? '训练中...' : '训练模型' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { getModel, doTraining } from '../assets/api.js'

export default {
  setup() {
    const scores = ref(null)
    const error = ref('')
    const training = ref(false)

    const loadModel = async () => {
      try {
        const res = await getModel()
        scores.value = res.data.model_scores
      } catch (e) {
        console.error('加载模型失败:', e)
      }
    }

    const trainModel = async () => {
      training.value = true
      error.value = ''
      try {
        const res = await doTraining()
        if (res.data.error_msg) {
          error.value = res.data.error_msg
        } else {
          scores.value = res.data.model_scores
        }
      } catch (e) {
        error.value = '训练失败: ' + e.message
      } finally {
        training.value = false
      }
    }

    onMounted(() => loadModel())

    return { scores, error, training, trainModel }
  }
}
</script>