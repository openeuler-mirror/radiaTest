<template>
  <n-button type="error" size="large" round ghost @click="handleClick">
    <div id="clearInput">清空</div>
  </n-button>
</template>

<script>
import { defineComponent } from 'vue';

export default defineComponent({
  setup(props, context) {
    const handleClick = () => {
      context.emit('clearAll', 'clearAll');
    };
    return {
      handleClick,
    };
  },
});
</script>

<style scoped>
#clearInput {
  font-size: 16px;
  padding: 18px;
}
</style>
