<template>
  <n-form
    :label-width="40"
    :model="formValue"
    :rules="rules"
    :size="size"
    label-placement="top"
    ref="formRef"
  >
    <n-grid :cols="18" :x-gap="20">
      <n-form-item-gi :span="6" label="创建方法" path="method">
        <n-select
          v-model:value="formValue.method"
          :options="[
            {
              label: 'qcow2镜像导入',
              value: 'import',
            },
            {
              label: '虚拟光驱安装',
              value: 'cdrom',
            },
            {
              label: '自动安装',
              value: 'auto',
            },
          ]"
          placeholder="选择创建方法"
        />
      </n-form-item-gi>
      <n-form-item-gi :span="6" label="产品" path="product">
        <n-select
          v-model:value="formValue.product"
          :options="productOpts"
          placeholder="选择产品"
          filterable
        />
      </n-form-item-gi>
      <n-form-item-gi :span="6" label="版本" path="version">
        <n-select
          v-model:value="formValue.version"
          :options="versionOpts"
          placeholder="选择版本"
          filterable
        />
      </n-form-item-gi>
      <n-form-item-gi :span="12" label="里程碑" path="milestone_id">
        <n-select
          v-model:value="formValue.milestone_id"
          :options="milestoneOpts"
          placeholder="选择里程碑"
          filterable
        />
      </n-form-item-gi>
      <n-form-item-gi :span="6" label="架构" path="frame" ref="frameRef">
        <n-select
          v-model:value="formValue.frame"
          :options="frameOpts"
          placeholder="选择架构"
          filterable
        />
      </n-form-item-gi>
      <n-form-item-gi :span="6" label="CPU Mode" path="cpu_mode">
        <n-select
          v-model:value="formValue.cpu_mode"
          :options="[
            { label: 'host-passthrough', value: 'host-passthrough' },
            { label: 'host-model', value: 'host-model' },
            { label: 'custom', value: 'custom' },
          ]"
          placeholder="默认 host-passthrough"
          filterable
        />
      </n-form-item-gi>
      <n-form-item-gi :span="6" label="内存(MB)" path="meomory">
        <n-input-number
          v-model:value="formValue.memory"
          :step="1024"
          :validator="validator"
          :max="16384"
        >
          <template #suffix>MB</template>
        </n-input-number>
      </n-form-item-gi>
      <n-form-item-gi :span="6" label="磁盘(GiB)" path="capacity">
        <n-input-number
          :disabled="formValue.method === 'import'"
          v-model:value="formValue.capacity"
          :step="10"
          :validator="validator"
          :max="500"
        >
          <template #suffix>GiB</template>
        </n-input-number>
      </n-form-item-gi>
      <n-form-item-gi :span="6" label="Sockets" path="sockets">
        <n-input-number
          v-model:value="formValue.sockets"
          :validator="validator"
          :min="1"
          :max="4"
        />
      </n-form-item-gi>
      <n-form-item-gi :span="6" label="Cores" path="cores">
        <n-input-number
          v-model:value="formValue.cores"
          :validator="validator"
          :min="1"
          :max="4"
        />
      </n-form-item-gi>
      <n-form-item-gi :span="6" label="Threads" path="threads">
        <n-input-number
          v-model:value="formValue.threads"
          :validator="validator"
          :min="1"
          :max="4"
        />
      </n-form-item-gi>
      <n-form-item-gi :span="18" label="使用描述" path="description">
        <n-input
          v-model:value="formValue.description"
          placeholder="输入使用描述"
        />
      </n-form-item-gi>
    </n-grid>
  </n-form>
</template>

<script>
import { onMounted, onUnmounted, defineComponent } from 'vue';

import { createAjax } from '@/assets/CRUD/create';
import createForm from '@/views/vmachine/modules/createForm.js';

export default defineComponent({
  setup(props, context) {
    onMounted(() => {
      createForm.getProductOptions();
    });

    createForm.activeMethodWatcher();
    createForm.activeProductWatcher();
    createForm.activeVersionWatcher();

    onUnmounted(() => {
      createForm.clean();
    });

    return {
      ...createForm,
      handlePropsButtonClick: () => createForm.validateFormData(context),
      post: () => {
        createAjax.postForm('/v1/vmachine', createForm.formValue);
        context.emit('close');
      },
    };
  },
});
</script>

<style scoped></style>
