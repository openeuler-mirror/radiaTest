<template>
  <n-input-group>
    <n-input
      v-model:value="filterValue.name"
      :style="{ width: '24%' }"
      round
      placeholder="虚拟机名称"
    />
    <n-input
      v-model:value="filterValue.ip"
      size="large"
      :style="{ width: '15%' }"
      placeholder="IP地址"
    />
    <n-select
      v-model:value="filterValue.frame"
      size="large"
      :style="{ width: '12%' }"
      placeholder="架构"
      :options="[
        { label: 'aarch64', value: 'aarch64' },
        { label: 'x86_64', value: 'x86_64' },
      ]"
      clearable
    />
    <n-input
      v-model:value="filterValue.host_ip"
      :style="{ width: '12%' }"
      placeholder="宿主机 IP"
    />
    <n-input
      v-model:value="filterValue.description"
      :style="{ width: '25%' }"
      placeholder="使用描述"
    />
    <clear-input @clearAll="clearAll" />
  </n-input-group>
</template>

<script>
import { watch, defineComponent } from 'vue';
import { useStore } from 'vuex';

import ClearInput from '@/components/CRUD/ClearInput.vue';

import vmachineFilter from '@/views/vmachine/modules/vmachineFilter.js';

export default defineComponent({
  components: {
    ClearInput,
  },
  setup(props, context) {
    const store = useStore();

    const handleGroupInput = () => {
      context.emit('filterGroupInput');
    };

    watch(
      vmachineFilter.filterValue,
      () => {
        store.commit('filterVm/setAll', vmachineFilter.filterValue.value);
        handleGroupInput();
      },
      { deep: true }
    );

    return {
      ...vmachineFilter,
      handleGroupInput,
    };
  },
});
</script>

<style scoped></style>
