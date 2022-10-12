<template>
  <div style="padding:28px 40px">
    <n-grid x-gap="24" y-gap="6">
      <n-gi :span="22">
        <n-space>
          <div>
            <create-button title="创建测试套" @click="createModalRef.show()" />
          </div>
          <modal-card :initY="100" :initX="300" title="新建测试套" ref="createModalRef" @validate="() => createFormRef.post()">
            <template #form>
              <testsuite-create
                ref="createFormRef"
                @close="
                  () => {
                    createModalRef.close();
                  }
                "
              />
            </template>
          </modal-card>
        </n-space>
      </n-gi>
      <n-gi :span="2">
        <div class="titleBtnWrap">
          <filterButton class="item" :filterRule="filterRule" @filterchange="filterchange"></filterButton>
          <refresh-button @refresh="tableRef.getData()">
            刷新测试套列表
          </refresh-button>
        </div>
      </n-gi>
      <n-gi :span="24">
        <testsuite-table ref="tableRef" @update="() => updateModalRef.show()" />
      </n-gi>
    </n-grid>
  </div>
</template>

<script>
import { ref, defineComponent, getCurrentInstance } from 'vue';
import settings from '@/assets/config/settings.js';
import Common from '@/components/CRUD';
import Essential from '@/components/testcaseComponents';
import testsuiteCreate from '@/components/testsuiteComponents/testsuiteCreate.vue';
import testsuiteTable from '@/components/testsuiteComponents/testsuiteTable.vue';
import filterButton from '@/components/filter/filterButton.vue';

export default defineComponent({
  components: {
    testsuiteCreate,
    testsuiteTable,
    ...Common,
    ...Essential,
    filterButton
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
    const { proxy } = getCurrentInstance();

    const filterValue = ref({
      name: '',
      machine_num: '',
      machine_type: null,
      remark: '',
      owner: ''
    });
    const filterRule = ref([
      {
        path: 'name',
        name: '测试套',
        type: 'input'
      },
      {
        path: 'machine_num',
        name: '节点数',
        type: 'input'
      },
      {
        path: 'machine_type',
        name: '节点类型',
        type: 'select',
        options: [
          { label: '虚拟机', value: 'kvm' },
          { label: '物理机', value: 'physical' }
        ]
      },
      {
        path: 'remark',
        name: '备注',
        type: 'input'
      },
      {
        path: 'owner',
        name: '责任人',
        type: 'input'
      }
    ]);

    const filterchange = (filterArray) => {
      filterValue.value = {
        name: null,
        machine_num: null,
        machine_type: null,
        remark: null,
        owner: null
      };
      filterArray.forEach((v) => {
        filterValue.value[v.path] = v.value;
      });
      proxy.$axios.get('/v1/suite', filterValue.value).then((res) => {
        tableRef.value.data = res.data;
        tableRef.value.pagination.page = 1;
      });
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
      filterchange
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
