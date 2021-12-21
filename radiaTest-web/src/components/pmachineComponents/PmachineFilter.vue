<template>
  <n-input-group>
    <n-input
      v-model:value="filterValue.mac"
      :style="{ width: '13%' }"
      @input="handleMacInput"
      round
      placeholder="MAC地址"
    />
    <n-select
      v-model:value="filterValue.frame"
      size="large"
      :style="{ width: '7.5%' }"
      placeholder="架构"
      :options="[
        { label: 'aarch64', value: 'aarch64' },
        { label: 'x86_64', value: 'x86_64' },
      ]"
      clearable
    />
    <n-input
      v-model:value="filterValue.sshIp"
      :style="{ width: '10%' }"
      placeholder="IP地址"
    />
    <n-input
      v-model:value="filterValue.bmcIp"
      :style="{ width: '10%' }"
      placeholder="BMC IP"
    />
    <n-input
      v-model:value="filterValue.occupier"
      :style="{ width: '9%' }"
      round
      placeholder="当前使用人"
    />
    <n-select
      v-model:value="filterValue._state"
      size="large"
      :style="{ width: '9%' }"
      placeholder="占用状态"
      :options="[
        { label: '占用', value: 'occupied' },
        { label: '释放', value: 'idle' },
      ]"
      clearable
    />
    <n-input
      v-model:value="filterValue.description"
      :style="{ width: '10%' }"
      round
      placeholder="使用说明"
    />
    <clear-input @clearAll="clearAll" />
  </n-input-group>
</template>

<script>
import { watch, defineComponent } from 'vue';
import { useStore } from 'vuex';

import ClearInput from '@/components/CRUD/ClearInput.vue';

import { macInput } from '@/assets/utils/formUtils.js';
import pmachineFilter from '@/views/pmachine/modules/pmachineFilter.js';

export default defineComponent({
  components: {
    ClearInput,
  },
  setup() {
    const store = useStore();

    watch(
      pmachineFilter.filterValue,
      () => {
        store.commit('filterPm/setAll', pmachineFilter.filterValue.value);
      },
      { deep: true }
    );

    return {
      ...pmachineFilter,
      handleMacInput: () => macInput(pmachineFilter.filterValue),
    };
  },
});
</script>

<style scoped></style>
