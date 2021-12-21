<template>
  <n-form :model="formValue" :rules="rules" ref="formRef">
    <n-form-item label="网卡类型" path="mode">
      <n-select
        v-model:value="formValue.mode"
        :options="[
          {
            label: 'bridge',
            value: 'bridge',
          },
          {
            label: 'network',
            value: 'network',
          },
        ]"
        placeholder="默认 bridge"
        @keydown.enter.prevent
        style="width: 100%"
      />
    </n-form-item>
    <n-form-item label="网卡总线" path="bus">
      <n-select
        v-model:value="formValue.bus"
        :options="[
          {
            label: 'virtio',
            value: 'virtio',
          },
          {
            label: 'e1000e',
            value: 'e1000e',
          },
          {
            label: 'e1000',
            value: 'e1000',
          },
          {
            label: 'rtl8139',
            value: 'rtl8139',
          },
        ]"
        placeholder="默认 virtio"
        @keydown.enter.prevent
        style="width: 100%"
      />
    </n-form-item>
    <n-form-item label="MAC地址" path="mac">
      <n-input
        v-model:value="formValue.mac"
        @input="handleMacInput"
        placeholder="若不填写将会自动生成"
        @keydown.enter.prevent
        style="width: 100%"
      />
    </n-form-item>
  </n-form>
</template>

<script>
import { watch, onMounted, onUnmounted, defineComponent } from 'vue';

import { createAjax } from '@/assets/CRUD/create';
import nicsForm from '@/views/vmachine/modules/expandedContent/nicsForm.js';

export default defineComponent({
  props: {
    id: Number,
  },
  setup(props, context) {
    onMounted(() => {
      nicsForm.initData(props.id);
    });

    watch(props, () => {
      nicsForm.initData(props.id);
    });

    onUnmounted(() => {
      nicsForm.clean();
    });

    return {
      ...nicsForm,
      handlePropsButtonClick: () => nicsForm.validateFormData(context),
      post: () => {
        createAjax.postForm('/v1/vnic', nicsForm.formValue);
        context.emit('close');
      },
    };
  },
});
</script>
