<template>
  <n-form
    :label-width="40"
    :model="contentFormValue"
    :rules="contentRules"
    :size="size"
    label-placement="top"
    ref="contentFormRef"
  >
    <n-grid :cols="18" :x-gap="24">
      <n-form-item-gi :span="18" label="用例描述" path="description">
        <n-input
          v-model:value="contentFormValue.description"
          type="textarea"
          :autosize="{
            minRows: 2,
          }"
          placeholder="请准确描述此用例"
        />
      </n-form-item-gi>
      <n-form-item-gi :span="18" label="预置条件" path="preset">
        <n-input
          v-model:value="contentFormValue.preset"
          type="textarea"
          :autosize="{
            minRows: 2,
          }"
        />
      </n-form-item-gi>
      <n-form-item-gi :span="18" label="操作步骤" path="steps">
        <n-input
          v-model:value="contentFormValue.steps"
          type="textarea"
          :autosize="{
            minRows: 4,
          }"
        />
      </n-form-item-gi>
      <n-form-item-gi :span="18" label="预期结果" path="expection">
        <n-input
          v-model:value="contentFormValue.expection"
          type="textarea"
          :autosize="{
            minRows: 3,
          }"
        />
      </n-form-item-gi>
    </n-grid>
  </n-form>
</template>

<script>
import { ref, onMounted, onUnmounted, defineComponent } from 'vue';

import validation from '@/assets/utils/validation.js';
import { updateAjax } from '@/assets/CRUD/update';
import updateContentForm from '@/views/caseManage/testcase/modules/updateContentForm.js';

export default defineComponent({
  props: {
    rowData: Object,
  },
  setup(props, context) {
    onMounted(() => {
      updateContentForm.initData(props.rowData);
    });
    onUnmounted(() => {
      updateContentForm.clean();
    });

    return {
      ...updateContentForm,
      handlePropsButtonClick: () =>
        validation(updateContentForm.contentFormRef, context),
      put: () => {
        const contentCopyData = JSON.parse(
          JSON.stringify(updateContentForm.contentFormValue.value)
        );
        const putData = ref(contentCopyData);
        updateAjax.putForm('/v1/case', putData);
        context.emit('close');
      },
    };
  },
});
</script>

<style scoped></style>
