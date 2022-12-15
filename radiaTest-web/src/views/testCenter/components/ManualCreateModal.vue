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
                <n-form-item-gi :span="24" label="用例" path="case_id">
                  <n-select
                    v-model:value="formValue.case_id"
                    placeholder="请选择用例"
                    :options="caseOptions"
                    clearable
                  />
                </n-form-item-gi>
                <n-form-item-gi :span="24" label="里程碑" path="milestone_id">
                  <n-select
                    v-model:value="formValue.milestone_id"
                    placeholder="请选择里程碑"
                    :options="milestoneOptions"
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
import { getCasePrecise, getMilestones } from '@/api/get';
import { createManualJob } from '@/api/post';

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
  case_id: null,
  milestone_id: null
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
const caseOptions = ref([]);
const milestoneOptions = ref([]);

const onNegativeClick = () => {
  showModal.value = false;
  formValue.value = {
    name: '',
    case_id: null,
    milestone_id: null
  };
};
const onPositiveClick = () => {
  formRef.value?.validate((errors) => {
    if (!errors) {
      createManualJob({
        case_id: formValue.value.case_id,
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
  getCasePrecise().then((res) => {
    caseOptions.value = [];
    res.data.forEach((v) => {
      caseOptions.value.push({
        label: v.name,
        value: v.id
      });
    });
  });
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
