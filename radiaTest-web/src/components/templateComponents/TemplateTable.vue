<template>
  <n-data-table
    :bordered="false"
    :data="data"
    :columns="columns"
    :row-key="(row) => row.id"
    :pagination="pagination"
  />
</template>

<script>
import { inject, computed, defineComponent } from 'vue';

import templateTable from '@/views/template/modules/templateTable.js';
import { getColumns } from '@/views/template/modules/templateTableColumns.js';

export default defineComponent({
  props: {
    type: {
      default: 'personal',
      type: String,
    },
  },
  setup(props) {
    const columns = getColumns();
    const injectData = inject(props.type);
    const injectSearch = inject('search');

    const data = computed(() => {
      if (injectSearch.value) {
        return injectData.value.filter((item) =>
          item.name.toLowerCase().includes(injectSearch.value.toLowerCase())
        );
      }
      return injectData.value;
    });

    return {
      data,
      ...templateTable,
      columns,
    };
  },
});
</script>

<style scoped></style>
