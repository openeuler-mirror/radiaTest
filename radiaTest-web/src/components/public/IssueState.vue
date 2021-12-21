<template>
  <n-tooltip trigger="hover">
    <template #trigger>
      <n-icon :size="size" :color="color">
        <slot></slot>
      </n-icon>
    </template>
    {{ tip }}
  </n-tooltip>
</template>

<script>
import { defineComponent } from 'vue';

export default defineComponent({
  props: {
    tip: String,
    color: String,
    size: Number,
  },
  setup() {
    return {};
  },
});
</script>
