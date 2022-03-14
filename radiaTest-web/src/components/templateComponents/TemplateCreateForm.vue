<template>
  <n-card
    id="baseinfoCard"
    :title="createTitle('填写模板基础信息')"
    size="huge"
    :bordered="false"
    :segmented="{
      content: 'hard',
    }"
    header-style="
            font-size: 20px; 
            height: 40px;
            padding-top: 10px;
            padding-bottom: 10px; 
            font-family: 'v-sans'; 
            background-color: rgba(250,250,252,1);
        "
  >
    <div>
      <n-form
        inline
        :label-width="80"
        :model="formValue"
        :rules="rules"
        size="medium"
        ref="formRef"
      >
        <n-grid :cols="24" :x-gap="36">
          <n-form-item-gi :span="10" label="模板名" path="name">
            <n-input
              v-model:value="formValue.name"
              style="width: 90%"
              placeholder="模版名称不可与已有模板重复"
            />
            <n-icon
              size="20"
              color="rgba(23, 168, 88,1)"
              class="loading"
              v-show="loading"
            >
              <loading />
            </n-icon>
            <n-icon size="25" color="rgba(255,195,0,1)" v-show="warning">
              <warning />
            </n-icon>
          </n-form-item-gi>
          <n-gi :span="2"></n-gi>
          <n-form-item-gi :span="6" label="模板类型" path="template_type">
            <n-select
              :options="typeOpts"
              v-model:value="formValue.template_type"
              placeholder="选择模板类型"
            />
          </n-form-item-gi>
          <n-form-item-gi :span="6" label="权限归属" path="owner">
            <n-select
              :disabled="disabled"
              filterable
              v-model:value="formValue.owner"
              placeholder="请选择待测对象类型"
              :options="ownerOpts"
            />
          </n-form-item-gi>
          <n-form-item-gi :span="6" label="产品" path="product">
            <n-select
              :options="productOpts"
              v-model:value="formValue.product"
              placeholder="选择产品"
              filterable
            />
          </n-form-item-gi>
          <n-gi :span="6">
            <n-form-item label="版本" path="version">
              <n-select
                :options="versionOpts"
                v-model:value="formValue.version"
                placeholder="选择版本"
                filterable
              />
            </n-form-item>
          </n-gi>
          <n-form-item-gi :span="12" label="里程碑" path="milestone">
            <n-select
              :options="milestoneOpts"
              v-model:value="formValue.milestone"
              placeholder="选择模板绑定的里程碑"
              filterable
            />
          </n-form-item-gi>
          <n-form-item-gi :span="8" label="测试脚本代码仓" path="git_repo">
            <n-select
              :options="gitRepoOpts"
              v-model:value="formValue.git_repo"
              placeholder="选择模板绑定的测试脚本代码仓"
              @update:value="changeRepo"
              filterable
            />
          </n-form-item-gi>
          <n-form-item-gi :span="16" label="模板描述" path="description">
            <n-input v-model:value="formValue.description" />
          </n-form-item-gi>
        </n-grid>
      </n-form>
    </div>
  </n-card>
  <n-card
    id="suitesCard"
    :title="createTitle('绑定测试用例')"
    size="huge"
    :bordered="false"
    :segmented="{
      content: 'hard',
    }"
    header-style="
            font-size: 20px; 
            height: 40px;
            padding-top: 10px;
            padding-bottom: 10px; 
            font-family: 'v-sans'; 
            background-color: rgba(250,250,252,1);
        "
  >
    <n-tree-select
      multiple
      filterable
      cascade
      checkable
      clearable
      check-strategy="child"
      :options="options"
      v-model:value="casesValue"
    />
  </n-card>
</template>

<script>
import { onMounted, onUnmounted, defineComponent } from 'vue';

import { Loading3QuartersOutlined as Loading } from '@vicons/antd';
import { Warning } from '@vicons/ionicons5';

import { createTitle } from '@/assets/utils/createTitle';
import createForm from '@/views/template/modules/createForm.js';
import casesForm from '@/views/template/modules/casesForm.js';
import createAjax from '@/views/template/modules/createAjax.js';

export default defineComponent({
  components: {
    Loading,
    Warning,
  },
  setup(props, context) {
    onMounted(() => {
      // createAjax.getData(casesForm.options, casesForm.loading);
      createForm.getProductOptions();
    });

    createForm.activeProductWatcher();
    createForm.activeVersionWatcher();

    onUnmounted(() => {
      createForm.clean();
      casesForm.clean();
    });

    return {
      createTitle,
      ...createAjax,
      ...createForm,
      ...casesForm,
      handlePropsButtonClick: () => createForm.validateFormData(context),
      post: () => {
        createAjax.postForm(createForm.formValue, casesForm.casesValue);
        context.emit('close');
      },
    };
  },
});
</script>

<style scoped>
.loading {
  position: relative;
  left: 10px;
  animation: loading 1s linear infinite;
}
@keyframes loading {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
