<template>
  <n-modal v-model:show="showModal" :mask-closable="false">
    <n-card
      :title="createTitle('应用模板')"
      size="large"
      :bordered="false"
      :segmented="{
        content: true
      }"
      style="width: 500px"
    >
      <n-form
        label-placement="left"
        :label-width="80"
        :model="formValue"
        :rules="formRules"
        size="medium"
        ref="formRef"
      >
        <n-grid :cols="12">
          <n-form-item-gi :span="12" label="模板名" path="templateName">
            <n-select
              v-model:value="formValue.templateName"
              placeholder="请选择模板"
              :options="templateOptions"
              clearable
            />
          </n-form-item-gi>
        </n-grid>
      </n-form>
      <n-space>
        <n-button size="medium" type="error" @click="onNegativeClick" ghost> 取消 </n-button>
        <n-button size="medium" type="primary" @click="onPositiveClick" ghost> 提交 </n-button>
      </n-space>
    </n-card>
  </n-modal>
</template>

<script setup>
import { createTitle } from '@/assets/utils/createTitle';
import { getStrategyTemplate } from '@/api/get';
import { applyStrategyTemplate } from '@/api/post';

const props = defineProps(['currentFeature']);
const { currentFeature } = toRefs(props);
const emits = defineEmits(['applyTemplateCb']);
const showModal = ref(false);
const formRef = ref(null);
const formValue = ref({
  templateName: null
});
const formRules = ref({
  templateName: {
    required: true,
    type: 'number',
    trigger: ['blur', 'change'],
    message: '请选择模板'
  }
});
const templateOptions = ref([]); // 模板列表

// 取消应用模板
const onNegativeClick = () => {
  showModal.value = false;
  formValue.value = {
    templateName: null
  };
};

// 确认应用模板
const onPositiveClick = (e) => {
  e.preventDefault();
  formRef.value?.validate((errors) => {
    if (!errors) {
      applyStrategyTemplate(formValue.value.templateName, currentFeature.value.info.product_feature_id).then(() => {
        emits('applyTemplateCb');
        onNegativeClick();
      });
    } else {
      console.log(errors);
    }
  });
};

// 查询模板
const getStrategyTemplateFn = () => {
  getStrategyTemplate()
    .then((res) => {
      templateOptions.value = [];
      res?.data?.forEach((item) => {
        templateOptions.value.push({
          value: item.id,
          label: item.title
        });
      });
    })
    .catch(() => {
      templateOptions.value = [];
    });
};

onMounted(() => {
  getStrategyTemplateFn();
});

defineExpose({
  showModal
});
</script>

<style scoped lang="less"></style>
