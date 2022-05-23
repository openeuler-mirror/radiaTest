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
  />
</template>

<script>
import { ref, onMounted, onUnmounted, defineComponent } from 'vue';
import { useStore } from 'vuex';
import { Socket } from '@/socket';

import settings from '@/assets/config/settings.js';
import { get, selection } from '@/assets/CRUD/read';
import productTable from '@/views/product/modules/productTable.js';
import createColumns from '@/views/product/modules/productTableColumns.js';

export default defineComponent({
  setup(props, context) {
    const store = useStore();
    const productSocket = new Socket(`${settings.websocketProtocol}://${settings.serverPath}/product`);
    productSocket.connect();

    onMounted(() => {
      get.list('/v1/product', productTable.totalData, productTable.loading);
      productSocket.listen('update', (res) => {
        productTable.totalData.value = JSON.parse(res);
      });
    });

    onUnmounted(() => {
      productSocket.disconnect();
    });

    const columns = ref(
      createColumns((row) => {
        store.commit('rowData/set', JSON.parse(JSON.stringify(row)));
        productTable.isUpdating.value = true;
        context.emit('update', row);
      })
    );

    return {
      columns,
      ...productTable,
      showSelection: () => selection.show(columns),
      offSelection: () => selection.off(columns),
      refreshData: () =>
        get.refresh('/v1/product', productTable.totalData, productTable.loading),
    };
  },
});
</script>

<style>
.cols {
  text-align: center !important;
}
.cols.name {
  width: 12% !important;
}
.cols.version {
  width: 12% !important;
}
.cols.description {
  width: 30%;
}
#switchBar {
  display: inline-block;
  padding: 20px;
  margin-top: 10px;
  margin-bottom: 10px;
}
.switcher {
  display: inline-block;
  margin-right: 20px;
}
</style>
