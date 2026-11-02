<template>
  <div class="row g-0" v-if="pageInfo && pageInfo.max_page > 0">
    <div class="col-12 text-center">
      <h6>
        <a v-if="pageInfo.current_page > 1" href="#" @click.prevent="goPage(1)">第一页</a>
        <a v-if="pageInfo.current_page > 1" href="#" @click.prevent="goPage(pageInfo.current_page - 1)"> 上一页</a>
        第{{ pageInfo.current_page }}页
        <a v-if="pageInfo.current_page < pageInfo.max_page" href="#" @click.prevent="goPage(pageInfo.current_page + 1)">下一页</a>
        <a v-if="pageInfo.current_page < pageInfo.max_page" href="#" @click.prevent="goPage(pageInfo.max_page)">最后页</a>
      </h6>
      <div>
        <span>共 {{ pageInfo.max_page }}页,{{ pageInfo.total_items }}条</span>
        跳转
        <input type="number" class="form-control d-inline-block" style="width: 5.5rem"
               aria-label="跳转页码" min="1" :max="pageInfo.max_page"
               :value="pageInfo.current_page" @change="goPage($event.target.value)" />
        页
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({ pageInfo: Object })
const emit = defineEmits(['go-page'])
const goPage = (value) => {
  const number = Number(value)
  if (!Number.isFinite(number)) return
  const page = Math.max(1, Math.min(props.pageInfo.max_page, Math.trunc(number)))
  if (page === props.pageInfo.current_page) return
  window.scrollTo({ top: 0, behavior: 'smooth' })
  emit('go-page', page)
}
</script>
