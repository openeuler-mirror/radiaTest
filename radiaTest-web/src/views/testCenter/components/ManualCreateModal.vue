<template>
  <n-modal v-model:show="showModal" :mask-closable="false">
    <vue3-draggable-resizable
      v-model:x="x"
      v-model:y="y"
      :draggable="draggable"
      :resizable="false"
      style="border-style: none"
    >
      <div class="dragArea" @mouseenter="draggable = true" @mouseleave="draggable = false"></div>
      <n-card class="modalCard" style="min-width: 680px; max-width: 1280px">
        <n-card
          :title="createTitle('创建手工测试任务')"
          size="huge"
          :bordered="false"
          :segmented="{
            content: 'hard'
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
            <n-form inline :label-width="80" :model="formValue" :rules="rules" size="medium" ref="formRef">
              <n-grid :cols="24" :x-gap="36">
                <n-form-item-gi :span="24" label="任务名" path="name">
                  <n-input v-model:value="formValue.name" placeholder="请输入任务名" />
                </n-form-item-gi>
                <n-form-item-gi :span="24" label="里程碑" path="milestone_id">
                  <n-select
                    v-model:value="formValue.milestone_id"
                    placeholder="请选择里程碑"
                    :options="milestoneOptions"
                    clearable
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
                    :disabled="!formValue.framework"
                    placeholder="选择测试脚本代码仓"
                  />
                </n-form-item-gi>
                <n-form-item-gi :span="9" label="测试套" path="suite">
                  <n-select
                    :options="suiteOpts"
                    v-model:value="formValue.suite"
                    placeholder="选择测试套"
                    :disabled="!formValue.git_repo_id"
                    @update:value="changeSuite"
                    filterable
                  />
                </n-form-item-gi>
                <n-form-item-gi :span="24" label="用例" path="case_id">
                  <n-select
                    v-model:value="formValue.case_id"
                    placeholder="请选择用例"
                    :options="caseOptions"
                    :disabled="!formValue.suite"
                    filterable
                    clearable
                  />
                </n-form-item-gi>
              </n-grid>
            </n-form>
          </div>
        </n-card>
        <n-space>
          <n-button size="large" type="error" @click="onNegativeClick" ghost> 取消 </n-button>
          <n-button size="large" type="primary" @click="onPositiveClick" ghost> 提交 </n-button>
        </n-space>
      </n-card>
    </vue3-draggable-resizable>
  </n-modal>
</template>

<script setup>
import Vue3DraggableResizable from 'vue3-draggable-resizable';
import 'vue3-draggable-resizable/dist/Vue3DraggableResizable.css';
import config from '@/assets/config/dragableResizable.js';
import { createTitle } from '@/assets/utils/createTitle';
import { getMilestones, getFramework } from '@/api/get';
import { createManualJob } from '@/api/post';
import { createRepoOptions, createSuiteOptions, createCaseOptions } from '@/assets/utils/getOpts';

const emit = defineEmits(['updateTable']);
const props = defineProps({
  initX: {
    default: 400,
    type: Number
  },
  initY: {
    default: 200,
    type: Number
  }
});
const x = ref(props.initX);
const y = ref(props.initY);
const showModal = ref(false);
const { draggable } = toRefs(config);
const formRef = ref(null);
const formValue = ref({
  name: '',
  milestone_id: null,
  framework: null,
  git_repo_id: null,
  suite: null,
  case_id: null
});
const rules = ref({
  name: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入任务名'
  },
  case_id: {
    required: true,
    type: 'number',
    trigger: ['blur', 'change'],
    message: '请选择用例'
  },
  milestone_id: {
    required: true,
    type: 'number',
    trigger: ['blur', 'change'],
    message: '请选择里程碑'
  }
});
const milestoneOptions = ref([]);
const repoOpts = ref();
const frameworkOpts = ref([]);
const suiteOpts = ref();
const caseOptions = ref([]);

const getFrameworkFunc = () => {
  getFramework().then((res) => {
    frameworkOpts.value = res.data?.map((item) => ({
      label: item.name,
      value: String(item.id)
    }));
  });
};

const frameworkChange = async (value) => {
  repoOpts.value = await createRepoOptions({ framework_id: value });
};

const repoChange = async (value) => {
  suiteOpts.value = await createSuiteOptions({
    git_repo_id: value
  });
};

const changeSuite = async (value) => {
  formValue.value.case_id = null;
  caseOptions.value = await createCaseOptions({
    suite_id: value
  });
};

const onNegativeClick = () => {
  showModal.value = false;
  formValue.value = {
    name: '',
    milestone_id: null,
    framework: null,
    git_repo_id: null,
    suite: null,
    case_id: null
  };
};
const onPositiveClick = () => {
  formRef.value?.validate((errors) => {
    if (!errors) {
      createManualJob({
        cases: formValue.value.cases,
        name: formValue.value.name,
        milestone_id: formValue.value.milestone_id
      }).then(() => {
        onNegativeClick();
        emit('updateTable');
      });
    }
  });
};

const init = () => {
  getFrameworkFunc();
  getMilestones({ paged: false }).then((res) => {
    milestoneOptions.value = [];
    res.data.items.forEach((v) => {
      milestoneOptions.value.push({
        label: v.name,
        value: v.id
      });
    });
  });
};

onMounted(() => {
  init();
});

defineExpose({
  showModal
});
</script>

<style scoped lang="less">
.modalCard {
  z-index: 2;
}
.dragArea {
  position: absolute;
  height: 60px;
  width: 100%;
  z-index: 3;
  &:hover {
    cursor: grab;
  }
}
</style>
