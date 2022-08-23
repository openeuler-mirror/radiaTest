<template>
  <n-data-table
    id="dailybuild-card"
    remote
    :loading="listLoading"
    :data="dailyBuildList"
    :row-props="(row) => {
      return {
        style: 'cursor: pointer;',
        onClick: () => handleDailyBuildClick(row),
      }
    }"
    :columns="dailyBuildColumns"
    :pagination="dailyBuildPagination"
    :bordered="false"
  />
  <n-drawer
    v-model:show="treeShow"
    placement="right"
    :height="'100%'"
    :trap-focus="false"
    :block-scroll="false"
    :width="1000"
  >
    <n-card 
      style="height: 100%"
      :title="currentBuild"
    >
      <template #header-extra>
        <n-button text @click="handleTreeClose">
          <n-icon :size="24">
            <close />
          </n-icon>
        </n-button>
      </template>
      <div class="chart" style="height: 100%;">
        <echart :option="buildTreeOption" chartId="treeChart" />
      </div>
    </n-card>
  </n-drawer>
</template>

<script>
import { watch, reactive, onMounted, onUnmounted, defineComponent } from 'vue';
import echart from '@/components/echart/echart.vue';
import { Close } from '@vicons/ionicons5';
import * as dailyBuild from './modules/dailyBuild';

export default defineComponent({
  components: {
    echart,
    Close,
  },
  props: {
    qualityBoardId: Number,
  },
  setup(props) {
    const dailyBuildPagination = reactive({
      page: 1,
      pageSize: 5,
      showSizePicker: true,
      pageSizes: [5, 10, 20, 50, 100],
      onChange: (page) => {
        dailyBuildPagination.page = page;
        dailyBuild.getDailyBuildList(props.qualityBoardId, {
          page_num: dailyBuildPagination.page,
          page_size: dailyBuildPagination.pageSize
        });
      },
      onUpdatePageSize: (pageSize) => {
        dailyBuildPagination.pageSize = pageSize;
        dailyBuildPagination.page = 1;
        dailyBuild.getDailyBuildList(props.qualityBoardId, {
          page_num: dailyBuildPagination.page,
          page_size: dailyBuildPagination.pageSize
        });
      }
    });
    onMounted(() => {
      dailyBuild.getDailyBuildList(props.qualityBoardId, {
        page_num: dailyBuildPagination.page,
        page_size: dailyBuildPagination.pageSize
      });
    });
    watch(dailyBuild.totalNum, () => { dailyBuildPagination.itemCount = dailyBuild.totalNum.value; });
    onUnmounted(() => { dailyBuild.cleanList(); });
    return { dailyBuildPagination, ...dailyBuild};
  },
});
</script>

<style scoped>
:deep(.completion) {
  width: 600px;
}
</style>
