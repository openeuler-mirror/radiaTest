<template>
  <n-input 
    v-model:value="searchValue"
    placeholder="搜索软件包..."
    clearable
    @input="handleInput"
  />
  <n-data-table
    :loading="loading"
    :columns="columns"
    :data="data"
    :bordered="false"
    :pagination="pagination"
  />
</template>

<script>
import { watch, toRefs, onMounted, onUnmounted, defineComponent } from 'vue';
import { loading, columns, data, getData, cleanData, searchValue, handleInput } from './modules/packageTable.js';

export default defineComponent({
  props: {
    qualityboardId: Number,
    milestonePreId: Number,
    milestoneCurId: Number, 
  },
  setup(props) {
    const { qualityboardId, milestonePreId, milestoneCurId } = toRefs(props);
    onMounted(() => {
      getData(qualityboardId.value, milestonePreId.value, milestoneCurId.value);
    });
    onUnmounted(() => {
      cleanData();
    });
    watch(milestoneCurId, () => {
      getData(qualityboardId.value, milestonePreId.value, milestoneCurId.value);
    });
    return {
      columns,
      data,
      loading,
      pagination: { 
        pageSizes: [10, 20, 50, 100, 200, 500, 1000],
        showSizePicker: true
      },
      searchValue,
      handleInput
    };
  }
});
</script>

<style scoped>
  :deep(.rpm-list-1){
  }
  :deep(.rpm-list-2){
  }
  :deep(.compare-result){
  }
</style>
