<template>
  <div style="padding: 28px 40px">
    <n-grid x-gap="24" y-gap="6">
      <n-gi :span="12">
        <n-space>
          <modal-card
            :initY="100"
            :initX="300"
            title="新建文本用例"
            ref="createModalRef"
            @validate="() => createFormRef.handlePropsButtonClick()"
            @submit="createFormRef.post()"
          >
            <template #form>
              <n-tabs
                animated
                type="line"
                size="large"
                :tab-padding="20"
                @update:value="(value) => createFormRef.changeTabs(value)"
              >
                <n-tab-pane tab="基本信息" name="basic">
                  <div></div>
                </n-tab-pane>
                <n-tab-pane tab="详细内容" name="detail">
                  <div></div>
                </n-tab-pane>
              </n-tabs>
              <testcase-create-form
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
            :initY="200"
            :initX="600"
            title="导入文本用例"
            ref="importModalRef"
            @validate="() => importFormRef.handlePropsButtonClick()"
            @submit="importFormRef.post()"
          >
            <template #form>
              <testcase-import-form
                ref="importFormRef"
                @valid="() => importModalRef.submitCreateForm()"
                @close="
                  () => {
                    importModalRef.close();
                  }
                "
              />
            </template>
          </modal-card>
        </n-space>
      </n-gi>
      <n-gi :span="12"> </n-gi>
      <n-gi :span="22"> </n-gi>
      <n-gi :span="2">
        <div class="titleBtnWrap">
          <filterButton
            class="item"
            :filterRule="filterRule"
            @filterchange="filterchange"
          ></filterButton>
          <refresh-button @refresh="tableRef.refreshData()"> 刷新版本列表 </refresh-button>
        </div>
      </n-gi>
      <n-gi :span="24">
        <testcase-table ref="tableRef" @update="() => updateModalRef.show()" />
        <modal-card
          :initX="300"
          title="修改文本用例"
          ref="updateModalRef"
          @validate="() => updateFormRef.handlePropsButtonClick()"
          @submit="updateFormRef.put()"
        >
          <template #form>
            <testcase-update-form
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
        <TestcaseExtendDrawer />
      </n-gi>
    </n-grid>
  </div>
</template>

<script>
import { ref, defineComponent } from 'vue';

import settings from '@/assets/config/settings.js';
import Common from '@/components/CRUD';
import Essential from '@/components/testcaseComponents';
import filterButton from '@/components/filter/filterButton.vue';
import { useStore } from 'vuex';

export default defineComponent({
  components: {
    ...Common,
    ...Essential,
    filterButton,
  },
  // eslint-disable-next-line max-lines-per-function
  setup() {
    const tableRef = ref(null);
    const createFormRef = ref(null);
    const importFormRef = ref(null);
    const updateFormRef = ref(null);
    const createModalRef = ref(null);
    const importModalRef = ref(null);
    const updateModalRef = ref(null);
    const store = useStore();
    const filterRule = ref([
      {
        path: 'suite',
        name: '测试套',
        type: 'input',
      },
      {
        path: 'name',
        name: '用例名',
        type: 'input',
      },
      {
        path: 'test_level',
        name: '测试等级',
        type: 'select',
        options: [
          {
            label: '系统测试',
            value: '系统测试',
          },
          {
            label: '集成测试',
            value: '集成测试',
          },
          {
            label: '单元测试',
            value: '单元测试',
          },
        ],
      },
      {
        path: 'test_type',
        name: '测试类型',
        type: 'select',
        options: [
          {
            label: '功能测试',
            value: '功能测试',
          },
          {
            label: '安全测试',
            value: '安全测试',
          },
          {
            label: '性能测试',
            value: '性能测试',
          },
          {
            label: '压力测试',
            value: '压力测试',
          },
          {
            label: '可靠性测试',
            value: '可靠性测试',
          },
        ],
      },
      {
        path: 'machine_num',
        name: '节点数',
        type: 'input',
      },
      {
        path: 'machine_type',
        name: '节点类型',
        type: 'select',
        options: [
          { label: '虚拟机', value: 'kvm' },
          { label: '物理机', value: 'physical' },
        ],
      },
      {
        path: 'automatic',
        name: '自动化',
        type: 'select',
        options: [
          { label: '是', value: true },
          { label: '否', value: false },
        ],
      },
      {
        path: 'remark',
        name: '备注',
        type: 'input',
      },
      {
        path: 'owner',
        name: '责任人',
        type: 'input',
      },
    ]);
    const filterValue = ref({
      suite: '',
      name: '',
      test_level: null,
      test_type: null,
      machine_num: '',
      machine_type: null,
      automatic: null,
      remark: '',
      owner: '',
    });

    const filterchange = (filterArray) => {
      filterValue.value = {
        suite: null,
        name: null,
        test_level: null,
        test_type: null,
        machine_num: null,
        machine_type: null,
        automatic: null,
        remark: null,
        owner: null,
      };
      filterArray.forEach((v) => {
        filterValue.value[v.path] = v.value;
      });
      store.commit('filterCase/setAll', filterValue.value);
    };

    return {
      settings,
      tableRef,
      createFormRef,
      importFormRef,
      updateFormRef,
      createModalRef,
      importModalRef,
      updateModalRef,
      filterRule,
      filterchange,
    };
  },
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
