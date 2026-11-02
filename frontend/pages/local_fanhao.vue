<template>
  <div class="library-page">
    <div class="library-toolbar">
      <div class="segmented-control">
        <NuxtLink to="/local">本地文件</NuxtLink
        ><NuxtLink to="/local_fanhao" class="active">添加收藏</NuxtLink>
      </div>
    </div>
    <div class="import-layout">
      <section class="surface">
        <h2 class="panel-title">添加影片番号</h2>
        <p class="panel-description">批量添加你的影片，已有资料会自动关联。</p>
        <div v-if="msg" class="alert alert-success" role="status">
          {{ msg }}
        </div>
        <div v-if="error" class="alert alert-danger" role="alert">
          {{ error }}
        </div>
        <form @submit.prevent="submitFanhao">
          <div class="mb-4">
            <label for="fanhao-list" class="form-label">番号列表</label
            ><textarea
              id="fanhao-list"
              class="form-control mono-input"
              v-model="fanhao"
              rows="8"
              placeholder="SSIS-406&#10;ABP-123"
              required
            ></textarea>
            <div class="form-text">
              每行一个番号；关联本地文件时，可填写「番号,文件路径」。
            </div>
          </div>
          <div class="mb-4">
            <label for="movie-type" class="form-label">影片类型</label
            ><select id="movie-type" class="form-select" v-model="movieType">
              <option value="mixed">自动识别</option>
              <option value="normal">有码</option>
              <option value="uncensored">无码</option>
            </select>
          </div>
          <div class="mb-4 form-check">
            <input
              type="checkbox"
              class="form-check-input"
              id="tagLike"
              v-model="tagLike"
              true-value="1"
              false-value="0"
            /><label class="form-check-label" for="tagLike"
              >同时标记为喜欢</label
            >
          </div>
          <button type="submit" class="btn btn-primary" :disabled="submitting">
            <AppIcon name="upload" />{{ submitting ? "提交中…" : "添加到收藏" }}
          </button>
        </form>
      </section>
      <aside class="form-guide">
        <span class="guide-icon"><AppIcon name="folder" /></span>
        <h2>把收藏整理好</h2>
        <p>添加本地路径后，你可以直接从资料库打开影片。</p>
        <div class="guide-example">
          SSIS-406<br />ABP-123,/Movies/ABP-123.mp4
        </div>
        <p>尚未收录的番号会加入后台爬取队列，完成后即可查看完整资料。</p>
      </aside>
    </div>
  </div>
</template>

<script setup>
const fanhao = ref("");
const tagLike = ref("0");
const movieType = ref("mixed");
const msg = ref("");
const error = ref("");
const submitting = ref(false);

const submitFanhao = async () => {
  if (!fanhao.value.trim() || submitting.value) return;
  submitting.value = true;
  error.value = "";
  msg.value = "";
  try {
    const res = await $fetch("/api/local_fanhao", {
      method: "POST",
      body: {
        fanhao: fanhao.value,
        tag_like: tagLike.value === "1",
        movie_type: movieType.value,
      },
    });
    msg.value = res.msg;
    fanhao.value = "";
  } catch (e) {
    error.value = "提交失败: " + e.message;
  } finally {
    submitting.value = false;
  }
};
</script>
