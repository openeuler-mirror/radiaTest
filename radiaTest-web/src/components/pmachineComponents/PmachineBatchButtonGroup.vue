<template>
  <batch-button class="batch-button" type="info" text="占用">
    <template #icon>
      <n-icon #="icon" size="20">
        <connect />
      </n-icon>
    </template>
  </batch-button>
  <batch-button class="batch-button" type="info" text="释放">
    <template #icon>
      <n-icon #="icon" size="20">
        <disconnect />
      </n-icon>
    </template>
  </batch-button>
  <batch-button class="batch-button" type="error" text="下电">
    <template #icon>
      <n-icon #="icon" size="20">
        <power-off />
      </n-icon>
    </template>
  </batch-button>
  <batch-button class="batch-button" type="primary" text="上电">
    <template #icon>
      <n-icon #="icon" size="20">
        <power-off />
      </n-icon>
    </template>
  </batch-button>
</template>

<script>
import { defineComponent } from 'vue';

import {
  Connector20Filled as Connect,
  PlugDisconnected20Filled as Disconnect,
} from '@vicons/fluent';
import { PowerOff } from '@vicons/fa';

import BatchButton from '@/components/CRUD/BatchButton.vue';

export default defineComponent({
  components: {
    BatchButton,
    Connect,
    Disconnect,
    PowerOff,
  },
  setup() {},
});
</script>

<style scoped>
.batch-button {
  margin-right: 20px;
}
</style>
