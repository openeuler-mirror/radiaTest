<template>
  <n-data-table
    size="large"
    :bordered="false"
    :columns="columns"
    :data="data"
    :loading="loading"
    :row-key="(row) => row.id"
    @update:expanded-row-keys="handleExpand"
    @update:checked-row-keys="(rowKey) => handleCheck(rowKey)"
    @update:sorter="handleSorterChange"
  />
</template>

<script>
import { ref, onMounted, onUnmounted, defineComponent } from 'vue';
import { useStore } from 'vuex';
import { Socket } from '@/socket';

import settings from '@/assets/config/settings.js';
import { get, selection } from '@/assets/CRUD/read';
import { createColumns } from '@/views/vmachine/modules/vmachineTableColumns.js';
import vmachineTable from '@/views/vmachine/modules/vmachineTable.js';

export default defineComponent({
  setup() {
    const store = useStore();
    const columns = ref(createColumns());
    const vmachineSocket = new Socket(`ws://${settings.serverPath}/vmachine`);
    vmachineSocket.connect();

    onMounted(() => {
      get.list('/v1/vmachine', vmachineTable.totalData, vmachineTable.loading);
      vmachineSocket.listen('update', () => {
        get.list('/v1/vmachine', vmachineTable.totalData, vmachineTable.loading);
      });
    });
    onUnmounted(() => {
      vmachineSocket.disconnect();
    });

    return {
      store,
      columns,
      ...vmachineTable,
      showSelection: () => selection.show(columns),
      offSelection: () => selection.off(columns),
      refreshData: () =>
        get.refresh(
          '/v1/vmachine',
          vmachineTable.totalData,
          vmachineTable.loading
        ),
      handleSorterChange: (sorter) =>
        vmachineTable.sorterChange(sorter, columns),
    };
  },
});
</script>

<style>
/* .end-time {
  width: 10%;
}
.vm-name {
  width: 18%;
}
.cols.vmachine-operation {
  width: 10%;
} */
</style>
