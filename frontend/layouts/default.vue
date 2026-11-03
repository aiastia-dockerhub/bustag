<template>
  <div class="app-shell">
    <aside class="app-sidebar">
      <NuxtLink class="brand" to="/" aria-label="Bustag 首页"
        ><span class="brand-mark"><AppIcon name="library" /></span
        ><span>Bustag<small>你的私人影音资料库</small></span></NuxtLink
      >
      <span class="sidebar-caption">资料库</span>
      <nav class="main-navigation" aria-label="主导航">
        <NuxtLink
          v-for="entry in navigation"
          :key="entry.path"
          :to="entry.path"
          :class="{ 'is-active': isActive(entry.path) }"
          :aria-current="isActive(entry.path) ? 'page' : undefined"
        >
          <AppIcon :name="entry.icon" /><span>{{ entry.label }}</span
          ><span v-if="isActive(entry.path)" class="nav-active-dot"></span>
        </NuxtLink>
      </nav>
      <div class="sidebar-bottom">
        <span class="sidebar-caption">下载服务</span>
        <div class="service-buttons">
          <button aria-label="Aria2 下载设置" @click="openSettings">
            <AppIcon name="download" /><span>Aria2 设置</span
            ><AppIcon name="settings" />
          </button>
          <button aria-label="115 云下载设置" @click="open115Settings">
            <AppIcon name="cloud" /><span>115 云下载</span
            ><AppIcon name="settings" />
          </button>
        </div>
        <button
          v-if="auth.enabled && auth.authed"
          class="logout-button"
          aria-label="退出登录"
          @click="logout"
        >
          <AppIcon name="logout" />退出登录
        </button>
        <div class="sidebar-footer">
          <span>Bustag · {{ version }}</span
          ><a
            href="https://github.com/aiastia-dockerhub/bustag"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="查看 GitHub 项目"
            ><AppIcon name="external"
          /></a>
        </div>
      </div>
    </aside>
    <div class="workspace">
      <header class="workspace-topbar">
        <span
          >我的资料库 <span class="breadcrumb-separator">/</span>
          {{ current.label }}</span
        ><NuxtLink to="/search" class="quick-search"
          ><AppIcon name="search" />搜索影片</NuxtLink
        >
      </header>
      <main id="main-content" class="workspace-main">
        <header class="page-heading">
          <div>
            <span class="page-eyebrow">{{ current.eyebrow }}</span>
            <h1>{{ current.title }}</h1>
            <p>{{ current.description }}</p>
          </div>
          <span class="heading-icon"><AppIcon :name="current.icon" /></span>
        </header>
        <slot />
      </main>
      <footer class="workspace-footer">
        每一次选择，都让推荐更懂你。<span>Bustag</span>
      </footer>
    </div>
    <ClientOnly><ImagePreview /></ClientOnly>
    <AppNotifications />
    <Aria2SettingsModal />
    <Open115SettingsModal />
  </div>
</template>
<script setup>
const navigation = [
  {
    path: "/",
    label: "为你推荐",
    title: "为你推荐",
    eyebrow: "DISCOVER",
    icon: "discover",
    description: "从你的偏好出发，发现下一部值得收藏的影片。",
  },
  {
    path: "/tagit",
    label: "偏好打标",
    title: "记录你的偏好",
    eyebrow: "YOUR TASTE",
    icon: "tag",
    description: "喜欢，或略过。用每一次选择，慢慢完善你的推荐。",
  },
  {
    path: "/search",
    label: "搜索发现",
    title: "搜索资料库",
    eyebrow: "EXPLORE",
    icon: "search",
    description: "通过番号、影片名称、类型或演员，找到你想看的内容。",
  },
  {
    path: "/local",
    label: "本地收藏",
    title: "本地收藏",
    eyebrow: "COLLECTION",
    icon: "folder",
    description: "整理已经收藏的影片，让每一部都有迹可循。",
  },
  {
    path: "/model",
    label: "推荐模型",
    title: "推荐模型",
    eyebrow: "PERSONALIZATION",
    icon: "model",
    description: "让你的选择变成更准确的推荐，查看和管理模型表现。",
  },
  {
    path: "/add_data",
    label: "批量添加",
    title: "批量添加影片",
    eyebrow: "IMPORT",
    icon: "download",
    description: "输入演员 ID 或搜索关键词，预览勾选后批量抓取有磁力链接的影片入库。",
  },
  {
    path: "/load_db",
    label: "数据管理",
    title: "数据管理",
    eyebrow: "YOUR DATA",
    icon: "database",
    description: "导入已有打标记录，延续你积累的观影偏好。",
  },
];
const route = useRoute();
const isActive = (path) =>
  path === "/"
    ? route.path === "/"
    : path === "/local"
      ? ["/local", "/local_fanhao"].includes(route.path)
      : route.path === path;
const current = computed(
  () => navigation.find((entry) => isActive(entry.path)) || navigation[0],
);
const version = useRuntimeConfig().public.appVersion || "dev";
const { openSettings } = useAria2Settings();
const { openSettings: open115Settings } = use115Settings();
const auth = useAuthState();
onMounted(() => fetchAuthStatus());
</script>
