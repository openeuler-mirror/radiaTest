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
          <n-form-item-gi :span="25" label="任务名" path="name">
            <n-input v-model:value="formValue.name" placeholder="默认任务名: Job-{milestone}-{frame}-{Y}-{m}-{d}-{H}-{M}-{S}" />
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
          <n-form-item-gi :span="6" label="测试框架" path="framework">
            <n-select
              :options="frameworkOpts"
              v-model:value="formValue.framework"
              @update:value="frameworkChange"
              placeholder="选择测试框架"
            />
          </n-form-item-gi>
          <n-form-item-gi :span="9" label="测试脚本代码仓" path="git_repo_id">
            <n-select
              :options="repoOpts"
              v-model:value="formValue.git_repo_id"
              @update:value="repoChange"
              placeholder="选择测试脚本代码仓"
            />
          </n-form-item-gi>
          <n-form-item-gi :span="9" label="测试套" path="suite">
            <n-select
              :options="suiteOpts"
              v-model:value="formValue.suite"
              :render-option="renderSuiteOption"
              placeholder="选择测试套"
              @update:value="changeSuite"
              filterable
            />
            <!-- <n-input v-model:value="formValue.suite" style="width: 90%" />
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
            </n-icon> -->
          </n-form-item-gi>
          <n-form-item-gi :span="6" label="选取策略" path="select_mode">
            <n-select
              :options="[
                {
                  label: '全自动选取',
                  value: 'auto',
                },
                {
                  label: '人工干预',
                  value: 'manual',
                },
              ]"
              v-model:value="formValue.select_mode"
              placeholder="选取策略"
            />
          </n-form-item-gi>
          <n-form-item-gi
            v-if="formValue.select_mode === 'manual'"
            :span="4"
            label="是否严格模式"
            path="strict_mode"
          >
            <n-switch v-model:value="formValue.strict_mode">
              <template #checked> 是 </template>
              <template #unchecked> 否 </template>
            </n-switch>
          </n-form-item-gi>
          <n-form-item-gi
            :span="8"
            label="已选机器"
            path="machine_list"
            v-if="formValue.select_mode === 'manual'"
          >
            <n-select
              filterable
              :value="formValue.machine_list"
              @update:value="selectPm"
              placeholder="请选择机器"
              :options="machineOptions"
              multiple
            >
              <template #arrow>
                {{ formValue.machine_list.length }}/{{ totalMachineCount }}
              </template>
            </n-select>
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

// import { Loading3QuartersOutlined as Loading } from '@vicons/antd';
// import { Warning } from '@vicons/ionicons5';

import { createTitle } from '@/assets/utils/createTitle';
import { createAjax } from '@/assets/CRUD/create';
import createForm from '@/views/job/modules/createForm.js';

export default defineComponent({
  // components: {
  //   Loading,
  //   Warning,
  // },
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
        let machineInfo;
        if (createForm.isPmachine.value) {
          machineInfo = { 
            pmachine_list: createForm.formValue.value.machine_list 
          };
        }else{
          machineInfo = { 
            vmachine_list: createForm.formValue.value.machine_list 
          };
        }
        createAjax.postForm(
          '/v2/job/suite',
          ref(Object.assign({
            milestone_id: createForm.formValue.value.milestone,
            name: createForm.formValue.value.name,
            frame: createForm.formValue.value.frame,
            suite_id: createForm.formValue.value.suite,
            git_repo_id: createForm.formValue.value.git_repo_id,
            strict_mode:createForm.formValue.value.strict_mode,
            machine_policy:createForm.formValue.value.select_mode, 
          },machineInfo))
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
