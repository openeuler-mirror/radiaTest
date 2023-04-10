<template>
  <n-form :model="model" :rules="rules" ref="form">
    <n-form-item path="memory">
      <n-input-number
        v-model:value="model.memory"
        :step="1024"
        :min="1024"
        :max="32768"
        @keydown.enter.prevent
        style="width: 100%"
      >
        <template #suffix>MB</template>
      </n-input-number>
    </n-form-item>
  </n-form>
</template>

<script>
import { watch, onMounted, defineComponent } from 'vue';

import memForm from '@/views/vmachine/modules/expandedContent/memForm.js';

export default defineComponent({
  props: {
    data: Object
  },
  setup(props) {
    onMounted(() => {
      memForm.initData(props.data);
    });

    watch(props, () => {
      memForm.initData(props.data);
    });

    return {
      ...memForm,
      rules: {
        memory: {
          required: true,
          validator(rule, value) {
            if (!value) {
              return new Error('内存容量不可为空');
            } else if (Number(value) < 1024) {
              return new Error('内存容量不可小于1024MB');
            }
            return true;
          },
          trigger: ['blur']
        }
      }
    };
  }
});
</script>
