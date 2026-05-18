<template>
  <div class="container">
    <div class="card-item mt-3">
      <h5 class="fw-bold mb-3">💾 上传数据</h5>
      <div v-if="msg" class="alert alert-success mb-3">✅ {{ msg }}</div>
      <div v-if="errmsg" class="alert alert-danger mb-3">❌ {{ errmsg }}</div>
      <form @submit.prevent="uploadDb">
        <div class="mb-3">
          <label class="form-label fw-bold">数据库文件</label>
          <input class="form-control" type="file" ref="fileInput" accept=".db" style="border-radius: 8px;" />
          <div class="form-text">上传 bustag 的 .db 数据库文件，导入用户打标数据</div>
        </div>
        <button type="submit" class="btn btn-primary" :disabled="uploading">
          {{ uploading ? '⏳ 上传中...' : '📤 上传' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
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
    const res = await $fetch('/api/load_db', {
      method: 'POST',
      body: formData,
    })
    msg.value = res.msg
    errmsg.value = res.errmsg
  } catch (e) {
    errmsg.value = '上传失败: ' + e.message
  } finally {
    uploading.value = false
  }
}
</script>