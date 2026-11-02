<template>
  <div
    class="movie-actions action-buttons"
    role="group"
    :aria-label="`${fanhao} 影片操作`"
  >
    <div class="download-actions">
      <button
        class="btn btn-quiet"
        :disabled="!!magnetLoading[fanhao]"
        @click="copyMagnet(fanhao)"
      >
        <AppIcon
          :name="magnetLoading[fanhao] === 'done' ? 'check' : 'magnet'"
        />
        {{
          magnetLoading[fanhao] === "done"
            ? "已复制"
            : magnetLoading[fanhao]
              ? "获取中"
              : "磁力"
        }}
      </button>
      <button
        class="btn btn-quiet"
        :disabled="!!aria2Loading[fanhao]"
        @click="sendToAria2(fanhao)"
      >
        <AppIcon
          :name="aria2Loading[fanhao] === 'done' ? 'check' : 'download'"
        />
        {{
          aria2Loading[fanhao] === "done"
            ? "已提交"
            : aria2Loading[fanhao]
              ? "提交中"
              : "Aria2"
        }}
      </button>
      <button
        class="btn btn-quiet"
        :disabled="!!pushLoading[fanhao]"
        @click="sendTo115(fanhao)"
      >
        <AppIcon :name="pushLoading[fanhao] === 'done' ? 'check' : 'cloud'" />
        {{
          pushLoading[fanhao] === "done"
            ? "已提交"
            : pushLoading[fanhao]
              ? "提交中"
              : "115"
        }}
      </button>
    </div>
    <div class="rating-actions">
      <button
        class="btn btn-positive"
        :disabled="busy"
        @click="$emit('rate', 1)"
      >
        <AppIcon :name="mode === 'feedback' ? 'check' : 'heart'" />{{
          mode === "feedback" ? "正确" : "喜欢"
        }}
      </button>
      <button class="btn btn-quiet" :disabled="busy" @click="$emit('rate', 0)">
        <AppIcon name="close" />{{ mode === "feedback" ? "错误" : "不喜欢" }}
      </button>
    </div>
  </div>
</template>
<script setup lang="ts">
defineProps<{ fanhao: string; mode?: "feedback" | "tag"; busy?: boolean }>();
defineEmits<{ rate: [value: number] }>();
const { magnetLoading, copyMagnet } = useMagnet();
const { aria2Loading, sendToAria2 } = useAria2();
const { pushLoading, sendTo115 } = use115Push();
</script>
