<template>
  <n-form :model="formValue" ref="formRef">
    <n-form-item label="磁盘总线" path="bus">
      <n-select
        v-model:value="formValue.bus"
        :options="[
          {
            label: 'virtio',
            value: 'virtio',
          },
          {
            label: 'sata',
            value: 'sata',
          },
          {
            label: 'scsi',
            value: 'scsi',
          },
          {
            label: 'usb',
            value: 'usb',
          },
        ]"
        placeholder="默认 virtio"
        clearable
        @keydown.enter.prevent
        style="width: 100%"
      />
    </n-form-item>
    <n-form-item label="缓存类型" path="cache">
      <n-select
        v-model:value="formValue.cache"
        :options="[
          {
            label: 'default',
            value: 'default',
          },
          {
            label: 'none',
            value: 'none',
          },
          {
            label: 'writethrough',
            value: 'writethrough',
          },
          {
            label: 'writeback',
            value: 'writeback',
          },
          {
            label: 'directsync',
            value: 'directsync',
          },
          {
            label: 'unsafe',
            value: 'unsafe',
          },
        ]"
        clearable
        filterable
        placeholder="默认 default"
        @keydown.enter.prevent
        style="width: 100%"
      />
    </n-form-item>
    <n-form-item label="磁盘容量" path="capacity">
      <n-input-number
        v-model:value="formValue.capacity"
        placeholder="请确保磁盘容量足够安装系统"
        :min="0"
        :max="100"
        :step="10"
        @keydown.enter.prevent
        style="width: 100%"
      >
        <template #suffix>GiB</template>
      </n-input-number>
    </n-form-item>
  </n-form>
</template>

<script>
import { watch, onMounted, onUnmounted, defineComponent } from 'vue';

import { createAjax } from '@/assets/CRUD/create';
import disksForm from '@/views/vmachine/modules/expandedContent/disksForm.js';

export default defineComponent({
  props: {
    id: Number,
  },
  setup(props, context) {
    onMounted(() => {
      disksForm.initData(props.id);
    });

    watch(props, () => {
      disksForm.initData(props.id);
    });

    onUnmounted(() => {
      disksForm.clean();
    });

    return {
      ...disksForm,
      handlePropsButtonClick: () => disksForm.validateFormData(context),
      post: () => {
        createAjax.postForm('/v1/vdisk', disksForm.formValue);
        context.emit('close');
      },
    };
  },
});
</script>
