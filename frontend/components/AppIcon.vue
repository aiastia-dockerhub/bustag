<template>
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.7"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    class="app-icon"
  >
    <path :d="paths[name] || paths.library" />
  </svg>
</template>
<script setup lang="ts">
defineProps<{ name: string }>();
const paths: Record<string, string> = {
  library: "M4 4v16M9 4v16M14 4v16M18 4l3 16",
  discover: "M12 3l2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z",
  tag: "M3 4h8l10 10-7 7L3 10ZM7 8h.01",
  search: "M21 21l-5-5M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0",
  folder: "M3 7V4h6l3 3h9v13H3Z",
  model: "M4 20V10h4v10M10 20V4h4v16M16 20v-7h4v7",
  database:
    "M20 5c0 2-16 2-16 0s16-2 16 0ZM4 5v14c0 2 16 2 16 0V5M4 12c0 2 16 2 16 0",
  download: "M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5",
  cloud:
    "M6 18a5 5 0 0 1-1-10 7 7 0 0 1 13-1 5.5 5.5 0 0 1 0 11M12 10v10m-3-3 3 3 3-3",
  magnet: "M4 4v8a8 8 0 0 0 16 0V4h-5v8a3 3 0 0 1-6 0V4ZM4 8h5m6 0h5",
  check: "m5 12 4 4L19 6",
  close: "m6 6 12 12M6 18 18 6",
  heart: "M20 5c-3-3-7-1-8 2-1-3-5-5-8-2s-2 6 1 9l7 7 7-7c3-3 4-6 1-9Z",
  settings: "M4 6h16M4 12h16M4 18h16M8 3v6m8 0v6m-6 0v6",
  logout: "M9 4H4v16h5M12 12h9m-4-4 4 4-4 4",
  external: "M14 3h7v7m0-7L10 14M10 4H4v16h16v-6",
  left: "m14 6-6 6 6 6",
  right: "m10 6 6 6-6 6",
  play: "m9 5 11 7-11 7ZM4 4v16",
  calendar: "M4 5h16v16H4ZM8 2v6m8-6v6M4 11h16",
  clock: "M12 8v5l3 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0",
  upload: "M12 16V3m-5 5 5-5 5 5M4 15v6h16v-6",
  refresh: "M20 8a9 9 0 0 0-16 0M20 3v5h-5M4 16a9 9 0 0 0 16 0M4 21v-5h5",
  eye: "M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12ZM15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0",
};
</script>
