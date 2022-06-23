<template>
  <n-form
    :label-width="40"
    :model="formValue"
    :rules="rules"
    :size="size"
    label-placement="top"
    ref="formRef"
  >
    <n-grid :cols="12" :x-gap="20">
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
      <n-form-item-gi :span="12" label="里程碑" path="milestone">
        <n-select
          v-model:value="formValue.milestone_id"
          :options="milestoneOpts"
          placeholder="选择里程碑"
          filterable
        />
      </n-form-item-gi>
    </n-grid>
  </n-form>
</template>

<script>
import { ref, onMounted, onUnmounted, defineComponent } from 'vue';

import { updateAjax } from '@/assets/CRUD/update';
import installForm from '@/views/pmachine/modules/changeState/installForm.js';

export default defineComponent({
  props: {
    machineId: Number,
  },
  setup(props, context) {
    onMounted(() => {
      installForm.getProductOptions();
    });

    installForm.activeProductWatcher();
    installForm.activeVersionWatcher();

    onUnmounted(() => {
      installForm.clean();
    });

    return {
      ...installForm,
      handlePropsButtonClick: () => installForm.validateFormData(context),
      post: () => {
        updateAjax.putForm(
          `/v1/pmachine/${props.machineId}/install`,
          ref({
            milestone_id: installForm.formValue.value.milestone_id,
          })
        );
        context.emit('close');
      },
    };
  },
});
</script>

<style scoped></style>
