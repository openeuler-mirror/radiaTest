<template>
  <n-checkbox-group v-model:value="archesParam">
    <n-space justify="space-between">
      <n-space item-style="display: flex;">
        <n-checkbox value="aarch64" label="aarch64" />
        <n-checkbox value="x86_64" label="x86_64" />
        <n-checkbox value="noarch" label="noarch" />
      </n-space>
      <n-space>
        <n-popover>
          <template #trigger>
            <n-button
              style="height: auto;"
              circle
              quaternary
              :disabled="buttonDisabled"
              @click="handleCreateClick(qualityboardId, milestonePreId, milestoneCurId)"
            >
              <template #icon>
                <n-icon>
                  <compare />
                </n-icon>
              </template>
            </n-button>
          </template>
          重新比对
        </n-popover>
        <refresh-button 
          :size="18" 
          @refresh="() => {
            getData(qualityboardId, milestonePreId, milestoneCurId);
          }"
        >
          刷新数据（非重新比对）
        </refresh-button>
      </n-space>
    </n-space>
  </n-checkbox-group>
  <n-input-group>
    <n-input 
      v-model:value="thisParams.search"
      placeholder="搜索软件包..."
      clearable
    />
    <n-input-group-label style="width: 15%;">
      {{ totalNum }} in total
    </n-input-group-label>
  </n-input-group>
  <n-data-table
    remote
    :loading="loading"
    :columns="columns"
    :data="data"
    :bordered="false"
    :pagination="pagination"
    @update:filters="handleFiltersChange"
  />
</template>

<script>
import { watch, toRefs, onMounted, onUnmounted, defineComponent } from 'vue';
import { 
  loading, 
  columns, 
  data, 
  getData, 
  cleanData, 
  searchValue, 
  thisParams,
  handleCreateClick,
  totalNum,
  buttonDisabled,
  archesParam,
  compareResultColumn,
  pagination
} from './modules/packageTable.js';
import RefreshButton from '@/components/CRUD/RefreshButton';
import { CompareArrowsFilled as Compare } from '@vicons/material';

export default defineComponent({
  components: {
    RefreshButton,
    Compare,
  },
  props: {
    qualityboardId: Number,
    milestonePreId: Number,
    milestoneCurId: Number, 
  },
  setup(props) {
    const { qualityboardId, milestonePreId, milestoneCurId } = toRefs(props);
    onMounted(() => { getData(qualityboardId.value, milestonePreId.value, milestoneCurId.value); });
    onUnmounted(() => { cleanData(); });
    watch(milestoneCurId, () => {
      totalNum.value = null;
      data.value = [];
      getData(qualityboardId.value, milestonePreId.value, milestoneCurId.value);
    });
    watch(thisParams, () => {
      getData(qualityboardId.value, milestonePreId.value, milestoneCurId.value);
    }, { deep: true });
    watch(archesParam, () => { getData(qualityboardId.value, milestonePreId.value, milestoneCurId.value); });
    return {
      columns,
      data,
      loading,
      pagination,
      searchValue,
      thisParams,
      getData,
      handleCreateClick,
      totalNum,
      buttonDisabled,
      archesParam,
      handleFiltersChange(filters) {
        compareResultColumn.filterOptionValues = filters.compare_result || [];
        pagination.page = 1;
        thisParams.value.page_num = 1;
        getData(qualityboardId.value, milestonePreId.value, milestoneCurId.value);
      },
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
    width: 15%;
  }
</style>
