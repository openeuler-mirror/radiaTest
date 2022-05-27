<template>
  <n-tooltip trigger="hover">
    <template #trigger>
      <n-button
        :disabled="disabled"
        v-show="status === 'on'"
        size="medium"
        type="error"
        @click="handleClick"
        circle
      >
        <n-icon size="18">
          <power-off />
        </n-icon>
      </n-button>
    </template>
    下电
  </n-tooltip>
  <n-tooltip trigger="hover">
    <template #trigger>
      <n-button
        :disabled="disabled"
        v-show="status === 'off'"
        size="medium"
        color="#038F03"
        @click="handleClick"
        circle
      >
        <n-icon size="18">
          <power-off />
        </n-icon>
      </n-button>
    </template>
    上电
  </n-tooltip>
</template>

<script>
import { toRefs, defineComponent } from 'vue';
import { PowerOff } from '@vicons/fa';

import { handlePowerClick } from '@/views/pmachine/modules/changeState/power.js';

export default defineComponent({
  components: {
    PowerOff,
  },
  props: {
    id: Number,
    status: String,
    disabled: {
      type: Boolean,
      default: false
    }
  },
  setup(props) {
    const { disabled } = toRefs(props);

    return {
      handleClick: () => handlePowerClick(props.id, props.status, disabled),
    };
  },
});
</script>

<style scoped></style>
