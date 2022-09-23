<template>
  <n-data-table 
    :columns="columns"
    :data="data"
    :bordered="false"
  />
</template>

<script>
import { data, columns } from './modules/rpmCheck.js';

export default defineComponent({
  components: {},
  props: {},
  setup() {
    return {
      data,
      columns,
    };
  },
});
</script>

<style scoped>
</style>
