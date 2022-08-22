<template>
  <n-data-table
    id="weeklybuild-card"
    remote
    :loading="listLoading"
    :data="weeklybuildData"
    :columns="weeklybuildColumns"
    :pagination="weeklybuildPagination"
    :bordered="false"
    :row-props="(row) => {
      return {
        style: 'cursor: pointer;',
        onClick: () => handleWeekClick(row),
      }
    }"
  />
  <n-drawer
    v-model:show="weekShow"
    placement="right"
    :height="'100%'"
    :width="1000"
    :trap-focus="false"
    :block-scroll="false"
  >
    <n-card 
      style="height: 100%;"
      :title="`Week: ${weekStartDate} -> ${weekEndDate}`" 
    >
      <template #header-extra>
        <n-button text @click="() => { weekShow = false; }">
          <n-icon :size="24">
            <close />
          </n-icon>
        </n-button>
      </template>
      <n-data-table 
        style="height: 100%;"
        :data="detailData"
        :loading="detailLoading"
        :bordered="false"
        :columns="detailColumns"
      />
    </n-card>
  </n-drawer>
</template>

<script>
import { watch, reactive, onMounted, onUnmounted, defineComponent } from 'vue';
import * as modules from './modules/weeklybuildHealth';
import { Close } from '@vicons/ionicons5';

export default defineComponent({
  components: {
    Close,
  },
  props: {
    qualityBoardId: Number,
  },
  setup(props) {
    const weeklybuildPagination = reactive({
      page: 1,
      pageSize: 5,
      showSizePicker: true,
      pageSizes: [5, 10, 20, 50, 100],
      onChange: (page) => {
        weeklybuildPagination.page = page;
        modules.getData(props.qualityBoardId, {
          page_num: weeklybuildPagination.page,
          page_size: weeklybuildPagination.pageSize
        });
      },
      onUpdatePageSize: (pageSize) => {
        weeklybuildPagination.pageSize = pageSize;
        weeklybuildPagination.page = 1;
        modules.getData(props.qualityBoardId, {
          page_num: weeklybuildPagination.page,
          page_size: weeklybuildPagination.pageSize
        });
      }
    });
    onMounted(() => {
      modules.getData(props.qualityBoardId, {
        page_num: weeklybuildPagination.page,
        page_size: weeklybuildPagination.pageSize
      });
    });
    watch(modules.totalNum, () => { weeklybuildPagination.itemCount = modules.totalNum.value; });
    onUnmounted(() => { modules.cleanData(); });
    return { weeklybuildPagination, ...modules};
  },
});
</script>

<style scoped>
</style>
