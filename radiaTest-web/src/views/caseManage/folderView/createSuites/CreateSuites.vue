<template>
  <n-modal v-model:show="showModal">
    <n-card
      style="width: 60%;"
      title="从游离测试套列表选取"
      :closable="true"
      @close="() => { showModal = false;}"
    >
      <n-button
        style="margin-bottom: 10px;"
        :disabled="checkedSuites.length === 0"
        @click="handleSubmitSuites"
        type="primary"
      >
        导入已选测试套
      </n-button>
      <n-data-table
        remote
        :columns="columns"
        :data="data"
        :row-key="row => row.id"
        @update:checked-row-keys="handleCheck"
        :pagination="pagination"
        @update:page="turnPage"
        @update:page-size="turnPageSize"
      />
    </n-card>
  </n-modal>
</template>

<script setup>
import { storage } from '@/assets/utils/storageUtils.js';
import { 
  createSuitesShow as showModal, 
  orphanSuitesData as data,
  orphanSuitesPagination as pagination,
  getOrphanSuitesReq,
  createSuitesTargetNode as node,
} from '../modules/menu.js';
import { createSuites } from '@/api/post.js';
import { useMessage } from 'naive-ui';

const columns = [
  {
    type: 'selection',
  },
  {
    title: '测试套',
    key: 'name',
  },
  {
    title: '备注',
    key: 'remark',
  },
  {
    title: '责任人',
    key: 'owner',
  },
  {
    title: '测试框架',
    key: 'framework',
    render: (row) => h('p', null, row.framework.name),
  },
  {
    title: '源码仓',
    key: 'gitRepo',
    render: (row) => h('a', { href: row.git_repo.git_url }, row.git_repo.git_url),
  },
];

const message = useMessage();

const checkedSuites = ref([]);

function handleCheck(checkedKeys) {
  checkedSuites.value = checkedKeys;
}

function turnPage(page) {
  pagination.page = page;
  getOrphanSuitesReq();
}

function turnPageSize(size) {
  pagination.pageSize = size;
  getOrphanSuitesReq();
}

function handleSubmitSuites() {
  createSuites(
    node.value.id,
    {
      permission_type: 'org',
      org_id: storage.getValue('loginOrgId'),
      suites: checkedSuites.value,
      creator_id: storage.getValue('user_id'),
    }
  )
    .then(() => {
      message.success('新增成功');
      showModal.value = false;
    });
}

onUnmounted(() => {
  data.value = [];
  checkedSuites.value = [];
  node.value = {};
  pagination.page = 1;
  pagination.pageCount = 1;
  pagination.itemCount = 1;
  pagination.pageSize = 10;
  pagination.showSizePicker = true;
  pagination.pageSizes = [5, 10, 20, 50];
});
</script>

<style scoped lang="less">
</style>
