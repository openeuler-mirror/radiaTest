<template>
  <n-data-table
    remote
    ref="table"
    size="large"
    :bordered="false"
    :columns="columns"
    :data="data"
    :loading="loading"
    :pagination="pagination"
    :row-key="(row) => row.id"
    :row-props="(row) => rowProps(row)"
  />
</template>

<script>
import { ref, onMounted, onUnmounted, defineComponent } from 'vue';
import { useStore } from 'vuex';
import { Socket } from '@/socket';
import settings from '@/assets/config/settings.js';
import { get } from '@/assets/CRUD/read';
import { any2stamp } from '@/assets/utils/dateFormatUtils.js';
import testcaseTable from '@/views/caseManage/testcase/modules/testcaseTable.js';
import createColumns from '@/views/caseManage/testcase/modules/testcaseTableColumns.js';
import { workspace } from '@/assets/config/menu.js';

export default defineComponent({
  setup(props, context) {
    const store = useStore();
    const testcaseSocket = new Socket(
      `${settings.websocketProtocol}://${settings.serverPath}/case`
    );
    testcaseSocket.connect();
    onMounted(() => {
      getDatas();

      testcaseSocket.listen('update', () => {
        get.filterItem(
          `/v1/ws/${workspace.value}/case`,
          testcaseTable.totalData,
          testcaseTable.loading,
          {
            deleted: false,
          }
        );
      });
    });
    onUnmounted(() => {
      testcaseSocket.disconnect();
    });
    const getDatas = () => {
      let params = {
        page_num: pagination.value.page,
        page_size: pagination.value.pageSize,
        deleted: false,
      };
      get.filterItem(
        `/v1/ws/${workspace.value}/case`,
        testcaseTable.totalData,
        testcaseTable.loading,
        params
      );
    };
    const columns = ref(
      createColumns((row) => {
        let data = JSON.parse(JSON.stringify(row));
        data.start_time = any2stamp(data.start_time);
        data.end_time = any2stamp(data.end_time);
        store.commit('rowData/set', data);
        testcaseTable.isUpdating.value = true;
        context.emit('update', row);
      })
    );
    const pagination = ref({
      page: 1,
      pageSize: 10,
      pageCount: testcaseTable.pageCounts,
      showSizePicker: true,
      pageSizes: [5, 10, 20, 50],
      onChange: (page) => {
        pagination.value.page = page;
        getDatas();
      },
      onPageSizeChange: (pageSize) => {
        pagination.value.pageSize = pageSize;
        pagination.value.page = 1;
        getDatas();
      },
    });
    return {
      store,
      columns,
      ...testcaseTable,
      refreshData: () =>
        get.refresh(`/v1/ws/${workspace.value}/case`, testcaseTable.data, testcaseTable.loading),
      pagination,
    };
  },
});
</script>

<style>
.cols.suite {
  width: 10%;
}
.cols.case-name {
  width: 25%;
}
.cols.test-level {
  width: 8%;
}
.cols.test-type {
  width: 8%;
}
.cols.machine-num {
  width: 5%;
}
.cols.machine-type {
  width: 5%;
}
.cols.auto {
  width: 5%;
}
.cols.remark {
  width: 14%;
}
.cols.owner {
  width: 8%;
}
</style>
