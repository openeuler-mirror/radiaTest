<template>
  <n-card hoverable>
    <n-data-table
      :columns="columns"
      :data="data"
      size="small"
      :max-height="250"
      virtual-scroll
    />
  </n-card>
</template>

<script>
import { defineComponent } from 'vue';

export default defineComponent({
  props: {
    data: Array,
  },
  setup() {
    return {
      columns: [
        {
          title: '测试用例',
          key: 'name',
        },
      ],
    };
  },
});
</script>
