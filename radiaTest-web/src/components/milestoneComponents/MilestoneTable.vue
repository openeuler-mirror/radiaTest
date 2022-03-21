<template>
  <n-data-table
    remote
    ref="table"
    size="large"
    :bordered="false"
    :columns="columns"
    :data="data"
    :loading="loading"
    :row-key="(row) => row.id"
    :row-props="(row) => rowProps(row)"
    @update:checked-row-keys="(keys) => handleCheck(keys)"
    :pagination="pagination"
    @update:page="changePage"
  />
</template>

<script>
import { ref, onMounted, onUnmounted, defineComponent } from 'vue';
import { useStore } from 'vuex';
import { Socket } from '@/socket';

import settings from '@/assets/config/settings.js';
import { get, selection } from '@/assets/CRUD/read';
import { any2stamp } from '@/assets/utils/dateFormatUtils.js';
import milestoneTable from '@/views/milestone/modules/milestoneTable.js';
import createColumns from '@/views/milestone/modules/milestoneTableColumns.js';

export default defineComponent({
  setup(props, context) {
    const store = useStore();
    const milestoneSocket = new Socket(`ws://${settings.serverPath}/milestone`);
    milestoneSocket.connect();
    onMounted(() => {
      get.list(
        '/v2/milestone',
        milestoneTable.totalData,
        milestoneTable.loading,
        milestoneTable.filter.value,
        milestoneTable.pagination
      );
      milestoneSocket.listen('update', () => {
        get.list(
          '/v2/milestone',
          milestoneTable.totalData,
          milestoneTable.loading,
          milestoneTable.filter.value,
          milestoneTable.pagination
        );
      });
    });
    onUnmounted(() => {
      milestoneSocket.disconnect();
    });
    const columns = ref(
      createColumns((row) => {
        let data = JSON.parse(JSON.stringify(row));
        data.start_time = any2stamp(data.start_time);
        data.end_time = any2stamp(data.end_time);
        store.commit('rowData/set', data);
        milestoneTable.isUpdating.value = true;
        context.emit('update', row);
      })
    );
    return {
      store,
      columns,
      ...milestoneTable,
      showSelection: () => selection.show(columns),
      offSelection: () => selection.off(columns),
      refreshData: () =>
        get.refresh(
          '/v2/milestone',
          milestoneTable.data,
          milestoneTable.loading,
          milestoneTable.filter.value
        ),
    };
  },
});
</script>

<style>
.cols.product-name {
  width: 10% !important;
}
.cols.product-version {
  width: 10% !important;
}
.cols .milestone-name {
  width: 20% !important;
}
.cols .milestone-type {
  width: 5% !important;
}
.cols .start-time {
  width: 8% !important;
}
.cols .end-time {
  width: 8% !important;
}
.cols .task {
  width: 5% !important;
}
</style>
