<template>
  <n-card style="width: 1000px" title="关联里程碑" :bordered="false" size="huge" role="dialog" aria-modal="true">
    <div class="searchWrap">
      <n-input
        type="text"
        clearable
        placeholder="搜索里程碑..."
        class="searchInput"
        @change="changeSearchValue"
        v-model:value="milestoneSearchValue"
      >
        <template #suffix>
          <n-icon size="22" class="search">
            <Search />
          </n-icon>
        </template>
      </n-input>
    </div>
    <n-data-table
      remote
      :loading="tableLoading"
      :columns="tableColumns"
      :data="tableData"
      :pagination="tablePagination"
      @update:page="tablePageChange"
      @update:page-size="tablePageSizeChange"
    />
  </n-card>
</template>

<script setup>
import { NButton, NSpace } from 'naive-ui';
import { roundRelateMilestonesAxios } from '@/api/put';
import { useTable } from '@/hooks/useTable';
import { Search } from '@vicons/tabler';
import { workspace } from '@/assets/config/menu.js';

const props = defineProps(['ProductId', 'currentRound']);
const { ProductId, currentRound } = toRefs(props);
const tableLoading = ref(false);
const tablePagination = ref({
  page: 1,
  pageSize: 10,
  pageCount: 1,
  showSizePicker: true,
  pageSizes: [5, 10, 20, 50]
});
const resData = ref([]);
const milestoneSearchValue = ref('');
const searchName = ref('');
const getDataParams = ref({
  product_id: ProductId.value,
  type: currentRound.value.type,
  is_sync: true,
  paged: true,
  page_num: toRef(tablePagination.value, 'page'),
  page_size: toRef(tablePagination.value, 'pageSize'),
  name: searchName
});
const tableData = computed(() => {
  return resData.value?.map((item) => ({
    id: item.id,
    milestone_name: item.name,
    relate_round: item?.round_info?.name ? item?.round_info?.name : '无'
  }));
});
const tableColumns = ref([
  {
    key: 'milestone_name',
    title: '里程碑名',
    align: 'center'
  },
  {
    key: 'relate_round',
    title: '关联round',
    align: 'center'
  },
  {
    title: '操作',
    align: 'center',
    render(row) {
      return h(
        NSpace,
        {
          style: 'justify-content: center'
        },
        {
          default: () => {
            return [
              h(
                NButton,
                {
                  text: true,
                  onClick: async () => {
                    await roundRelateMilestonesAxios(currentRound.value.id, {
                      milestone_id: row.id,
                      isbind: true
                    });
                    useTable(`/v2/ws/${workspace.value}/milestone`, getDataParams.value, resData, tablePagination, tableLoading, true);
                  }
                },
                {
                  default: () => '关联'
                }
              ),
              h(
                NButton,
                {
                  text: true,
                  onClick: async () => {
                    await roundRelateMilestonesAxios(currentRound.value.id, {
                      milestone_id: row.id,
                      isbind: false
                    });
                    useTable(`/v2/ws/${workspace.value}/milestone`, getDataParams.value, resData, tablePagination, tableLoading, true);
                  }
                },
                {
                  default: () => '取消关联'
                }
              )
            ];
          }
        }
      );
    }
  }
]);

const tablePageChange = (page) => {
  tablePagination.value.page = page;
};

const tablePageSizeChange = (pageSize) => {
  tablePagination.value.pageSize = pageSize;
  tablePagination.value.page = 1;
};

const changeSearchValue = () => {
  searchName.value = milestoneSearchValue.value;
  tablePagination.value.page = 1;
};

useTable(`/v2/ws/${workspace.value}/milestone`, getDataParams.value, resData, tablePagination, tableLoading);
</script>

<style lang="less">
.searchWrap {
  display: flex;
  justify-content: right;

  .searchInput {
    width: 400px;
    margin: 0 0 10px;
  }
}
</style>
