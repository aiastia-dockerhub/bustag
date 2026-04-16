<template>
  <div class="container">
    <div class="row py-3">
      <div class="col-12">
        <ul class="nav nav-tabs">
          <li class="nav-item">
            <router-link class="nav-link" to="/local">本地文件</router-link>
          </li>
          <li class="nav-item">
            <router-link class="nav-link active" to="/local_fanhao">上传番号</router-link>
          </li>
        </ul>
      </div>
    </div>

    <div class="row py-3">
      <div class="col-12">
        <div v-if="msg" class="alert alert-success">{{ msg }}</div>
        <form @submit.prevent="submitFanhao">
          <div class="mb-3">
            <label class="form-label">番号列表（每行一个）</label>
            <textarea class="form-control" v-model="fanhao" rows="10" placeholder="SSIS-406&#10;ABP-123"></textarea>
          </div>
          <div class="mb-3 form-check">
            <input type="checkbox" class="form-check-input" id="tagLike" v-model="tagLike" true-value="1" false-value="0">
            <label class="form-check-label" for="tagLike">同时打标为喜欢</label>
          </div>
          <button type="submit" class="btn btn-primary">提交</button>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import { postLocalFanhao } from '../assets/api.js'

export default {
  setup() {
    const fanhao = ref('')
    const tagLike = ref('0')
    const msg = ref('')

    const submitFanhao = async () => {
      if (!fanhao.value.trim()) return
      try {
        const res = await postLocalFanhao({ fanhao: fanhao.value, tag_like: tagLike.value === '1' })
        msg.value = res.data.msg
        fanhao.value = ''
      } catch (e) {
        msg.value = '提交失败: ' + e.message
      }
    }

    return { fanhao, tagLike, msg, submitFanhao }
  }
}
</script>