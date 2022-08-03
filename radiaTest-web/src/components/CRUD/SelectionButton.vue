<template>
  <div class="selectionWrap">
    <n-icon size="16"><ChecklistFilled /></n-icon>&nbsp;
    <n-button class="selection" text v-show="!showSelection" @click="handleShowSelection">
      选择
    </n-button>
    <n-button class="selection" text v-show="showSelection" @click="handleOffSelection">
      隐藏
    </n-button>
  </div>
</template>

<script>
import { ref, defineComponent } from 'vue';
import { ChecklistFilled } from '@vicons/material';

export default defineComponent({
  components: { ChecklistFilled },
  setup(props, context) {
    const showSelection = ref(false);

    return {
      showSelection,
      handleShowSelection() {
        context.emit('show');
        showSelection.value = true;
      },
      handleOffSelection() {
        context.emit('off');
        showSelection.value = false;
      }
    };
  }
});
</script>

<style scope lang="less">
.selectionWrap {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 50px;
  cursor: pointer;
}
</style>
