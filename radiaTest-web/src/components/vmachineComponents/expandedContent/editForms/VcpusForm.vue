<template>
  <n-form :model="model" :rules="rules" ref="form">
    <n-form-item label="Sockets" path="sockets">
      <n-input-number
        :min="1"
        :max="socketsMax"
        v-model:value="model.sockets"
        @keydown.enter.prevent
        style="width: 100%"
      />
    </n-form-item>
    <n-form-item label="Cores" path="cores">
      <n-input-number :min="1" :max="coresMax" v-model:value="model.cores" @keydown.enter.prevent style="width: 100%" />
    </n-form-item>
    <n-form-item label="Threads" path="threads">
      <n-input-number
        :min="1"
        :max="threadsMax"
        v-model:value="model.threads"
        @keydown.enter.prevent
        style="width: 100%"
      />
    </n-form-item>
  </n-form>
</template>

<script>
import { watch, onMounted, defineComponent } from 'vue';

import vcpusForm from '@/views/vmachine/modules/expandedContent/vcpusForm.js';

export default defineComponent({
  props: {
    data: Object
  },
  setup(props) {
    onMounted(() => {
      vcpusForm.initData(props.data);
    });

    watch(props, () => {
      vcpusForm.initData(props.data);
    });

    return {
      ...vcpusForm
    };
  }
});
</script>
