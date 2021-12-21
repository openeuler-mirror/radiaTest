<template>
  <n-button
    id="create"
    type="primary"
    size="large"
    @mouseenter="handleEnter"
    @mouseleave="handleLeave"
    round
  >
    <rotate-icon ref="icon" />
    {{ title }}
  </n-button>
</template>

<script>
import { defineComponent } from 'vue';
import RotateIcon from '@/components/public/RotateIcon';

import { createIcon } from '@/assets/CRUD/create';

export default defineComponent({
  components: {
    RotateIcon,
  },
  props: {
    title: String,
  },
  setup() {
    return {
      ...createIcon,
    };
  },
});
</script>

<style scoped>
#create {
  font-size: 20px;
}
</style>
