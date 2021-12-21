<template>
  <n-card hoverable>
    <n-data-table
      ref="table"
      size="large"
      :bordered="false"
      :loading="loading"
      :columns="columns"
      :data="data"
      :row-key="(row) => row.id"
    />
  </n-card>
</template>

<script>
import { onMounted, defineComponent } from 'vue';

import productMilestone from '@/views/product/modules/productMilestone.js';

export default defineComponent({
  props: {
    form: Object,
  },
  setup(props) {
    onMounted(() => {
      productMilestone.getData(props.form.id);
    });

    return {
      ...productMilestone,
    };
  },
});
</script>

<style scoped></style>
