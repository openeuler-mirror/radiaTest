<template>
  <n-modal v-model:show="showModal" :mask-closable="false">
    <vue3-draggable-resizable
      v-model:x="x"
      v-model:y="y"
      :draggable="draggable"
      :resizable="false"
      style="border-style: none"
    >
      <div
        class="dragArea"
        @mouseenter="draggable = true"
        @mouseleave="draggable = false"
      ></div>
      <n-card
        class="modalCard"
        :title="title"
        style="min-width: 680px; max-width: 1280px"
      >
        <slot name="form"></slot>
        <n-space class="NPbutton">
          <n-button
            size="large"
            type="error"
            @click="onNegativeClick"
            ghost
            v-if="showCancel"
          >
            {{ cancelText }}
          </n-button>
          <n-button
            size="large"
            type="primary"
            @click="onPositiveClick"
            ghost
            v-if="showConfirm"
          >
            {{ confirmText }}
          </n-button>
        </n-space>
      </n-card>
    </vue3-draggable-resizable>
  </n-modal>
</template>

<script>
import { ref, defineComponent } from 'vue';
import Vue3DraggableResizable from 'vue3-draggable-resizable';
import 'vue3-draggable-resizable/dist/Vue3DraggableResizable.css';

import config from '@/assets/config/dragableResizable.js';

export default defineComponent({
  components: {
    Vue3DraggableResizable,
  },
  props: {
    showConfirm: {
      type: Boolean,
      default: true
    },
    showCancel: {
      type: Boolean,
      default: true
    },
    cancelText: {
      type: String,
      default: '取消'
    },
    confirmText: {
      type: String,
      default: '提交'
    },
    title: String,
    initX: {
      default: 600,
      type: Number,
    },
    initY: {
      default: 300,
      type: Number,
    },
  },
  setup(props, context) {
    const showModal = ref(false);

    const x = ref(props.initX);
    const y = ref(props.initY);

    const onNegativeClick = () => {
      showModal.value = false;
    };
    const onPositiveClick = () => {
      context.emit('validate');
    };

    return {
      x,
      y,
      onNegativeClick,
      onPositiveClick,
      showModal,
      ...config,
      submitCreateForm() {
        context.emit('submit');
      },
      show() {
        showModal.value = true;
      },
      close() {
        showModal.value = false;
      },
    };
  },
});
</script>

<style scoped>
.modalCard {
  z-index: 2;
}
.NPbutton {
  position: relative;
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
