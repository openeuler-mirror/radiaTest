<template>
  <n-card style="width: 1000px" title="关联里程碑" :bordered="false" size="huge" role="dialog" aria-modal="true">
    <n-data-table :loading="tableLoading" :columns="tableColumns" :data="tableData" />
  </n-card>
</template>

<script setup>
import { NButton, NSpace } from 'naive-ui';
import { getMilestones } from '@/api/get';
import { roundRelateMilestonesAxios } from '@/api/put';

const props = defineProps(['ProductId', 'currentRound']);
const { ProductId, currentRound } = toRefs(props);

const tableLoading = ref(false);
const tableData = ref([]);
const getTableData = () => {
  getMilestones({
    product_id: ProductId.value,
    type: currentRound.value.type,
    is_sync: true,
    paged: false
  }).then((res) => {
    tableData.value = [];
    res.data.items.forEach((item) => {
      tableData.value.push({
        id: item.id,
        milestone_name: item.name,
        relate_round: item.round_id ? item.round_id : '无'
      });
    });
  });
};
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
                    getTableData();
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
                    getTableData();
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

onMounted(() => {
  getTableData();
});
</script>

<style lang="less"></style>
