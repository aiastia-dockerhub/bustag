<template>
  <div class="search-select" @focusout="onFocusOut">
    <label :for="id">{{ label }}</label>
    <div class="search-select-input">
      <input :id="id" ref="input" v-model="text" class="form-control"
        role="combobox" autocomplete="off" aria-autocomplete="list"
        :placeholder="placeholder" :disabled="disabled" :aria-expanded="open"
        :aria-controls="`${id}-options`"
        :aria-activedescendant="open && active >= 0 ? `${id}-option-${active}` : undefined"
        @focus="showOptions" @click="showOptions" @input="onInput" @keydown="onKeydown" />
      <button v-if="text" type="button" class="search-select-clear" :aria-label="`清除${label}`" :disabled="disabled" @click="clear">×</button>
    </div>
    <div v-if="open" class="search-select-popup">
      <div class="search-select-count" role="status">{{ filtered.length }} 个匹配{{ !text ? ' · 输入关键词快速查找' : '' }}</div>
      <ul :id="`${id}-options`" role="listbox" :aria-label="label">
        <li v-for="(option, index) in filtered" :id="`${id}-option-${index}`" :key="option.id"
          role="option" :aria-selected="option.id === modelValue" :class="{ active: index === active }"
          @mousedown.prevent @click="choose(option)">{{ option.value }}</li>
      </ul>
      <p v-if="!filtered.length" class="search-select-empty">没有匹配项，试试其他关键词</p>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  id: { type: String, required: true },
  label: { type: String, required: true },
  placeholder: String,
  options: { type: Array, default: () => [] },
  modelValue: { type: [String, Number], default: '' },
  disabled: Boolean,
});
const emit = defineEmits(['update:modelValue', 'select']);
const input = ref(null);
const text = ref('');
const open = ref(false);
const active = ref(-1);
const editing = ref(false);
const filtered = computed(() => {
  const keyword = editing.value ? text.value.trim().toLocaleLowerCase() : '';
  return props.options.filter(option => option.value.toLocaleLowerCase().includes(keyword));
});
watch(() => props.modelValue, value => {
  text.value = props.options.find(option => option.id === value)?.value || '';
  editing.value = false;
}, { immediate: true });
const showOptions = () => { open.value = true; };
const onInput = () => {
  editing.value = true;
  open.value = true;
  active.value = -1;
  // Selection is committed only when a suggestion is chosen.
};
const choose = option => {
  text.value = option.value;
  editing.value = false;
  open.value = false;
  active.value = -1;
  emit('update:modelValue', option.id);
  emit('select', option.id);
};
const clear = () => {
  text.value = '';
  editing.value = true;
  active.value = -1;
  emit('update:modelValue', '');
  input.value?.focus();
};
const onFocusOut = event => {
  if (event.currentTarget.contains(event.relatedTarget)) return;
  open.value = false;
  active.value = -1;
  text.value = props.options.find(option => option.id === props.modelValue)?.value || '';
  editing.value = false;
};
const onKeydown = async event => {
  if (event.isComposing) return;
  if (event.key === 'Escape') { open.value = false; active.value = -1; return; }
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault();
    open.value = true;
    const count = filtered.value.length;
    active.value = count ? (active.value + (event.key === 'ArrowDown' ? 1 : active.value < 0 ? count : -1) + count) % count : -1;
    await nextTick();
    document.getElementById(`${props.id}-option-${active.value}`)?.scrollIntoView({ block: 'nearest' });
  } else if (event.key === 'Enter' && open.value) {
    event.preventDefault();
    const option = filtered.value[active.value] || (filtered.value.length === 1 ? filtered.value[0] : null);
    if (option) choose(option);
  }
};
</script>
