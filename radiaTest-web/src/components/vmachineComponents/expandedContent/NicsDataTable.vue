<template>
  <n-data-table
    :row-keys="(row) => row.id"
    :data="data"
    :loading="loading"
    :columns="columns"
    :bordered="false"
  />
</template>

<script>
import { ref, onUnmounted, defineComponent, onMounted } from 'vue';
import { Socket } from '@/socket';

import settings from '@/assets/config/settings.js';
import nicsDataTable from '@/views/vmachine/modules/expandedContent/nicsDataTable.js';
import { get } from '@/assets/CRUD/read';

export default defineComponent({
  props: {
    id: Number,
  },
  setup(props) {
    const vnicSocket = new Socket(`ws://${settings.serverPath}/vnic`);
    vnicSocket.connect();

    const data = ref([]);
    const loading = ref(false);

    onMounted(() => {
      get.filter('/v1/vnic', data, loading, {
        vmachine_id: props.id,
      });
      vnicSocket.listen('update', (res) => {
        const totalData = JSON.parse(res);
        data.value = totalData.filter((item) => item.vmachine_id === props.id);
      });
    });

    onUnmounted(() => {
      vnicSocket.disconnect();
    });

    return {
      data,
      loading,
      ...nicsDataTable,
      refreshData: () =>
        get.filter('/v1/vnic', data, loading, {
          vmachine_id: props.id,
        }),
    };
  },
});
</script>

<style scoped></style>
