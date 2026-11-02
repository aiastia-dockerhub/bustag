<template>
  <article class="movie-card card-item" :aria-label="item.fanhao">
    <div class="movie-card-content">
      <button
        class="movie-cover"
        :aria-label="`查看 ${item.fanhao} 大图`"
        @click="showImage(imgProxyUrl(item.cover_img_url, 0, item.url))"
      >
        <CoverImage
          :src="item.cover_img_url"
          :referer="item.url"
          :priority="priority"
        />
        <span class="cover-hint"><AppIcon name="search" /> 查看大图</span>
      </button>
      <div class="movie-info">
        <div class="movie-heading">
          <h2>{{ item.fanhao }}</h2>
          <span
            class="status-pill"
            :class="{ 'status-liked': status === '已喜欢' }"
          >
            <span class="status-dot"></span>{{ status }}
          </span>
        </div>
        <a
          :href="item.url"
          target="_blank"
          rel="noopener noreferrer"
          class="movie-title"
          >{{ item.title || item.fanhao }}<AppIcon name="external"
        /></a>
        <div class="movie-meta">
          <span
            ><AppIcon name="calendar" />{{
              item.release_date || "发行日期未知"
            }}</span
          >
          <span v-if="item.add_date"
            ><AppIcon name="clock" />{{
              String(item.add_date).slice(0, 10)
            }}
            添加</span
          >
        </div>
        <div v-if="local" class="movie-meta">
          <span>已观看 {{ local.view_times || 0 }} 次</span
          ><span v-if="local.last_view_date"
            >上次 {{ String(local.last_view_date).slice(0, 10) }}</span
          >
        </div>
        <div class="movie-tags">
          <span
            v-for="star in visibleStars"
            :key="`star-${star}`"
            class="tag-chip tag-star"
            >{{ star }}</span
          >
          <span
            v-for="genre in visibleGenres"
            :key="`genre-${genre}`"
            class="tag-chip"
            >{{ genre }}</span
          >
          <button
            v-if="extraCount > 0 || expanded"
            class="tag-chip tag-more"
            @click="expanded = !expanded"
            :aria-expanded="expanded"
          >
            {{ expanded ? "收起" : `+${extraCount}` }}
          </button>
        </div>
      </div>
      <div class="movie-footer">
        <a
          v-if="local"
          class="btn btn-primary"
          :href="`/api/local_play/${local.id}`"
          target="_blank"
          ><AppIcon name="play" />播放本地文件</a
        >
        <MovieActions
          v-else
          :fanhao="item.fanhao"
          :mode="mode"
          :busy="busy"
          @rate="$emit('rate', item.fanhao, $event)"
        />
      </div>
    </div>
  </article>
</template>
<script setup lang="ts">
const props = defineProps<{
  item: any;
  priority?: boolean;
  mode?: "feedback" | "tag";
  busy?: boolean;
  local?: any;
  statusLabel?: string;
}>();
defineEmits<{ rate: [fanhao: string, value: number] }>();
const { showImage } = useImageModal();
const expanded = ref(false);
const stars = computed(() => props.item.tags_dict?.star || []);
const genres = computed(() => props.item.tags_dict?.genre || []);
const visibleStars = computed(() =>
  expanded.value ? stars.value : stars.value.slice(0, 3),
);
const visibleGenres = computed(() =>
  expanded.value ? genres.value : genres.value.slice(0, 5),
);
const extraCount = computed(
  () =>
    Math.max(0, stars.value.length - 3) + Math.max(0, genres.value.length - 5),
);
const status = computed(
  () =>
    props.statusLabel ||
    (props.local
      ? "本地收藏"
      : props.mode === "feedback"
        ? "偏好推荐"
        : props.item.rate_type === 1
          ? props.item.rate_value
            ? "已喜欢"
            : "不喜欢"
          : props.item.rate_type === 2
            ? "系统推荐"
            : "待打标"),
);
</script>
