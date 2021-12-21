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
import { ref, onMounted, onUnmounted, defineComponent } from 'vue';
import { Socket } from '@/socket';

import settings from '@/assets/config/settings.js';
import disksDataTable from '@/views/vmachine/modules/expandedContent/disksDataTable.js';
import { get } from '@/assets/CRUD/read';

export default defineComponent({
  props: {
    id: Number,
  },
  setup(props) {
    const vdiskSocket = new Socket(`ws://${settings.serverPath}/vdisk`);
    vdiskSocket.connect();

    const data = ref([]);
    const loading = ref([]);

    onMounted(() => {
      get.filter('/v1/vdisk', data, loading, {
        vmachine_id: props.id,
      });
      vdiskSocket.listen('update', (res) => {
        const totalData = JSON.parse(res);
        data.value = totalData.filter((item) => item.vmachine_id === props.id);
      });
    });
    onUnmounted(() => {
      vdiskSocket.disconnect();
    });

    return {
      data,
      loading,
      ...disksDataTable,
      refreshData: () =>
        get.filter('/v1/vdisk', data, loading, {
          vmachine_id: props.id,
        }),
    };
  },
});
</script>

<style scoped></style>
