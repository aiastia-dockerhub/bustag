<template>
  <div class="container">
    <div class="row py-3">
      <div class="col-12">
        <h4>上传数据</h4>
        <div v-if="msg" class="alert alert-success">{{ msg }}</div>
        <div v-if="errmsg" class="alert alert-danger">{{ errmsg }}</div>
        <form @submit.prevent="uploadDb">
          <div class="mb-3">
            <label class="form-label">数据库文件</label>
            <input class="form-control" type="file" id="dbfile" ref="fileInput" accept=".db" />
          </div>
          <button type="submit" class="btn btn-primary" :disabled="uploading">
            {{ uploading ? '上传中...' : '上传' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import { postLoadDb } from '../assets/api.js'

export default {
  setup() {
    const msg = ref('')
    const errmsg = ref('')
    const uploading = ref(false)
    const fileInput = ref(null)

    const uploadDb = async () => {
      const file = fileInput.value?.files?.[0]
      if (!file) {
        errmsg.value = '请选择数据库文件'
        return
      }
      uploading.value = true
      msg.value = ''
      errmsg.value = ''
      try {
        const formData = new FormData()
        formData.append('dbfile', file)
        const res = await postLoadDb(formData)
        msg.value = res.data.msg
        errmsg.value = res.data.errmsg
      } catch (e) {
        errmsg.value = '上传失败: ' + e.message
      } finally {
        uploading.value = false
      }
    }

    return { msg, errmsg, uploading, fileInput, uploadDb }
  }
}
</script>