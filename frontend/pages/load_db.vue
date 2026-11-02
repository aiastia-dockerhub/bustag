<template>
  <div class="import-layout">
    <section class="surface">
      <h2 class="panel-title">导入打标数据</h2>
      <p class="panel-description">迁移已有的偏好记录，继续完善你的资料库。</p>
      <div v-if="msg" class="alert alert-success" role="status">{{ msg }}</div>
      <div v-if="errmsg" class="alert alert-danger" role="alert">
        {{ errmsg }}
      </div>
      <form @submit.prevent="uploadDb">
        <div class="file-upload-field">
          <span class="guide-icon"><AppIcon name="upload" /></span
          ><label for="database-file" class="form-label">选择数据库文件</label>
          <p>支持 Bustag 的 .db 文件</p>
          <input
            id="database-file"
            class="form-control"
            type="file"
            ref="fileInput"
            accept=".db"
          />
        </div>
        <button type="submit" class="btn btn-primary" :disabled="uploading">
          <AppIcon name="database" />{{ uploading ? "导入中…" : "开始导入" }}
        </button>
      </form>
    </section>
    <aside class="form-guide">
      <span class="guide-icon"><AppIcon name="database" /></span>
      <h2>让偏好接着积累</h2>
      <p>导入会读取你之前标记的喜欢与不喜欢。缺少的影片资料会在后台补充。</p>
      <p>导入完成后，可以重新训练模型，让这些记录参与下一次推荐。</p>
      <NuxtLink to="/model" class="text-link"
        >前往推荐模型<AppIcon name="right"
      /></NuxtLink>
    </aside>
  </div>
</template>

<script setup>
const msg = ref("");
const errmsg = ref("");
const uploading = ref(false);
const fileInput = ref(null);

const uploadDb = async () => {
  const file = fileInput.value?.files?.[0];
  if (!file) {
    errmsg.value = "请选择数据库文件";
    return;
  }
  uploading.value = true;
  msg.value = "";
  errmsg.value = "";
  try {
    const formData = new FormData();
    formData.append("dbfile", file);
    const res = await $fetch("/api/load_db", {
      method: "POST",
      body: formData,
    });
    msg.value = res.msg;
    errmsg.value = res.errmsg;
  } catch (e) {
    errmsg.value = "上传失败: " + e.message;
  } finally {
    uploading.value = false;
  }
};
</script>
