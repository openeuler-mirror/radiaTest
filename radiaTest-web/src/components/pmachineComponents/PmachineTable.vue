<template>
  <n-data-table
    remote
    ref="table"
    size="large"
    :bordered="false"
    :columns="columns"
    :data="data"
    :loading="loading"
    :row-class-name="(row) => row.state"
    :row-key="(row) => row.id"
    @update:expanded-row-keys="handleExpand"
    @update:checked-row-keys="(keys) => handleCheck(keys, store)"
    @update:sorter="handleSorterChange"
  />
</template>

<script>
import { ref, onMounted, onUnmounted, defineComponent } from 'vue';
import { useStore } from 'vuex';
import { Socket } from '@/socket';

import settings from '@/assets/config/settings.js';
import { get, selection } from '@/assets/CRUD/read';
import pmachineTable from '@/views/pmachine/modules/pmachineTable.js';
import { createColumns } from '@/views/pmachine/modules/pmachineTableColumns.js';

export default defineComponent({
  setup(props, context) {
    const store = useStore();
    const pmachineSocket = new Socket(`ws://${settings.serverPath}/pmachine`);
    pmachineSocket.connect();

    onMounted(() => {
      get.list('/v1/pmachine', pmachineTable.totalData, pmachineTable.loading);
      pmachineSocket.listen('update', (res) => {
        pmachineTable.totalData.value = JSON.parse(res);
      });
    });
    onUnmounted(() => {
      pmachineSocket.disconnect();
    });

    const updateHandler = (row) => {
      store.commit('rowData/set', JSON.parse(JSON.stringify(row)));
      context.emit('update', row);
    };

    const columns = ref(createColumns(updateHandler));

    return {
      store,
      columns,
      ...pmachineTable,
      showSelection: () => selection.show(columns),
      offSelection: () => selection.off(columns),
      refreshData: () =>
        get.refresh(
          '/v1/pmachine',
          pmachineTable.totalData,
          pmachineTable.loading
        ),
    };
  },
});
</script>

<style>
.state {
  transition: all 0.4s linear;
}
.idle .state {
  background-color: rgb(3, 143, 3) !important;
  color: white !important;
  text-align: center !important;
  font-weight: 700 !important;
}
.occupied .state {
  background-color: rgb(146, 9, 9) !important;
  color: white !important;
  text-align: center !important;
  font-weight: 700 !important;
}
.cols.mac {
  width: 11.5%;
}
.cols.frame {
  width: 6.7%;
}
.cols.state {
  width: 9%;
}
.cols.ip {
  width: 10%;
}
.cols.bmcip {
  width: 10%;
}
.cols.occupier {
  width: 9%;
}
.cols.des {
  width: 9%;
}
.cols.endtime {
  width: 18%;
}
.operation {
  justify-content: center !important;
}
</style>
