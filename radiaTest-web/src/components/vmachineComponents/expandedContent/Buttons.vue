<template>
  <div v-if="status === 'running' || status === 'paused'">
    <n-button-group size="small" style="margin-right: 20px">
      <n-button
        :disabled="disabledAll"
        type="default"
        style="width: 90px"
        @click="handleClick(restartValue)"
      >
        {{ restartValue }}
      </n-button>
      <n-popselect
        v-model:value="restartValue"
        :options="restartOpts"
        trigger="click"
        placement="bottom-end"
      >
        <n-button type="default" style="width: 30px" :disabled="disabledAll">
          <n-icon>
            <chevron-down />
          </n-icon>
        </n-button>
      </n-popselect>
    </n-button-group>
    <n-button
      v-if="status !== 'paused'"
      :disabled="disabledAll"
      size="small"
      type="default"
      style="width: 90px; margin-right: 20px"
      @click="handleClick('suspend')"
    >
      suspend
    </n-button>
    <n-button
      v-else
      :disabled="disabledAll"
      size="small"
      type="success"
      style="width: 90px; margin-right: 20px"
      @click="handleClick('resume')"
    >
      resume
    </n-button>
    <n-button-group size="small" style="margin-right: 20px">
      <n-button
        :disabled="disabledAll"
        type="error"
        style="width: 90px"
        @click="handleClick(shutdownValue)"
      >
        {{ shutdownValue }}
      </n-button>
      <n-popselect
        v-model:value="shutdownValue"
        :options="shutdownOpts"
        trigger="click"
        placement="bottom-end"
      >
        <n-button
          type="error"
          style="width: 30px; border-left: 1px solid #fff"
          :disabled="disabledAll"
        >
          <n-icon>
            <chevron-down />
          </n-icon>
        </n-button>
      </n-popselect>
    </n-button-group>
  </div>
  <div v-else>
    <n-button
      size="small"
      type="primary"
      style="width: 120px; margin-right: 20px"
      :disabled="disabledAll"
      @click="handleClick('start')"
    >
      start
    </n-button>
  </div>
</template>

<script>
import { defineComponent } from 'vue';
import { ChevronDown } from '@vicons/ionicons5';

import buttons from '@/views/vmachine/modules/expandedContent/buttons.js';

export default defineComponent({
  components: {
    ChevronDown,
  },
  props: {
    id: Number,
    status: String,
  },
  setup(props) {
    const handleClick = (status) =>
      buttons.changeState(props.id, status);

    return {
      ...buttons,
      handleClick,
    };
  },
});
</script>

<style scoped></style>
