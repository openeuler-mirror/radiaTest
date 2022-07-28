<template>
  <n-icon id="icon" :class="status" size="24">
    <add />
  </n-icon>
</template>

<script>
import { ref, defineComponent } from 'vue';
import { Add20Filled as Add } from '@vicons/fluent';

export default defineComponent({
  components: {
    Add,
  },
  setup() {
    const status = ref('freeze');
    const rotate = () => {
      status.value = 'rotate';
    };
    const reverse = () => {
      status.value = 'reverse';
    };
    return {
      status,
      reverse,
      rotate,
    };
  },
});
</script>

<style scoped>
.rotate {
  animation: rotate 1s;
}
@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(180deg);
  }
}
.reverse {
  animation: reverse 1s;
}
@keyframes reverse {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(-180deg);
  }
}
</style>
