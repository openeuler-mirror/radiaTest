<template>
  <n-modal v-model:show="showModal" :mask-closable="false">
    <vue3-draggable-resizable
      v-model:x="x"
      v-model:y="y"
      :initH="100"
      :draggable="draggable"
      :resizable="false"
      style="border-style: none"
    >
      <div
        class="dragArea"
        @mouseenter="draggable = true"
        @mouseleave="draggable = false"
      ></div>
      <n-card class="edit-card">
        <template #header>
          <span>{{ title }}</span>
          <span>修改</span>
        </template>
        <template #header-extra> {{ data.name }} </template>
        <div v-if="target === 'memory'">
          <mem-form :data="data" ref="form" />
        </div>
        <div v-if="target === 'vcpus'">
          <vcpus-form :data="data" ref="form" />
        </div>
        <div v-if="target === 'device'">
          <device-form :data="data" ref="form" />
        </div>
        <n-space class="NPbutton">
          <n-button size="large" type="error" @click="onNegativeClick" ghost
            >取消</n-button
          >
          <n-button size="large" type="primary" @click="onPositiveClick" ghost>
            提交
          </n-button>
        </n-space>
      </n-card>
    </vue3-draggable-resizable>
  </n-modal>
</template>

<script>
import { ref, defineComponent } from 'vue';
import { useMessage } from 'naive-ui';
import Vue3DraggableResizable from 'vue3-draggable-resizable';
import 'vue3-draggable-resizable/dist/Vue3DraggableResizable.css';

import VcpusForm from './editForms/VcpusForm';
import MemForm from './editForms/MemForm';
import DeviceForm from './editForms/DeviceForm';

export default defineComponent({
  components: {
    Vue3DraggableResizable,
    VcpusForm,
    MemForm,
    DeviceForm,
  },
  props: {
    data: Object,
  },
  // eslint-disable-next-line max-lines-per-function
  setup(props, context) {
    const message = useMessage();
    const showModal = ref(false);
    const draggable = ref(false);
    const x = ref(500);
    const y = ref(300);
    const form = ref(null);
    const title = ref(null);
    const target = ref(null);
    const changeShow = (t) => {
      showModal.value = true;
      target.value = t;
      if (t === 'memory') {
        title.value = '内存配置';
      } else if (t === 'vcpus') {
        title.value = '虚拟机CPU配置';
      } else if (t === 'device') {
        title.value = '特殊配置';
      } else {
        title.value = '磁盘Boot顺序';
      }
    };
    const onNegativeClick = () => {
      showModal.value = false;
    };
    const onPositiveClick = () => {
      if (target.value !== 'device') {
        form.value.$refs.form.validate((err) => {
          if (!err) {
            showModal.value = false;
            form.value.onValidSubmit(context);
          } else {
            message.error('请检查输入合法性');
          }
        });
      } else {
        form.value.submit(context);
        showModal.value = false;
      }
    };
    return {
      x,
      y,
      title,
      target,
      draggable,
      form,
      showModal,
      changeShow,
      onNegativeClick,
      onPositiveClick,
    };
  },
});
</script>

<style scoped>
.edit-card {
  width: max-content;
}
.dragArea {
  position: absolute;
  height: 60px;
  width: 100%;
  z-index: 3;
}
.dragArea:hover {
  cursor: grab;
}
</style>
