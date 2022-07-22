<template>
  <n-card
    title="里程碑"
    size="huge"
    :segmented="{
      content: 'hard'
    }"
    header-style="
            font-size: 30px; 
            height: 80px; 
            font-family: 'v-sans';
            padding-top: 40px; 
            background-color: rgb(242,242,242);
        "
    style="height: 100%"
  >
    <!-- <selection-button
      :left="20"
      :top="88"
      @show="tableRef.showSelection()"
      @off="tableRef.offSelection()"
    /> -->
    <n-grid x-gap="24" y-gap="6">
      <n-gi :span="12">
        <n-space>
          <create-button title="注册里程碑" @click="createModalRef.show()" />
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
          <!-- <delete-button title="里程碑" url="/v2/milestone" /> -->
        </n-space>
      </n-gi>
      <n-gi :span="10">
      </n-gi>
      <n-gi :span="2">
        <div class="titleBtnWrap">
          <filterButton class="item" :filterRule="filterRule" @filterchange="filterchange"></filterButton>
          <refresh-button class="item" @refresh="tableRef.refreshData()">
            刷新版本列表
          </refresh-button>
        </div>
      </n-gi>
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
        <extend-drawer />
      </n-gi>
    </n-grid>
    <template #action>
      <n-divider />
      <div
        style="
          text-align: center;
          color: grey;
          padding-top: 15px;
          padding-bottom: 0;
        "
      >
        {{ settings.name }} {{ settings.version }} · {{ settings.license }}
      </div>
    </template>
  </n-card>
</template>

<script>
import { ref, defineComponent } from 'vue';

import settings from '@/assets/config/settings.js';
import Common from '@/components/CRUD';
import Essential from '@/components/milestoneComponents';
import filterButton from '@/components/filter/filterButton.vue';
import milestoneTable from '@/views/milestone/modules/milestoneTable';
import { get } from '@/assets/CRUD/read';

export default defineComponent({
  components: {
    ...Common,
    ...Essential,
    filterButton
  },
  setup() {
    const tableRef = ref(null);
    const createFormRef = ref(null);
    const updateFormRef = ref(null);
    const createModalRef = ref(null);
    const updateModalRef = ref(null);
    const filterRule = ref([
      {
        path: 'milestoneName',
        name: '里程碑名',
        type: 'input'
      }
    ]);

    const filterchange = (filterArray) => {
      milestoneTable.filter.value.name = filterArray[0].value;
      get.list('/v2/milestone', milestoneTable.totalData, milestoneTable.loading, milestoneTable.filter.value);
    };

    return {
      settings,
      tableRef,
      createFormRef,
      updateFormRef,
      createModalRef,
      updateModalRef,
      filterRule,
      filterchange,
      ...milestoneTable
    };
  }
});
</script>

<style scoped lang="less">
.titleBtnWrap {
  display: flex;
  align-items: center;

  .item {
    margin: 0 20px;
  }
}
</style>
