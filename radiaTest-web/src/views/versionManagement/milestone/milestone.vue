<template>
  <modal-card
    title="注册里程碑"
    url="/v2/milestone"
    ref="createModalRef"
    @validate="() => createFormRef.handlePropsButtonClick()"
    @submit="createFormRef.post()"
  >
    <template #form>
      <milestone-create-form
        ref="createFormRef"
        @valid="() => createModalRef.submitCreateForm()"
        @close="
          () => {
            createModalRef.close();
          }
        "
      />
    </template>
  </modal-card>

  <modal-card
    title="批量同步社区里程碑"
    url="/v2/milestone/batch-sync"
    ref="synchModalRef"
    @validate="() => synchFormRef.handlePropsButtonClick()"
    @submit="synchFormRef.post()"
  >
    <template #form>
      <milestone-synch-form
        ref="synchFormRef"
        @valid="() => synchModalRef.submitCreateForm()"
        @close="
          () => {
            synchModalRef.close();
          }
        "
      />
    </template>
  </modal-card>

  <div class="milestone-head">
    <div>
      <create-button title="注册里程碑" @click="createModalRef.show()" />
      <create-button
        style="margin-left: 30px"
        title="批量同步社区里程碑"
        @click="synchModalRef.show()"
      />
    </div>
    <div style="display: flex; align-items: center">
      <filterButton
        :filterRule="filterRule"
        @filterchange="filterchange"
        style="display: flex; padding-right: 20px"
      >
      </filterButton>
      <refresh-button @refresh="getTableData()"> 刷新里程碑列表 </refresh-button>
    </div>
  </div>
  <n-grid x-gap="24">
    <n-gi :span="24">
      <milestone-table ref="tableRef" @update="() => updateModalRef.show()" />
      <modal-card
        title="修改里程碑"
        url="/v2/milestone"
        ref="updateModalRef"
        @validate="() => updateFormRef.handlePropsButtonClick()"
        @submit="updateFormRef.put()"
      >
        <template #form>
          <milestone-update-form
            ref="updateFormRef"
            @valid="() => updateModalRef.submitCreateForm()"
            @close="
              () => {
                updateModalRef.close();
              }
            "
          />
        </template>
      </modal-card>
      <n-modal v-model:show="showSyncRepoModal" @after-leave="leaveSyncRepoModal">
        <n-card
          style="width: 600px"
          title="同步企业仓"
          :bordered="false"
          size="huge"
          role="dialog"
          aria-modal="true"
        >
          <div class="itemWrap">
            <n-select
              class="item"
              v-model:value="selectMilestoneValue"
              :options="selectMilestoneOptions"
              @scroll="handleScroll"
              :loading="loading"
              remote
            />
            <n-button
              class="btn"
              type="info"
              ghost
              @click="syncMilestoneFn"
              :disabled="!selectMilestoneValue"
              >同步</n-button
            >
          </div>
        </n-card>
      </n-modal>
      <MilestoneExtendDrawer />
    </n-gi>
  </n-grid>
</template>

<script>
import { ref, defineComponent } from 'vue';
import settings from '@/assets/config/settings.js';
import milestoneTable from '@/views/versionManagement/milestone/modules/milestoneTable';
import milestoneTableColumns from '@/views/versionManagement/milestone/modules/milestoneTableColumns.js';
import Common from '@/components/CRUD';
import Essential from '@/components/milestoneComponents';
import filterButton from '@/components/filter/filterButton.vue';

export default defineComponent({
  components: {
    filterButton,
    ...Common,
    ...Essential,
  },
  // eslint-disable-next-line max-lines-per-function
  setup() {
    const tableRef = ref(null);
    const createFormRef = ref(null);
    const updateFormRef = ref(null);
    const createModalRef = ref(null);
    const updateModalRef = ref(null);
    const synchModalRef = ref(null);
    const synchFormRef = ref(null);
    const filterRule = ref([
      {
        path: 'milestoneName',
        name: '里程碑名',
        type: 'input',
      },
    ]);

    const filterchange = (filterArray) => {
      milestoneTable.filter.value.name = filterArray[0].value;
      milestoneTable.pagination.value.page = 1;
      milestoneTable.filter.value.page_num = 1;
      milestoneTable.getTableData();
    };

    return {
      settings,
      tableRef,
      createFormRef,
      updateFormRef,
      createModalRef,
      updateModalRef,
      synchModalRef,
      synchFormRef,
      filterchange,
      filterRule,
      ...milestoneTable,
      ...milestoneTableColumns,
    };
  },
});
</script>

<style scoped lang="less">
.milestone-head {
  display: flex;
  justify-content: space-between;
  margin: 10px 0;
}

.itemWrap {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;

  .item {
    width: 450px;
  }
}
</style>
