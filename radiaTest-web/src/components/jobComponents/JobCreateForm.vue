<template>
  <n-card
    :title="createTitle('单包快速验证')"
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
          <n-form-item-gi :span="10" label="测试套" path="suite">
            <n-input v-model:value="formValue.suite" style="width: 90%" />
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
          <n-form-item-gi :span="6" label="机器类型" path="filetype">
            <n-select
              :options="[
                {
                  label: '物理机',
                  value: 'iso',
                },
                {
                  label: '虚拟机',
                  value: 'qcow2',
                },
              ]"
              v-model:value="formValue.filetype"
              placeholder="选择物理机/虚拟机"
            />
          </n-form-item-gi>
          <n-form-item-gi :span="6" label="架构" path="frame">
            <n-select
              filterable
              v-model:value="formValue.frame"
              placeholder="请选择架构"
              :options="[
                {
                  label: 'aarch64',
                  value: 'aarch64',
                },
                {
                  label: 'x86_64',
                  value: 'x86_64',
                },
              ]"
            />
          </n-form-item-gi>
        </n-grid>
      </n-form>
    </div>
  </n-card>
</template>

<script>
import { ref, onMounted, onUnmounted, defineComponent } from 'vue';

import { Loading3QuartersOutlined as Loading } from '@vicons/antd';
import { Warning } from '@vicons/ionicons5';

import { createTitle } from '@/assets/utils/createTitle';
import { createAjax } from '@/assets/CRUD/create';
import createForm from '@/views/job/modules/createForm.js';

export default defineComponent({
  components: {
    Loading,
    Warning,
  },
  setup(props, context) {
    onMounted(() => {
      createForm.getProductOptions();
    });

    createForm.activeProductWatcher();
    createForm.activeVersionWatcher();

    onUnmounted(() => {
      createForm.clean();
    });

    return {
      createTitle,
      ...createForm,
      handlePropsButtonClick: () => createForm.validateFormData(context),
      post: () => {
        createAjax.postForm(
          '/v1/job/suite',
          ref({
            milestone_id: createForm.formValue.value.milestone,
            filetype: createForm.formValue.value.filetype,
            frame: createForm.formValue.value.frame,
            testsuite: createForm.formValue.value.suite,
          })
        );
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
