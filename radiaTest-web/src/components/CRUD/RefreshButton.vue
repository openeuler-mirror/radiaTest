<template>
  <n-popover trigger="hover">
    <template #trigger>
      <n-button
        ref="button"
        color="black"
        size="large"
        @click="handleClick"
        text
        circle
        ghost
      >
        <n-icon size="40" class="refresh-icon">
          <refresh />
        </n-icon>
      </n-button>
    </template>
    <slot></slot>
  </n-popover>
</template>

<script>
import { ref, defineComponent } from 'vue';
import { MdRefresh as Refresh } from '@vicons/ionicons4';

export default defineComponent({
  components: {
    Refresh,
  },
  setup(props, context) {
    const button = ref(null);
    return {
      button,
      handleClick() {
        context.emit('refresh');
      },
    };
  },
});
</script>

<style scoped>
.refresh-icon {
  display: inline-block !important;
  transition: rotate 0.8s linear;
}
.refresh-icon:hover {
  color: rgba(0, 47, 167, 1);
  animation: rotate 1s linear infinite forwards;
}
@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
