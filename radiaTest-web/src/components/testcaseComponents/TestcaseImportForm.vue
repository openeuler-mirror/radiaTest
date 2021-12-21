<template>
  <n-form
    :label-width="40"
    :model="model"
    :rules="rules"
    :size="size"
    label-placement="top"
    ref="formRef"
  >
    <n-grid :cols="18" :x-gap="24">
      <n-form-item-gi :span="18" label="默认归属测试套" path="suite">
        <n-select
          v-model:value="model.suite"
          placeholder="为文件中测试套属性为空的用例赋予默认测试套"
          :options="suiteOptions"
          filterable
        />
      </n-form-item-gi>
    </n-grid>
  </n-form>
  <n-upload
    ref="uploadRef"
    multiple
    :data="model"
    v-model:file-list="fileListRef"
    @change="handleUploadChange"
    :default-upload="false"
    @before-upload="beforeUpload"
    action="/api/v1/case/import"
  >
    <n-upload-dragger>
      <div style="margin-bottom: 12px;">
        <n-icon size="48" :depth="3">
          <archive-icon />
        </n-icon>
      </div>
      <n-text style="font-size: 16px;">点击或者拖动文件到该区域来上传</n-text>
      <n-p depth="3" style="margin: 8px 0 0 0;">
        仅支持导入xlsx、csv、xls格式的Excel文件，且表格列名需与平台保持一致
      </n-p>
    </n-upload-dragger>
  </n-upload>
</template>

<script>
import { onMounted, onUnmounted, defineComponent } from 'vue';

import { ArchiveOutline as ArchiveIcon } from '@vicons/ionicons5';

import settings from '@/assets/config/settings.js';
import importForm from '@/views/caseManage/testcase/modules/importForm.js';

export default defineComponent({
  components: {
    ArchiveIcon,
  },
  setup(props, context) {
    onMounted(() => importForm.initSuiteOptions());
    onUnmounted(() => importForm.clean());

    return {
      settings,
      ...importForm,
      handlePropsButtonClick: () => importForm.validateFormData(context),
      post: () => {
        importForm.uploadRef.value.submit();
        context.emit('close');
      },
    };
  },
});
</script>

<style>
.n-upload-trigger {
  display: block;
}
</style>
