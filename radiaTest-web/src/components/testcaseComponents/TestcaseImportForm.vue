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
      <n-form-item-gi :span="18" v-if="showGroup" label="归属团队" path="group_id">
        <n-select
          v-model:value="model.group_id"
          placeholder="选择团队"
          :options="groupOptions"
          filterable
        />
      </n-form-item-gi>
      <!-- <n-form-item-gi
        :span="showGroup ? 9 : 18"
        label="测试框架"
        path="framework_id"
      >
        <n-select
          v-model:value="model.framework_id"
          placeholder="选择框架"
          :options="frameworkOptions"
          filterable
        />
      </n-form-item-gi> -->
    </n-grid>
  </n-form>
  <n-upload
    ref="uploadRef"
    max="1"
    :data="model"
    v-model:file-list="fileListRef"
    @change="handleUploadChange"
    :default-upload="false"
    @before-upload="beforeUpload"
    action="/api/v1/case/import"
  >
    <n-upload-dragger>
      <div style="margin-bottom: 12px">
        <n-icon size="48" :depth="3">
          <archive-icon />
        </n-icon>
      </div>
      <n-text style="font-size: 16px">点击或者拖动文件到该区域来上传</n-text>
      <n-p depth="3" style="margin: 8px 0 0 0">
        仅支持导入xlsx、csv、xls、md、markdown格式的文件，且表格列名需与平台标准保持一致
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
  props: {
    showGroup: {
      type: Boolean,
      default: true,
    },
  },
  components: {
    ArchiveIcon,
  },
  setup(props, context) {
    onMounted(() => importForm.initOptions());
    onUnmounted(() => importForm.clean());

    return {
      settings,
      ...importForm,
      handlePropsButtonClick: () => importForm.validateFormData(context),
      post: () => {
        if (props.showGroup) {
          importForm.uploadRef.value.submit();
          context.emit('close');
        } else {
          context.emit('submitForm', {
            data: importForm.model.value,
            file: importForm.fileListRef.value,
          });
        }
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
