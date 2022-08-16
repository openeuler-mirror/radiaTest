<template>
  <n-data-table
    id="at-card"
    remote
    :loading="atLoading"
    :data="atGroupOverviewData"
    :row-key="(rowData) => rowData.build"
    :row-props="(row) => {
      return {
        style: 'cursor: pointer;',
        onClick: () => handleAtBuildClick(qualityBoardId, row),
      }
    }"
    :columns="atColumns"
    :pagination="atPagination"
    :bordered="false"
    @update:sorter="handleSorterChange"
  />
  <n-drawer
    v-model:show="atTestsOverviewShow"
    placement="bottom"
    :height="'100%'"
    :trap-focus="false"
    :block-scroll="false"
    to="#at-card"
  >
    <n-card 
      style="height: 100%;"
      :title="currentBuild" 
    >
      <template #header-extra>
        <n-button text @click="handleTestsClose">
          <n-icon :size="24">
            <close />
          </n-icon>
        </n-button>
      </template>
      <n-data-table 
        style="height: 100%;"
        :data="atTestsOverviewData"
        :loading="atLoading"
        :bordered="false"
        :columns="atTestsColumns"
        :row-key="(rowData) => rowData.test"
      />
    </n-card>
    
  </n-drawer>
</template>

<script>
import { watch, reactive, onMounted, onUnmounted, defineComponent } from 'vue';
import * as atOverview from './modules/atOverview';
import { Close } from '@vicons/ionicons5';

export default defineComponent({
  components: {
    Close,
  },
  props: {
    qualityBoardId: Number
  },
  setup(props) {
    const atPagination = reactive({
      page: 1,
      pageSize: 5,
      showSizePicker: true,
      pageSizes: [5, 10, 20, 50, 100],
      onChange: (page) => {
        atPagination.page = page;
        atOverview.getAtData(props.qualityBoardId, {
          page_num: atPagination.page,
          page_size: atPagination.pageSize
        });
      },
      onUpdatePageSize: (pageSize) => {
        atPagination.pageSize = pageSize;
        atPagination.page = 1;
        atOverview.getAtData(props.qualityBoardId, {
          page_num: atPagination.page,
          page_size: atPagination.pageSize
        });
      }
    });
    onMounted(() => {
      atOverview.getAtData(props.qualityBoardId, {
        page_num: atPagination.page,
        page_size: atPagination.pageSize
      });
    });
    watch(atOverview.totalNum, () => { atPagination.itemCount = atOverview.totalNum.value; });
    onUnmounted(() => { atOverview.cleanData(); });
    return { 
      atPagination, 
      ...atOverview,
      handleSorterChange (sorter) {
        atOverview.getAtData(props.qualityBoardId, {
          page_num: atPagination.page,
          page_size: atPagination.pageSize,
          build_order: sorter.order ? sorter.order : 'descend'
        });
      }
    };
  }
});
</script>

<style>
.at-progress {
  width: 600px;
}
.tests-col {
  width: 30%;
}
.tests-res {
  display: flex;
  align-items: center;
}
</style>
