<template>
  <div class="row" v-if="pageInfo">
    <div class="col-12 text-center">
      <h6>
        <a v-if="pageInfo.current_page !== 1" href="#" @click.prevent="goPage(1)"> 第一页</a>
        <a v-if="pageInfo.current_page > 1" href="#" @click.prevent="goPage(pageInfo.current_page - 1)"> 上一页</a>
        第{{ pageInfo.current_page }}页
        <a v-if="pageInfo.current_page < pageInfo.max_page" href="#" @click.prevent="goPage(pageInfo.current_page + 1)">下一页</a>
        <a v-if="pageInfo.current_page !== pageInfo.max_page" href="#" @click.prevent="goPage(pageInfo.max_page)">最后页</a>
      </h6>
      <div>
        <span>共 {{ pageInfo.max_page }}页,{{ pageInfo.total_items }}条</span>
        跳转
        <select class="form-select d-inline-block w-auto" :value="pageInfo.current_page" @change="goPage($event.target.value)">
          <option v-for="p in pageInfo.max_page" :key="p" :value="p">{{ p }}</option>
        </select>
        页
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: ['pageInfo'],
  emits: ['go-page'],
  methods: {
    goPage(page) {
      this.$emit('go-page', Number(page))
    }
  }
}
</script>