<template>
  <n-form
    :label-width="40"
    :model="formValue"
    :rules="rules"
    :size="size"
    label-placement="top"
    ref="formRef"
  >
    <n-grid :cols="24">
      <n-form-item-gi :span="12" label="产品" path="name">
        <n-input
          v-model:value="formValue.name"
          placeholder="输入产品名"
          :style="{ width: '90%' }"
        />
      </n-form-item-gi>
      <n-form-item-gi :span="12" label="版本" path="version">
        <n-input
          v-model:value="formValue.version"
          placeholder="选择版本名"
          :style="{ width: '90%' }"
        />
      </n-form-item-gi>
      <n-form-item-gi :span="24" label="描述" path="description">
        <n-input
          v-model:value="formValue.description"
          placeholder="输入产品版本描述"
          :style="{ width: '95%' }"
        />
      </n-form-item-gi>
    </n-grid>
  </n-form>
</template>

<script>
import { computed, onMounted, defineComponent } from 'vue';
import { useStore } from 'vuex';

import validation from '@/assets/utils/validation.js';
import updateAjax from '@/assets/CRUD/update/updateAjax.js';
import updateForm from '@/views/product/modules/updateForm.js';

export default defineComponent({
  setup(porps, context) {
    const store = useStore();

    onMounted(() => {
      updateForm.formValue.value = computed(
        () => store.getters.getRowData
      ).value;
    });

    return {
      ...updateForm,
      handlePropsButtonClick: () => validation(updateForm.formRef, context),
      put: () => {
        updateAjax.putForm('/v1/product', updateForm.formValue);
        context.emit('close');
      },
    };
  },
});
</script>

<style scoped></style>
