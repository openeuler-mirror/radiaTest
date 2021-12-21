<template>
  <n-button
    class="selection"
    text
    v-show="!showSelection"
    @click="handleShowSelection"
  >
    选择
  </n-button>
  <n-button
    class="selection"
    text
    v-show="showSelection"
    @click="handleOffSelection"
  >
    隐藏
  </n-button>
</template>

<script>
import { ref, onMounted, defineComponent } from 'vue';

export default defineComponent({
  props: {
    left: {
      type: Number,
      default: 42,
    },
    top: {
      type: Number,
      default: 145,
    },
  },
  setup(props, context) {
    const showSelection = ref(false);

    onMounted(() => {
      document.getElementsByClassName(
        'selection'
      )[0].style.left = `${props.left}px`;
      document.getElementsByClassName(
        'selection'
      )[0].style.top = `${props.top}px`;
      document.getElementsByClassName(
        'selection'
      )[1].style.left = `${props.left}px`;
      document.getElementsByClassName(
        'selection'
      )[1].style.top = `${props.top}px`;
    });

    return {
      showSelection,
      handleShowSelection() {
        context.emit('show');
        showSelection.value = true;
      },
      handleOffSelection() {
        context.emit('off');
        showSelection.value = false;
      },
    };
  },
});
</script>

<style scope>
.selection {
  z-index: 1;
  position: relative;
}
</style>
